from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import current_user, get_db
from app.api.routes.workspaces import accessible_workspaces
from app.repositories.domain import ActivityRepository, CollectionRepository, DocumentRepository, WorkspaceRepository

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard(user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> dict:
    workspaces = await accessible_workspaces(db, user["id"])
    workspace_ids = [workspace["id"] for workspace in workspaces]
    collections: list[dict] = []
    recent_documents: list[dict] = []
    activity: list[dict] = []
    for workspace_id in workspace_ids:
        collections.extend(await CollectionRepository(db).list_for_workspace(workspace_id))
        recent_documents.extend(await DocumentRepository(db).list_for_workspace(workspace_id, limit=10))
        activity.extend(await ActivityRepository(db).list_for_workspace(workspace_id, limit=10))

    recent_documents = sorted(recent_documents, key=lambda item: item["updated_at"], reverse=True)[:10]
    insights = [
        {
            "document_id": doc["id"],
            "title": doc["title"],
            "summary": doc.get("summary"),
            "key_points": doc.get("key_points", [])[:3],
            "action_items": doc.get("action_items", [])[:3],
        }
        for doc in recent_documents
        if doc.get("summary") or doc.get("key_points") or doc.get("action_items")
    ][:6]
    return {
        "workspaces": workspaces,
        "collections": collections[:20],
        "recent_documents": recent_documents,
        "insights": insights,
        "activity": sorted(activity, key=lambda item: item["created_at"], reverse=True)[:15],
    }


@router.get("/search")
async def search(
    q: str,
    limit: int = 25,
    offset: int = 0,
    include_archived: bool = False,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    workspaces = await accessible_workspaces(db, user["id"])
    if not q.strip() or not workspaces:
        return {"items": [], "limit": limit, "offset": offset}
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    items = await DocumentRepository(db).search(
        [workspace["id"] for workspace in workspaces],
        q.strip(),
        limit=limit,
        skip=offset,
        include_archived=include_archived,
    )
    return {"items": items, "limit": limit, "offset": offset}
