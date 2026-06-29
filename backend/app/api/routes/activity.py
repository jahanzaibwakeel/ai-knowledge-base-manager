from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import current_user, get_db
from app.api.routes.workspaces import accessible_workspaces
from app.repositories.domain import ActivityRepository

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("")
async def activity_timeline(
    workspace_id: str | None = None,
    action: str | None = Query(default=None, max_length=80),
    entity_type: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    workspaces = await accessible_workspaces(db, user["id"])
    workspace_ids = [workspace["id"] for workspace in workspaces]
    repository = ActivityRepository(db)
    return {
        "items": await repository.list_for_workspaces(
            workspace_ids,
            workspace_id=workspace_id,
            action=action,
            entity_type=entity_type,
            limit=limit,
            skip=offset,
        ),
        "total": await repository.count_for_workspaces(
            workspace_ids,
            workspace_id=workspace_id,
            action=action,
            entity_type=entity_type,
        ),
        "limit": limit,
        "offset": offset,
    }
