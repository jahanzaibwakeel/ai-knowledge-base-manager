import os
import unittest

from app.core.config import get_settings
from app.services.ai import AIService
from app.services.embeddings import EmbeddingService, local_embed_text


class ZeroCostSafetyTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        for key in ["ZERO_COST_MODE", "AI_PROVIDER", "EMBEDDING_PROVIDER", "OPENAI_API_KEY"]:
            os.environ.pop(key, None)
        get_settings.cache_clear()

    async def test_zero_cost_mode_blocks_openai_ai_calls(self):
        os.environ["ZERO_COST_MODE"] = "true"
        os.environ["AI_PROVIDER"] = "openai"
        os.environ["OPENAI_API_KEY"] = "sk-test"
        get_settings.cache_clear()

        class GuardedAIService(AIService):
            async def _openai(self, title: str, content: str) -> dict:
                raise AssertionError("OpenAI should not be called when ZERO_COST_MODE=true")

        result = await GuardedAIService().analyze("Title", "Local fallback sentence.")

        self.assertIn("Local fallback sentence", result["summary"])

    async def test_zero_cost_mode_blocks_openai_embedding_calls(self):
        os.environ["ZERO_COST_MODE"] = "true"
        os.environ["EMBEDDING_PROVIDER"] = "openai"
        os.environ["OPENAI_API_KEY"] = "sk-test"
        get_settings.cache_clear()

        class GuardedEmbeddingService(EmbeddingService):
            async def _openai_many(self, texts: list[str]) -> list[list[float]]:
                raise AssertionError("OpenAI embeddings should not be called when ZERO_COST_MODE=true")

        vector = await GuardedEmbeddingService().embed("free local embedding")

        self.assertEqual(vector, local_embed_text("free local embedding", get_settings().embedding_dimensions))

    def test_safety_snapshot_reports_blocked_paid_providers(self):
        os.environ["ZERO_COST_MODE"] = "true"
        os.environ["AI_PROVIDER"] = "openai"
        os.environ["EMBEDDING_PROVIDER"] = "openai"
        os.environ["OPENAI_API_KEY"] = "sk-test"
        get_settings.cache_clear()

        snapshot = get_settings().safety_snapshot()

        self.assertTrue(snapshot["zero_cost_mode"])
        self.assertTrue(snapshot["paid_ai_blocked"])
        self.assertTrue(snapshot["paid_embeddings_blocked"])
        self.assertFalse(snapshot["billing_risk"])


if __name__ == "__main__":
    unittest.main()
