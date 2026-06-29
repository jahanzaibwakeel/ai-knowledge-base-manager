import unittest

from app.services.rag_eval import evaluate_rag_answer


class RAGEvalTests(unittest.TestCase):
    def test_evaluation_passes_when_terms_and_citations_match(self):
        result = evaluate_rag_answer(
            "MongoDB Atlas supports managed search for documents.",
            [{"document_id": "doc-1"}],
            ["MongoDB", "Atlas", "search"],
            min_citations=1,
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["term_recall"], 1.0)
        self.assertEqual(result["missing_terms"], [])

    def test_evaluation_fails_when_terms_are_missing(self):
        result = evaluate_rag_answer("MongoDB is configured.", [], ["MongoDB", "Atlas"], min_citations=1)

        self.assertFalse(result["passed"])
        self.assertEqual(result["missing_terms"], ["atlas"])
        self.assertEqual(result["citation_count"], 0)


if __name__ == "__main__":
    unittest.main()
