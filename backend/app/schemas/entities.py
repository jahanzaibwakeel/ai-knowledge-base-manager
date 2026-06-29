from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class WorkspaceOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    owner_id: str
    created_at: datetime
    updated_at: datetime


class WorkspaceMemberAdd(BaseModel):
    email: str
    role: str = Field(default="viewer", pattern="^(owner|editor|viewer)$")


class WorkspaceMemberUpdate(BaseModel):
    role: str = Field(pattern="^(owner|editor|viewer)$")


class WorkspaceOwnershipTransfer(BaseModel):
    user_id: str


class WorkspaceMemberOut(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    email: str
    name: str
    role: str
    created_at: datetime
    updated_at: datetime


class CollectionCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)


class CollectionOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


class NoteCreate(BaseModel):
    workspace_id: str
    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=200_000)
    collection_ids: list[str] = []
    tags: list[str] = []


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    content: str | None = Field(default=None, max_length=200_000)
    collection_ids: list[str] | None = None
    tags: list[str] | None = None


class DocumentVersionOut(BaseModel):
    id: str
    workspace_id: str
    document_id: str
    version: int
    actor_id: str
    reason: str
    snapshot: dict
    created_at: datetime
    updated_at: datetime


class DocumentOut(BaseModel):
    id: str
    workspace_id: str
    title: str
    source_type: str
    filename: str | None = None
    file_storage_path: str | None = None
    file_size_bytes: int | None = None
    analysis_status: str = "complete"
    archived_at: datetime | None = None
    content: str
    content_segments: list[dict] = []
    summary: str | None = None
    key_points: list[str] = []
    action_items: list[str] = []
    collection_ids: list[str] = []
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime


class ActivityOut(BaseModel):
    id: str
    workspace_id: str
    actor_id: str
    action: str
    entity_type: str
    entity_id: str | None = None
    message: str
    created_at: datetime


class DashboardOut(BaseModel):
    workspaces: list[dict]
    collections: list[dict]
    recent_documents: list[dict]
    insights: list[dict]
    activity: list[dict]
