import unittest

from app.repositories.domain import DocumentRepository


class DocumentRepositoryFilterTests(unittest.TestCase):
    def test_query_excludes_archived_by_default(self):
        repo = DocumentRepository.__new__(DocumentRepository)

        query = repo._query("workspace-1")

        self.assertEqual(query["workspace_id"], "workspace-1")
        self.assertIsNone(query["archived_at"])

    def test_query_can_include_filters_and_archived(self):
        repo = DocumentRepository.__new__(DocumentRepository)

        query = repo._query("workspace-1", collection_id="collection-1", tag="ai", include_archived=True)

        self.assertEqual(query["collection_ids"], "collection-1")
        self.assertEqual(query["tags"], "ai")
        self.assertNotIn("archived_at", query)


if __name__ == "__main__":
    unittest.main()
