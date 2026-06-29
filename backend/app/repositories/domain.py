from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.common import now_utc
from app.repositories.base import MongoRepository, oid, serialize


class WorkspaceRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.workspaces)

    async def list_for_user(self, user_id: str, include_archived: bool = False) -> list[dict]:
        query = {"owner_id": user_id}
        if not include_archived:
            query["archived_at"] = None
        cursor = self.collection.find(query).sort("updated_at", -1)
        return [serialize(doc) async for doc in cursor]


class WorkspaceMemberRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.workspace_members)

    async def get_member(self, workspace_id: str, user_id: str) -> dict | None:
        return serialize(await self.collection.find_one({"workspace_id": workspace_id, "user_id": user_id}))

    async def list_for_user(self, user_id: str) -> list[dict]:
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1)
        return [serialize(doc) async for doc in cursor]

    async def list_for_workspace(self, workspace_id: str) -> list[dict]:
        cursor = self.collection.find({"workspace_id": workspace_id}).sort("role", 1)
        return [serialize(doc) async for doc in cursor]


class CollectionRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.collections)

    async def list_for_workspace(self, workspace_id: str) -> list[dict]:
        cursor = self.collection.find({"workspace_id": workspace_id}).sort("name", 1)
        return [serialize(doc) async for doc in cursor]


class DocumentRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.documents)

    def _query(
        self,
        workspace_id: str | None = None,
        *,
        workspace_ids: list[str] | None = None,
        collection_id: str | None = None,
        tag: str | None = None,
        include_archived: bool = False,
    ) -> dict:
        query: dict = {}
        if workspace_id:
            query["workspace_id"] = workspace_id
        if workspace_ids is not None:
            query["workspace_id"] = {"$in": workspace_ids}
        if collection_id:
            query["collection_ids"] = collection_id
        if tag:
            query["tags"] = tag
        if not include_archived:
            query["archived_at"] = None
        return query

    async def list_for_workspace(
        self,
        workspace_id: str,
        limit: int = 50,
        skip: int = 0,
        collection_id: str | None = None,
        tag: str | None = None,
        include_archived: bool = False,
    ) -> list[dict]:
        cursor = (
            self.collection.find(
                self._query(workspace_id, collection_id=collection_id, tag=tag, include_archived=include_archived)
            )
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [serialize(doc) async for doc in cursor]

    async def count_for_workspace(
        self,
        workspace_id: str,
        collection_id: str | None = None,
        tag: str | None = None,
        include_archived: bool = False,
    ) -> int:
        return await self.collection.count_documents(
            self._query(workspace_id, collection_id=collection_id, tag=tag, include_archived=include_archived)
        )

    async def search(
        self,
        user_workspace_ids: list[str],
        query: str,
        limit: int = 25,
        skip: int = 0,
        include_archived: bool = False,
    ) -> list[dict]:
        search_query = self._query(workspace_ids=user_workspace_ids, include_archived=include_archived)
        search_query["$text"] = {"$search": query}
        cursor = (
            self.collection.find(
                search_query,
                {"score": {"$meta": "textScore"}},
            )
            .sort([("score", {"$meta": "textScore"})])
            .skip(skip)
            .limit(limit)
        )
        return [serialize(doc) async for doc in cursor]

    async def archive(self, document_id: str) -> dict | None:
        return await self.update(document_id, {"archived_at": now_utc()})

    async def restore(self, document_id: str) -> dict | None:
        await self.collection.update_one({"_id": oid(document_id)}, {"$set": {"archived_at": None, "updated_at": now_utc()}})
        return await self.get(document_id)

    async def remove_collection_reference(self, collection_id: str) -> None:
        await self.collection.update_many({"collection_ids": collection_id}, {"$pull": {"collection_ids": collection_id}})


class DocumentVersionRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.document_versions)

    async def next_version(self, document_id: str) -> int:
        latest = await self.collection.find_one({"document_id": document_id}, sort=[("version", -1)])
        return int(latest["version"]) + 1 if latest else 1

    async def create_from_document(self, document: dict, actor_id: str, reason: str) -> dict:
        version = await self.next_version(document["id"])
        return await self.create(
            {
                "workspace_id": document["workspace_id"],
                "document_id": document["id"],
                "version": version,
                "actor_id": actor_id,
                "reason": reason,
                "snapshot": {
                    "title": document["title"],
                    "content": document["content"],
                    "content_segments": document.get("content_segments", []),
                    "summary": document.get("summary"),
                    "key_points": document.get("key_points", []),
                    "action_items": document.get("action_items", []),
                    "collection_ids": document.get("collection_ids", []),
                    "tags": document.get("tags", []),
                    "analysis_status": document.get("analysis_status", "complete"),
                },
            }
        )

    async def list_for_document(self, document_id: str, limit: int = 25) -> list[dict]:
        cursor = self.collection.find({"document_id": document_id}).sort("version", -1).limit(limit)
        return [serialize(doc) async for doc in cursor]

    async def get_version(self, document_id: str, version: int) -> dict | None:
        return serialize(await self.collection.find_one({"document_id": document_id, "version": version}))


class DocumentChunkRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.document_chunks)

    async def replace_for_document(self, document: dict, chunks: list[dict]) -> None:
        await self.collection.delete_many({"document_id": document["id"]})
        if not chunks:
            return
        timestamp = now_utc()
        await self.collection.insert_many(
            [
                {
                    **chunk,
                    "workspace_id": document["workspace_id"],
                    "document_id": document["id"],
                    "document_title": document["title"],
                    "tags": document.get("tags", []),
                    "embedding_provider": chunk.get("embedding_provider"),
                    "embedding_model": chunk.get("embedding_model"),
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
                for chunk in chunks
            ]
        )

    async def delete_for_document(self, document_id: str) -> None:
        await self.collection.delete_many({"document_id": document_id})

    async def keyword_search(self, workspace_ids: list[str], query: str, limit: int = 50) -> list[dict]:
        cursor = (
            self.collection.find(
                {"workspace_id": {"$in": workspace_ids}, "$text": {"$search": query}},
                {"score": {"$meta": "textScore"}},
            )
            .sort([("score", {"$meta": "textScore"})])
            .limit(limit)
        )
        return [serialize(doc) async for doc in cursor]

    async def list_for_workspaces(self, workspace_ids: list[str], limit: int = 300) -> list[dict]:
        cursor = self.collection.find({"workspace_id": {"$in": workspace_ids}}).limit(limit)
        return [serialize(doc) async for doc in cursor]


class ActivityRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.activities)

    async def list_for_workspace(self, workspace_id: str, limit: int = 30) -> list[dict]:
        cursor = self.collection.find({"workspace_id": workspace_id}).sort("created_at", -1).limit(limit)
        return [serialize(doc) async for doc in cursor]

    def _query(
        self,
        workspace_ids: list[str],
        *,
        workspace_id: str | None = None,
        action: str | None = None,
        entity_type: str | None = None,
    ) -> dict:
        query: dict = {"workspace_id": {"$in": workspace_ids}}
        if workspace_id:
            query["workspace_id"] = workspace_id
        if action:
            query["action"] = action
        if entity_type:
            query["entity_type"] = entity_type
        return query

    async def list_for_workspaces(
        self,
        workspace_ids: list[str],
        *,
        workspace_id: str | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[dict]:
        if not workspace_ids:
            return []
        if workspace_id and workspace_id not in workspace_ids:
            return []
        cursor = (
            self.collection.find(
                self._query(workspace_ids, workspace_id=workspace_id, action=action, entity_type=entity_type)
            )
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [serialize(doc) async for doc in cursor]

    async def count_for_workspaces(
        self,
        workspace_ids: list[str],
        *,
        workspace_id: str | None = None,
        action: str | None = None,
        entity_type: str | None = None,
    ) -> int:
        if not workspace_ids or (workspace_id and workspace_id not in workspace_ids):
            return 0
        return await self.collection.count_documents(
            self._query(workspace_ids, workspace_id=workspace_id, action=action, entity_type=entity_type)
        )


class AnalysisJobRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.analysis_jobs)

    async def list_for_document(self, document_id: str, limit: int = 10) -> list[dict]:
        cursor = self.collection.find({"document_id": document_id}).sort("created_at", -1).limit(limit)
        return [serialize(doc) async for doc in cursor]


class RAGFeedbackRepository(MongoRepository):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db.rag_feedback)

    def _query(self, workspace_ids: list[str], rating: str | None = None) -> dict:
        query: dict = {"workspace_ids": {"$in": workspace_ids}}
        if rating:
            query["rating"] = rating
        return query

    async def list_for_workspaces(
        self,
        workspace_ids: list[str],
        *,
        rating: str | None = None,
        limit: int = 25,
        skip: int = 0,
    ) -> list[dict]:
        if not workspace_ids:
            return []
        cursor = (
            self.collection.find(self._query(workspace_ids, rating))
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [serialize(doc) async for doc in cursor]

    async def count_for_workspaces(self, workspace_ids: list[str], rating: str | None = None) -> int:
        if not workspace_ids:
            return 0
        return await self.collection.count_documents(self._query(workspace_ids, rating))

    async def summary_for_workspaces(self, workspace_ids: list[str]) -> dict:
        if not workspace_ids:
            return {"helpful": 0, "not_helpful": 0, "total": 0}
        pipeline = [
            {"$match": {"workspace_ids": {"$in": workspace_ids}}},
            {"$group": {"_id": "$rating", "count": {"$sum": 1}}},
        ]
        counts = {"helpful": 0, "not_helpful": 0}
        async for row in self.collection.aggregate(pipeline):
            if row["_id"] in counts:
                counts[row["_id"]] = row["count"]
        return {**counts, "total": counts["helpful"] + counts["not_helpful"]}
