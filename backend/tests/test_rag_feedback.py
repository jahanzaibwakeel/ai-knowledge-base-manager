import unittest

from pydantic import ValidationError

from app.api.routes.rag import RAGFeedback
from app.repositories.domain import RAGFeedbackRepository


class FakeAggregateCollection:
    def aggregate(self, pipeline):
        self.pipeline = pipeline
        return self

    async def __aiter__(self):
        for row in [{"_id": "helpful", "count": 3}, {"_id": "not_helpful", "count": 1}]:
            yield row


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.sort_args = None
        self.skip_value = None
        self.limit_value = None

    def sort(self, *args):
        self.sort_args = args
        return self

    def skip(self, value):
        self.skip_value = value
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    async def __aiter__(self):
        for row in self.rows:
            yield row


class FakeFeedbackCollection:
    def __init__(self):
        self.query = None
        self.cursor = FakeCursor(
            [
                {
                    "_id": "feedback-1",
                    "workspace_ids": ["workspace-1"],
                    "query": "Question?",
                    "answer": "Answer",
                    "rating": "not_helpful",
                    "citations": [],
                }
            ]
        )

    def find(self, query):
        self.query = query
        return self.cursor

    async def count_documents(self, query):
        self.count_query = query
        return 1


class RAGFeedbackTests(unittest.IsolatedAsyncioTestCase):
    def test_feedback_rejects_invalid_rating(self):
        with self.assertRaises(ValidationError):
            RAGFeedback(query="Is this useful?", answer="Yes", rating="maybe")

    def test_feedback_accepts_valid_payload(self):
        feedback = RAGFeedback(query="Is this useful?", answer="Yes", rating="helpful", citations=[])

        self.assertEqual(feedback.rating, "helpful")

    async def test_feedback_summary_counts_ratings(self):
        repo = RAGFeedbackRepository.__new__(RAGFeedbackRepository)
        repo.collection = FakeAggregateCollection()

        summary = await repo.summary_for_workspaces(["workspace-1"])

        self.assertEqual(summary, {"helpful": 3, "not_helpful": 1, "total": 4})
        self.assertEqual(repo.collection.pipeline[0]["$match"], {"workspace_ids": {"$in": ["workspace-1"]}})

    async def test_feedback_review_filters_by_workspace_and_rating(self):
        repo = RAGFeedbackRepository.__new__(RAGFeedbackRepository)
        repo.collection = FakeFeedbackCollection()

        items = await repo.list_for_workspaces(["workspace-1"], rating="not_helpful", limit=10, skip=5)
        total = await repo.count_for_workspaces(["workspace-1"], rating="not_helpful")

        expected_query = {"workspace_ids": {"$in": ["workspace-1"]}, "rating": "not_helpful"}
        self.assertEqual(repo.collection.query, expected_query)
        self.assertEqual(repo.collection.count_query, expected_query)
        self.assertEqual(repo.collection.cursor.sort_args, ("created_at", -1))
        self.assertEqual(repo.collection.cursor.skip_value, 5)
        self.assertEqual(repo.collection.cursor.limit_value, 10)
        self.assertEqual(total, 1)
        self.assertEqual(items[0]["id"], "feedback-1")


if __name__ == "__main__":
    unittest.main()
