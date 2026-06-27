import unittest

from scripts.prefetch_models import embedding_download_target, transformers_download_target


class PrefetchModelTests(unittest.TestCase):
    def test_embedding_target_uses_fastembed_model(self):
        self.assertEqual(
            embedding_download_target("fastembed", "sentence-transformers/all-MiniLM-L6-v2", "other/model"),
            "sentence-transformers/all-MiniLM-L6-v2",
        )

    def test_embedding_target_ignores_local_hash_provider(self):
        self.assertIsNone(embedding_download_target("local", "fast/model", "sentence/model"))

    def test_transformers_target_only_for_transformers_provider(self):
        self.assertEqual(transformers_download_target("transformers", "google/flan-t5-small"), "google/flan-t5-small")
        self.assertIsNone(transformers_download_target("local", "google/flan-t5-small"))


if __name__ == "__main__":
    unittest.main()
