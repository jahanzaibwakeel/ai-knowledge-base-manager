import unittest
from io import BytesIO

from fastapi import UploadFile

from app.services.parser import extract_document_text, extract_text


class ParserTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_text_reads_txt_uploads(self):
        upload = UploadFile(filename="note.txt", file=BytesIO(b"hello knowledge base"))

        filename, text = await extract_text(upload)

        self.assertEqual(filename, "note.txt")
        self.assertEqual(text, "hello knowledge base")

    async def test_extract_document_text_keeps_paragraph_references(self):
        upload = UploadFile(filename="note.md", file=BytesIO(b"First paragraph.\n\nSecond paragraph."))

        extracted = await extract_document_text(upload)

        self.assertEqual(extracted.content, "First paragraph.\n\nSecond paragraph.")
        self.assertEqual(extracted.segments[0]["paragraph_index"], 1)
        self.assertEqual(extracted.segments[1]["paragraph_index"], 2)
        self.assertIsNone(extracted.segments[0]["page_number"])

    async def test_extract_text_rejects_unsupported_extensions(self):
        upload = UploadFile(filename="image.png", file=BytesIO(b"not text"))

        with self.assertRaisesRegex(ValueError, "Only PDF, TXT, and Markdown"):
            await extract_text(upload)

    async def test_extract_text_rejects_empty_text(self):
        upload = UploadFile(filename="empty.md", file=BytesIO(b"   \n"))

        with self.assertRaisesRegex(ValueError, "No readable text"):
            await extract_text(upload)


if __name__ == "__main__":
    unittest.main()
