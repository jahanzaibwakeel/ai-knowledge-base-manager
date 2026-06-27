import os
import unittest

from motor.motor_asyncio import AsyncIOMotorClient

from app.db.mongo import create_indexes
from app.repositories.domain import DocumentChunkRepository, DocumentRepository, WorkspaceRepository
from app.repositories.users import UserRepository
from app.services.rag import RAGService


@unittest.skipUnless(os.getenv("RUN_INTEGRATION_TESTS") == "1", "set RUN_INTEGRATION_TESTS=1 to run Mongo integration tests")
class MongoIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        uri = os.getenv("MONGO_URI", "mongodb://mongo:27017")
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[os.getenv("MONGO_DB", "knowledge_base_test")]
        await self.db.command("ping")
        await self.db.drop_collection("users")
        await self.db.drop_collection("workspaces")
        await self.db.drop_collection("documents")
        await self.db.drop_collection("document_chunks")
        await self.db.drop_collection("activities")
        await self.db.drop_collection("collections")
        await create_indexes(self.db)

    async def asyncTearDown(self):
        await self.client.drop_database(self.db.name)
        self.client.close()

    async def test_document_text_search_and_rag_indexing(self):
        user = await UserRepository(self.db).create(
            {"email": "integration@example.com", "name": "Integration", "password_hash": "hash"}
        )
        workspace = await WorkspaceRepository(self.db).create({"owner_id": user["id"], "name": "Research"})
        document = await DocumentRepository(self.db).create(
            {
                "workspace_id": workspace["id"],
                "title": "Mongo Notes",
                "source_type": "note",
                "filename": None,
                "content": "MongoDB stores documents and supports text search for knowledge bases.",
                "summary": "MongoDB text search notes.",
                "key_points": [],
                "action_items": [],
                "collection_ids": [],
                "tags": ["mongodb", "search"],
            }
        )

        await RAGService(self.db).index_document(document)

        documents = await DocumentRepository(self.db).search([workspace["id"]], "MongoDB")
        chunks = await DocumentChunkRepository(self.db).keyword_search([workspace["id"]], "knowledge")
        answer = await RAGService(self.db).ask(user["id"], "How does MongoDB help search?", limit=2)

        self.assertEqual(documents[0]["id"], document["id"])
        self.assertEqual(chunks[0]["document_id"], document["id"])
        self.assertEqual(answer["citations"][0]["document_id"], document["id"])


if __name__ == "__main__":
    unittest.main()
