from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import current_user, get_db
from app.api.routes.workspaces import require_workspace
from app.repositories.domain import (
    ActivityRepository,
    AnalysisJobRepository,
    CollectionRepository,
    DocumentRepository,
    DocumentVersionRepository,
)
from app.schemas.entities import DocumentOut, NoteCreate, NoteUpdate
from app.services.activity import ActivityService
from app.services.analysis import AnalysisService
from app.services.parser import ExtractedTextTooLargeError, extract_document_text
from app.services.rag import RAGService
from app.services.storage import FileStorageService, UploadTooLargeError

router = APIRouter(prefix="/documents", tags=["documents"])


async def require_document(db: AsyncIOMotorDatabase, user_id: str, document_id: str) -> dict:
    document = await DocumentRepository(db).get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    await require_workspace(db, user_id, document["workspace_id"])
    return document


def normalize_terms(values: list[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        terms.extend(item.strip() for item in value.split(","))
    return sorted({term for term in terms if term}, key=str.lower)


def validate_document_content_size(content: str) -> None:
    from app.core.config import get_settings

    limit = get_settings().max_document_chars
    if len(content) > limit:
        raise HTTPException(status_code=413, detail=f"Document content exceeds {limit} character limit")


async def require_workspace_collections(
    db: AsyncIOMotorDatabase, workspace_id: str, collection_ids: list[str]
) -> list[str]:
    normalized_ids = normalize_terms(collection_ids)
    if not normalized_ids:
        return []
    collections = await CollectionRepository(db).list_for_workspace(workspace_id)
    valid_ids = {collection["id"] for collection in collections}
    invalid_ids = [collection_id for collection_id in normalized_ids if collection_id not in valid_ids]
    if invalid_ids:
        raise HTTPException(status_code=400, detail="One or more collections do not belong to this workspace")
    return normalized_ids


@router.post("/notes", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    await require_workspace(db, user["id"], payload.workspace_id, "editor")
    validate_document_content_size(payload.content)
    collection_ids = await require_workspace_collections(db, payload.workspace_id, payload.collection_ids)
    tags = normalize_terms(payload.tags)
    document = await DocumentRepository(db).create(
        {
            **payload.model_dump(exclude={"collection_ids", "tags"}),
            "collection_ids": collection_ids,
            "tags": tags,
            "source_type": "note",
            "filename": None,
            "file_storage_path": None,
            "file_size_bytes": None,
            "analysis_status": "pending",
            "summary": None,
            "key_points": [],
            "action_items": [],
        }
    )
    await ActivityService(ActivityRepository(db)).record(
        payload.workspace_id, user["id"], "created", "document", f"Created note {document['title']}", document["id"]
    )
    background_tasks.add_task(AnalysisService(db).run_document_analysis, document["id"], user["id"])
    return document


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    workspace_id: str = Form(...),
    collection_ids: list[str] = Form(default=[]),
    tags: list[str] = Form(default=[]),
    file: UploadFile = File(...),
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    await require_workspace(db, user["id"], workspace_id, "editor")
    collection_ids = await require_workspace_collections(db, workspace_id, collection_ids)
    tags = normalize_terms(tags)
    storage = FileStorageService()
    try:
        stored_file = await storage.save_upload(file, workspace_id)
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    try:
        extracted = await extract_document_text(file)
    except ExtractedTextTooLargeError as exc:
        storage.delete_stored_file(stored_file.get("storage_path"))
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ValueError as exc:
        storage.delete_stored_file(stored_file.get("storage_path"))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    title = Path(extracted.filename).stem
    document = await DocumentRepository(db).create(
        {
            "workspace_id": workspace_id,
            "title": title,
            "source_type": "upload",
            "filename": extracted.filename,
            "file_storage_path": stored_file["storage_path"],
            "file_size_bytes": stored_file["size_bytes"],
            "content": extracted.content,
            "content_segments": extracted.segments,
            "analysis_status": "pending",
            "summary": None,
            "key_points": [],
            "action_items": [],
            "collection_ids": collection_ids,
            "tags": tags,
        }
    )
    await ActivityService(ActivityRepository(db)).record(
        workspace_id, user["id"], "uploaded", "document", f"Uploaded {extracted.filename}", document["id"]
    )
    background_tasks.add_task(AnalysisService(db).run_document_analysis, document["id"], user["id"])
    return document


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: str, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    return await require_document(db, user["id"], document_id)


@router.patch("/{document_id}", response_model=DocumentOut)
async def update_document(
    document_id: str,
    payload: NoteUpdate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    document = await require_document(db, user["id"], document_id)
    await require_workspace(db, user["id"], document["workspace_id"], "editor")
    updates = payload.model_dump(exclude_unset=True)
    if "collection_ids" in updates:
        updates["collection_ids"] = await require_workspace_collections(
            db, document["workspace_id"], updates["collection_ids"]
        )
    if "tags" in updates:
        updates["tags"] = normalize_terms(updates["tags"])
    if "content" in updates:
        validate_document_content_size(updates["content"])
    should_reanalyze = "content" in updates or "title" in updates
    if should_reanalyze:
        updates.update({"analysis_status": "pending", "summary": None, "key_points": [], "action_items": []})
    await DocumentVersionRepository(db).create_from_document(document, user["id"], "updated")
    updated = await DocumentRepository(db).update(document_id, updates)
    await ActivityService(ActivityRepository(db)).record(
        document["workspace_id"], user["id"], "updated", "document", f"Updated {updated['title']}", document_id
    )
    if should_reanalyze:
        background_tasks.add_task(AnalysisService(db).run_document_analysis, document_id, user["id"])
    else:
        await RAGService(db).index_document(updated)
    return updated


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> None:
    document = await require_document(db, user["id"], document_id)
    await require_workspace(db, user["id"], document["workspace_id"], "editor")
    await DocumentVersionRepository(db).create_from_document(document, user["id"], "archived")
    await DocumentRepository(db).archive(document_id)
    await RAGService(db).remove_document(document_id)
    await ActivityService(ActivityRepository(db)).record(
        document["workspace_id"], user["id"], "archived", "document", f"Archived {document['title']}"
    )


@router.post("/{document_id}/restore", response_model=DocumentOut)
async def restore_archived_document(
    document_id: str,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    document = await DocumentRepository(db).get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    await require_workspace(db, user["id"], document["workspace_id"], "editor")
    restored = await DocumentRepository(db).restore(document_id)
    await RAGService(db).index_document(restored)
    await ActivityService(ActivityRepository(db)).record(
        document["workspace_id"], user["id"], "restored", "document", f"Restored {document['title']}", document_id
    )
    return restored


@router.get("/{document_id}/export")
async def export_document(
    document_id: str, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    document = await require_document(db, user["id"], document_id)
    versions = await DocumentVersionRepository(db).list_for_document(document_id, limit=100)
    jobs = await AnalysisJobRepository(db).list_for_document(document_id, limit=100)
    return {"document": document, "versions": versions, "analysis_jobs": jobs}


@router.post("/{document_id}/analyze", response_model=DocumentOut)
async def regenerate_insights(
    document_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    document = await require_document(db, user["id"], document_id)
    await require_workspace(db, user["id"], document["workspace_id"], "editor")
    updated = await DocumentRepository(db).update(
        document_id, {"analysis_status": "pending", "summary": None, "key_points": [], "action_items": []}
    )
    await ActivityService(ActivityRepository(db)).record(
        document["workspace_id"], user["id"], "analyzed", "document", f"Regenerated AI insights for {document['title']}", document_id
    )
    background_tasks.add_task(AnalysisService(db).run_document_analysis, document_id, user["id"])
    return updated


@router.get("/{document_id}/analysis-jobs")
async def document_analysis_jobs(
    document_id: str, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> list[dict]:
    await require_document(db, user["id"], document_id)
    return await AnalysisJobRepository(db).list_for_document(document_id)


@router.get("/{document_id}/versions")
async def document_versions(
    document_id: str, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> list[dict]:
    await require_document(db, user["id"], document_id)
    return await DocumentVersionRepository(db).list_for_document(document_id)


@router.post("/{document_id}/versions/{version}/restore", response_model=DocumentOut)
async def restore_document_version(
    document_id: str,
    version: int,
    background_tasks: BackgroundTasks,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    document = await require_document(db, user["id"], document_id)
    await require_workspace(db, user["id"], document["workspace_id"], "editor")
    target = await DocumentVersionRepository(db).get_version(document_id, version)
    if not target:
        raise HTTPException(status_code=404, detail="Document version not found")
    await DocumentVersionRepository(db).create_from_document(document, user["id"], "restored")
    snapshot = target["snapshot"]
    restored = await DocumentRepository(db).update(
        document_id,
        {
            "title": snapshot["title"],
            "content": snapshot["content"],
            "content_segments": snapshot.get("content_segments", []),
            "summary": snapshot.get("summary"),
            "key_points": snapshot.get("key_points", []),
            "action_items": snapshot.get("action_items", []),
            "collection_ids": snapshot.get("collection_ids", []),
            "tags": snapshot.get("tags", []),
            "analysis_status": "pending",
        },
    )
    await ActivityService(ActivityRepository(db)).record(
        document["workspace_id"], user["id"], "restored", "document", f"Restored {document['title']} to v{version}", document_id
    )
    background_tasks.add_task(AnalysisService(db).run_document_analysis, document_id, user["id"])
    return restored
