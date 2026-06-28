import json
import unittest

from app.api.routes.rag import answer_chunks, sse_event, stream_rag_answer


class RAGStreamingTests(unittest.IsolatedAsyncioTestCase):
    def test_sse_event_formats_json_payload(self):
        event = sse_event("token", {"text": "hello"})

        self.assertEqual(event, 'event: token\ndata: {"text":"hello"}\n\n')

    def test_answer_chunks_preserve_answer_text(self):
        answer = "one two three four five six seven eight nine"

        chunks = answer_chunks(answer, chunk_words=3)

        self.assertEqual("".join(chunks), answer)
        self.assertEqual(len(chunks), 3)

    async def test_stream_rag_answer_yields_status_citations_tokens_and_done(self):
        class FakeService:
            async def ask(self, user_id: str, query: str, limit: int) -> dict:
                self.calls = (user_id, query, limit)
                return {
                    "answer": "alpha beta",
                    "citations": [{"document_id": "doc-1", "document_title": "Doc", "chunk_index": 0, "text": "alpha"}],
                }

        service = FakeService()

        events = [event async for event in stream_rag_answer(service, "user-1", "question", 2)]

        self.assertIn("event: status", events[0])
        self.assertIn("event: citations", events[1])
        self.assertIn("event: token", events[3])
        self.assertIn("event: done", events[-1])
        done_payload = json.loads(events[-1].split("data: ", 1)[1])
        self.assertEqual(done_payload["answer"], "alpha beta")
        self.assertEqual(service.calls, ("user-1", "question", 2))


if __name__ == "__main__":
    unittest.main()
