from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import current_user, get_db
from app.api.routes.workspaces import require_workspace
from app.repositories.domain import ActivityRepository, CollectionRepository, DocumentRepository
from app.schemas.entities import CollectionCreate, CollectionOut
from app.services.activity import ActivityService

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
async def create_collection(
    payload: CollectionCreate, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    await require_workspace(db, user["id"], payload.workspace_id, "editor")
    collection = await CollectionRepository(db).create(payload.model_dump())
    collection["document_count"] = 0
    await ActivityService(ActivityRepository(db)).record(
        payload.workspace_id,
        user["id"],
        "created",
        "collection",
        f"Created collection {collection['name']}",
        collection["id"],
    )
    return collection


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: str, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> None:
    collection = await CollectionRepository(db).get(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    await require_workspace(db, user["id"], collection["workspace_id"], "editor")
    await CollectionRepository(db).delete(collection_id)
    await DocumentRepository(db).remove_collection_reference(collection_id)
    await ActivityService(ActivityRepository(db)).record(
        collection["workspace_id"], user["id"], "deleted", "collection", f"Deleted collection {collection['name']}"
    )
