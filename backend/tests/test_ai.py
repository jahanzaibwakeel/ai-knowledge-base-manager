import os
import unittest

from app.core.config import get_settings
from app.services.ai import AIService


class AIServiceTests(unittest.TestCase):
    def test_fallback_returns_summary_key_points_and_actions(self):
        content = "First useful point. Second useful point.\nThird useful point."

        result = AIService()._fallback(content)

        self.assertIn("First useful point", result["summary"])
        self.assertEqual(result["key_points"], ["First useful point", "Second useful point", "Third useful point"])
        self.assertEqual(result["action_items"], [])

    def test_coerce_normalizes_shape_and_limits_lists(self):
        payload = {
            "summary": 123,
            "key_points": list(range(12)),
            "action_items": ["follow up", 9],
        }

        result = AIService()._coerce(payload)

        self.assertEqual(result["summary"], "123")
        self.assertEqual(len(result["key_points"]), 10)
        self.assertEqual(result["key_points"][0], "0")
        self.assertEqual(result["action_items"], ["follow up", "9"])


class LocalTransformersAIServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_transformers_provider_can_summarize_without_ollama(self):
        previous_provider = os.environ.get("AI_PROVIDER")
        os.environ["AI_PROVIDER"] = "transformers"
        get_settings.cache_clear()

        class TestAIService(AIService):
            def _load_transformers_pipeline(self, model_name: str):
                def fake_pipeline(prompt: str, **_kwargs):
                    return [{"generated_text": "Local model summary"}]

                return fake_pipeline

        try:
            result = await TestAIService().analyze("Title", "First point. Second point.")
        finally:
            if previous_provider is None:
                os.environ.pop("AI_PROVIDER", None)
            else:
                os.environ["AI_PROVIDER"] = previous_provider
            get_settings.cache_clear()

        self.assertEqual(result["summary"], "Local model summary")
        self.assertEqual(result["key_points"], ["First point", "Second point"])


if __name__ == "__main__":
    unittest.main()
