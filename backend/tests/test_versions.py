import unittest

from app.repositories.domain import DocumentVersionRepository


class FakeVersions:
    def __init__(self):
        self.docs = []

    async def find_one(self, query, sort=None):
        matches = [doc for doc in self.docs if doc["document_id"] == query["document_id"]]
        if not matches:
            return None
        return sorted(matches, key=lambda item: item["version"], reverse=True)[0]


class DocumentVersionTests(unittest.IsolatedAsyncioTestCase):
    async def test_next_version_starts_at_one(self):
        repo = DocumentVersionRepository.__new__(DocumentVersionRepository)
        repo.collection = FakeVersions()

        self.assertEqual(await repo.next_version("doc-1"), 1)

    async def test_next_version_increments_latest(self):
        repo = DocumentVersionRepository.__new__(DocumentVersionRepository)
        fake = FakeVersions()
        fake.docs = [{"document_id": "doc-1", "version": 2}, {"document_id": "doc-1", "version": 1}]
        repo.collection = fake

        self.assertEqual(await repo.next_version("doc-1"), 3)


if __name__ == "__main__":
    unittest.main()
