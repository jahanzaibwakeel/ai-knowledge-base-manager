from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import current_user, get_db
from app.repositories.domain import ActivityRepository, CollectionRepository, DocumentRepository, WorkspaceMemberRepository, WorkspaceRepository
from app.repositories.users import UserRepository
from app.schemas.entities import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberUpdate,
    WorkspaceOut,
    WorkspaceOwnershipTransfer,
    WorkspaceUpdate,
)
from app.services.activity import ActivityService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

ROLE_LEVELS = {"viewer": 1, "editor": 2, "owner": 3}


async def require_workspace(
    db: AsyncIOMotorDatabase, user_id: str, workspace_id: str, minimum_role: str = "viewer"
) -> dict:
    workspace = await WorkspaceRepository(db).get(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    role = "owner" if workspace["owner_id"] == user_id else None
    if role is None:
        member = await WorkspaceMemberRepository(db).get_member(workspace_id, user_id)
        role = member["role"] if member else None
    if role is None or ROLE_LEVELS[role] < ROLE_LEVELS[minimum_role]:
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace["current_user_role"] = role
    return workspace


async def accessible_workspaces(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    workspaces = {workspace["id"]: workspace for workspace in await WorkspaceRepository(db).list_for_user(user_id)}
    memberships = await WorkspaceMemberRepository(db).list_for_user(user_id)
    for membership in memberships:
        workspace = await WorkspaceRepository(db).get(membership["workspace_id"])
        if workspace:
            workspaces[workspace["id"]] = workspace
    return sorted(workspaces.values(), key=lambda item: item["updated_at"], reverse=True)


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)) -> list[dict]:
    return await accessible_workspaces(db, user["id"])


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    workspace = await WorkspaceRepository(db).create({**payload.model_dump(), "owner_id": user["id"]})
    await WorkspaceMemberRepository(db).create(
        {
            "workspace_id": workspace["id"],
            "user_id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": "owner",
        }
    )
    await ActivityService(ActivityRepository(db)).record(
        workspace["id"], user["id"], "created", "workspace", f"Created workspace {workspace['name']}", workspace["id"]
    )
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: str,
    payload: WorkspaceUpdate,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    await require_workspace(db, user["id"], workspace_id, "owner")
    workspace = await WorkspaceRepository(db).update(workspace_id, payload.model_dump(exclude_unset=True))
    await ActivityService(ActivityRepository(db)).record(
        workspace_id, user["id"], "updated", "workspace", f"Updated workspace {workspace['name']}", workspace_id
    )
    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> None:
    await require_workspace(db, user["id"], workspace_id, "owner")
    await WorkspaceRepository(db).delete(workspace_id)
    await db.collections.delete_many({"workspace_id": workspace_id})
    await db.documents.delete_many({"workspace_id": workspace_id})
    await db.activities.delete_many({"workspace_id": workspace_id})
    await db.workspace_members.delete_many({"workspace_id": workspace_id})
    await db.document_chunks.delete_many({"workspace_id": workspace_id})
    await db.analysis_jobs.delete_many({"workspace_id": workspace_id})


