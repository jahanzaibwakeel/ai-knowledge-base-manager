from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

client: AsyncIOMotorClient | None = None


async def connect_to_mongo() -> None:
    global client
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongo_uri)
    await get_database().command("ping")
    await create_indexes(get_database())


async def close_mongo_connection() -> None:
    if client:
        client.close()


def get_database() -> AsyncIOMotorDatabase:
    if client is None:
        settings = get_settings()
        return AsyncIOMotorClient(settings.mongo_uri)[settings.mongo_db]
    return client[get_settings().mongo_db]


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_index("email", unique=True)
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.password_reset_tokens.create_index([("user_id", 1), ("used_at", 1)])
    await db.workspaces.create_index([("owner_id", 1), ("archived_at", 1), ("name", 1)])
    await db.workspace_members.create_index([("workspace_id", 1), ("user_id", 1)], unique=True)
    await db.workspace_members.create_index([("user_id", 1), ("role", 1)])
    await db.collections.create_index([("workspace_id", 1), ("name", 1)])
    await db.documents.create_index([("workspace_id", 1), ("archived_at", 1), ("created_at", -1)])
    await db.documents.create_index([("workspace_id", 1), ("collection_ids", 1), ("tags", 1)])
    await db.document_versions.create_index([("document_id", 1), ("version", -1)], unique=True)
    await db.document_versions.create_index([("workspace_id", 1), ("created_at", -1)])
    await db.documents.create_index(
        [("title", "text"), ("content", "text"), ("summary", "text"), ("tags", "text")],
        name="document_text_index",
        default_language="english",
    )
    await db.activities.create_index([("workspace_id", 1), ("created_at", -1)])
    await db.analysis_jobs.create_index([("workspace_id", 1), ("created_at", -1)])
    await db.analysis_jobs.create_index([("document_id", 1), ("status", 1)])
    await db.rag_feedback.create_index([("user_id", 1), ("created_at", -1)])
    await db.rag_feedback.create_index([("workspace_ids", 1), ("rating", 1)])
    await db.document_chunks.create_index([("workspace_id", 1), ("document_id", 1)])
    await db.document_chunks.create_index(
        [("text", "text"), ("document_title", "text"), ("tags", "text")],
        name="chunk_text_index",
        default_language="english",
    )
