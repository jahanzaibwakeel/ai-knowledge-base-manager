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


if __name__ == "__main__":
    unittest.main()