@router.get("/{workspace_id}/collections")
async def workspace_collections(
    workspace_id: str, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> list[dict]:
    await require_workspace(db, user["id"], workspace_id)
    collections = await CollectionRepository(db).list_for_workspace(workspace_id)
    for collection in collections:
        collection["document_count"] = await db.documents.count_documents({"collection_ids": collection["id"]})
    return collections


@router.get("/{workspace_id}/documents")
async def workspace_documents(
    workspace_id: str,
    limit: int = 25,
    offset: int = 0,
    collection_id: str | None = None,
    tag: str | None = None,
    include_archived: bool = False,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    await require_workspace(db, user["id"], workspace_id)
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    documents = await DocumentRepository(db).list_for_workspace(
        workspace_id,
        limit=limit,
        skip=offset,
        collection_id=collection_id,
        tag=tag,
        include_archived=include_archived,
    )
    total = await DocumentRepository(db).count_for_workspace(
        workspace_id, collection_id=collection_id, tag=tag, include_archived=include_archived
    )
    return {"items": documents, "total": total, "limit": limit, "offset": offset}


@router.get("/{workspace_id}/export")
async def export_workspace(
    workspace_id: str, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    workspace = await require_workspace(db, user["id"], workspace_id)
    collections = await CollectionRepository(db).list_for_workspace(workspace_id)
    documents = await DocumentRepository(db).list_for_workspace(workspace_id, limit=1000, include_archived=True)
    activity = await ActivityRepository(db).list_for_workspace(workspace_id, limit=1000)
    return {"workspace": workspace, "collections": collections, "documents": documents, "activity": activity}


@router.get("/{workspace_id}/members")
async def workspace_members(
    workspace_id: str, user: dict = Depends(current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> list[dict]:
    await require_workspace(db, user["id"], workspace_id)
    return await WorkspaceMemberRepository(db).list_for_workspace(workspace_id)


@router.post("/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: str,
    payload: WorkspaceMemberAdd,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    await require_workspace(db, user["id"], workspace_id, "owner")
    invited = await UserRepository(db).get_by_email(payload.email)
    if not invited:
        raise HTTPException(status_code=404, detail="User must register before being added to a workspace")
    existing = await WorkspaceMemberRepository(db).get_member(workspace_id, invited["id"])
    member_payload = {
        "workspace_id": workspace_id,
        "user_id": invited["id"],
        "email": invited["email"],
        "name": invited["name"],
        "role": payload.role,
    }
    if existing:
        return await WorkspaceMemberRepository(db).update(existing["id"], member_payload)
    member = await WorkspaceMemberRepository(db).create(member_payload)
    await ActivityService(ActivityRepository(db)).record(
        workspace_id, user["id"], "added", "workspace_member", f"Added {invited['email']} as {payload.role}", member["id"]
    )
    return member


@router.patch("/{workspace_id}/members/{member_id}")
async def update_workspace_member(
    workspace_id: str,
    member_id: str,
    payload: WorkspaceMemberUpdate,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    workspace = await require_workspace(db, user["id"], workspace_id, "owner")
    member = await WorkspaceMemberRepository(db).get(member_id)
    if not member or member["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Workspace member not found")
    if member["user_id"] == workspace["owner_id"] and payload.role != "owner":
        raise HTTPException(status_code=400, detail="Transfer workspace ownership before downgrading this owner")
    updated = await WorkspaceMemberRepository(db).update(member_id, {"role": payload.role})
    await ActivityService(ActivityRepository(db)).record(
        workspace_id, user["id"], "updated", "workspace_member", f"Updated {member['email']} to {payload.role}", member_id
    )
    return updated


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: str,
    member_id: str,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    workspace = await require_workspace(db, user["id"], workspace_id, "owner")
    member = await WorkspaceMemberRepository(db).get(member_id)
    if not member or member["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Workspace member not found")
    if member["user_id"] == workspace["owner_id"]:
        raise HTTPException(status_code=400, detail="Transfer workspace ownership before removing this owner")
    await WorkspaceMemberRepository(db).delete_member(workspace_id, member_id)
    await ActivityService(ActivityRepository(db)).record(
        workspace_id, user["id"], "removed", "workspace_member", f"Removed {member['email']}", member_id
    )


@router.post("/{workspace_id}/transfer-ownership")
async def transfer_workspace_ownership(
    workspace_id: str,
    payload: WorkspaceOwnershipTransfer,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    workspace = await require_workspace(db, user["id"], workspace_id, "owner")
    member = await WorkspaceMemberRepository(db).get_member(workspace_id, payload.user_id)
    if not member:
        raise HTTPException(status_code=404, detail="New owner must be a workspace member")
    updated_workspace = await WorkspaceRepository(db).update(workspace_id, {"owner_id": payload.user_id})
    await WorkspaceMemberRepository(db).update(member["id"], {"role": "owner"})
    current_owner = await WorkspaceMemberRepository(db).get_member(workspace_id, workspace["owner_id"])
    if current_owner and current_owner["user_id"] != payload.user_id:
        await WorkspaceMemberRepository(db).update(current_owner["id"], {"role": "editor"})
    await ActivityService(ActivityRepository(db)).record(
        workspace_id, user["id"], "transferred", "workspace", f"Transferred ownership to {member['email']}", workspace_id
    )
    return updated_workspace
