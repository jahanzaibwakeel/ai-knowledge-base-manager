from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader

from app.core.config import get_settings


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}


class ExtractedTextTooLargeError(ValueError):
    pass


@dataclass
class ExtractedDocument:
    filename: str
    content: str
    segments: list[dict]


def _paragraph_segments(text: str, page_number: int | None = None) -> list[dict]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    return [
        {"text": paragraph, "page_number": page_number, "paragraph_index": index + 1}
        for index, paragraph in enumerate(paragraphs)
    ]


async def extract_text(upload: UploadFile) -> tuple[str, str]:
    extracted = await extract_document_text(upload)
    return extracted.filename, extracted.content


async def extract_document_text(upload: UploadFile) -> ExtractedDocument:
    settings = get_settings()
    filename = upload.filename or "document"
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only PDF, TXT, and Markdown files are supported.")

    content = await upload.read()
    segments: list[dict]
    if ext == ".pdf":
        from io import BytesIO

        reader = PdfReader(BytesIO(content))
        segments = []
        for page_index, page in enumerate(reader.pages):
            page_text = (page.extract_text() or "").strip()
            segments.extend(_paragraph_segments(page_text, page_index + 1))
        text = "\n\n".join(segment["text"] for segment in segments).strip()
    else:
        text = content.decode("utf-8", errors="replace").strip()
        segments = _paragraph_segments(text)

    if not text:
        raise ValueError("No readable text could be extracted from the uploaded file.")
    if len(text) > settings.max_document_chars:
        raise ExtractedTextTooLargeError(
            f"Extracted document text exceeds {settings.max_document_chars} character limit."
        )
    return ExtractedDocument(filename=filename, content=text, segments=segments)
