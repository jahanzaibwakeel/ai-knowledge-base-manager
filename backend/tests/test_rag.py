import os
import unittest

from app.core.config import get_settings
from app.services.rag import chunk_segments, chunk_text, chunks_for_document, cosine, embed_text


class RAGTests(unittest.TestCase):
    def test_chunk_text_overlaps_long_content(self):
        content = " ".join(f"word{i}" for i in range(300))

        chunks = chunk_text(content, chunk_size=120, overlap=20)

        self.assertGreater(len(chunks), 1)
        self.assertLessEqual(len(chunks[0]), 120)

    def test_embed_text_is_normalized_and_stable(self):
        first = embed_text("MongoDB knowledge search")
        second = embed_text("MongoDB knowledge search")

        self.assertEqual(first, second)
        self.assertAlmostEqual(cosine(first, first), 1.0)

    def test_related_text_scores_higher_than_unrelated_text(self):
        query = embed_text("workspace document search")

        related = cosine(query, embed_text("search documents inside workspace"))
        unrelated = cosine(query, embed_text("banana orange pear"))

        self.assertGreater(related, unrelated)

    def test_chunk_segments_preserves_page_and_paragraph_refs(self):
        segments = [
            {"text": "Alpha strategy", "page_number": 2, "paragraph_index": 1},
            {"text": "Beta execution", "page_number": 2, "paragraph_index": 2},
        ]

        chunks = chunk_segments(segments)

        self.assertEqual(chunks[0]["source_refs"][0]["label"], "page 2, paragraph 1")
        self.assertEqual(chunks[0]["source_refs"][1]["label"], "page 2, paragraph 2")


class RAGEvaluationTests(unittest.IsolatedAsyncioTestCase):
    async def test_chunks_for_document_embeds_and_keeps_citations(self):
        previous_provider = os.environ.get("EMBEDDING_PROVIDER")
        os.environ["EMBEDDING_PROVIDER"] = "local"
        get_settings.cache_clear()
        document = {
            "content": "Alpha strategy\n\nBeta execution",
            "content_segments": [
                {"text": "Alpha strategy", "page_number": None, "paragraph_index": 1},
                {"text": "Beta execution", "page_number": None, "paragraph_index": 2},
            ],
        }

        try:
            chunks = await chunks_for_document(document)
        finally:
            if previous_provider is None:
                os.environ.pop("EMBEDDING_PROVIDER", None)
            else:
                os.environ["EMBEDDING_PROVIDER"] = previous_provider
            get_settings.cache_clear()

        self.assertEqual(chunks[0]["source_refs"][0]["label"], "paragraph 1")
        self.assertIn("embedding", chunks[0])
        self.assertGreater(cosine(embed_text("strategy"), chunks[0]["embedding"]), 0)

    async def test_chunks_record_sentence_transformer_model_metadata(self):
        previous_provider = os.environ.get("EMBEDDING_PROVIDER")
        previous_model = os.environ.get("SENTENCE_TRANSFORMER_MODEL")
        os.environ["EMBEDDING_PROVIDER"] = "sentence-transformers"
        os.environ["SENTENCE_TRANSFORMER_MODEL"] = "sentence-transformers/test-model"
        get_settings.cache_clear()

        class FakeEmbeddings:
            async def embed_many(self, texts):
                return [[1.0, 0.0] for _text in texts]

        try:
            chunks = await chunks_for_document({"content": "Alpha strategy"}, FakeEmbeddings())
        finally:
            if previous_provider is None:
                os.environ.pop("EMBEDDING_PROVIDER", None)
            else:
                os.environ["EMBEDDING_PROVIDER"] = previous_provider
            if previous_model is None:
                os.environ.pop("SENTENCE_TRANSFORMER_MODEL", None)
            else:
                os.environ["SENTENCE_TRANSFORMER_MODEL"] = previous_model
            get_settings.cache_clear()

        self.assertEqual(chunks[0]["embedding_provider"], "sentence-transformers")
        self.assertEqual(chunks[0]["embedding_model"], "sentence-transformers/test-model")


if __name__ == "__main__":
    unittest.main()
