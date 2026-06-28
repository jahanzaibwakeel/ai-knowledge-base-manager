import re

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.repositories.domain import DocumentChunkRepository, WorkspaceMemberRepository, WorkspaceRepository
from app.services.ai import AIService
from app.services.embeddings import EmbeddingService, cosine, local_embed_text


def chunk_text(content: str, chunk_size: int = 900, overlap: int = 140) -> list[str]:
    normalized = re.sub(r"\s+", " ", content).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end].strip())
        if end == len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def embed_text(text: str, dimensions: int = 128) -> list[float]:
    return local_embed_text(text, dimensions)


def _segments_for_content(content: str) -> list[dict]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", content) if paragraph.strip()]
    return [
        {"text": paragraph, "page_number": None, "paragraph_index": index + 1}
        for index, paragraph in enumerate(paragraphs)
    ]


def _format_ref(segment: dict) -> str:
    paragraph = segment.get("paragraph_index")
    page = segment.get("page_number")
    if page:
        return f"page {page}, paragraph {paragraph}"
    return f"paragraph {paragraph}"


def chunk_segments(segments: list[dict], chunk_size: int = 900) -> list[dict]:
    chunks: list[dict] = []
    current_text: list[str] = []
    current_refs: list[dict] = []
    current_len = 0

    for segment in segments:
        text = re.sub(r"\s+", " ", segment.get("text", "")).strip()
        if not text:
            continue
        if current_text and current_len + len(text) > chunk_size:
            chunks.append({"text": " ".join(current_text), "source_refs": current_refs})
            current_text = []
            current_refs = []
            current_len = 0
        current_text.append(text)
        current_refs.append(
            {
                "page_number": segment.get("page_number"),
                "paragraph_index": segment.get("paragraph_index"),
                "label": _format_ref(segment),
            }
        )
        current_len += len(text)

    if current_text:
        chunks.append({"text": " ".join(current_text), "source_refs": current_refs})
    return chunks


async def chunks_for_document(document: dict, embeddings: EmbeddingService | None = None) -> list[dict]:
    segments = document.get("content_segments") or _segments_for_content(document["content"])
    chunks = chunk_segments(segments)
    service = embeddings or EmbeddingService()
    vectors = await service.embed_many([chunk["text"] for chunk in chunks])
    settings = get_settings()
    provider = settings.embedding_provider.lower()
    embedding_model = {
        "openai": settings.openai_embedding_model,
        "fastembed": settings.fastembed_model,
        "sentence-transformers": settings.sentence_transformer_model,
        "sentence_transformers": settings.sentence_transformer_model,
        "huggingface-local": settings.sentence_transformer_model,
    }.get(provider, "local-hash")
    return [
        {
            "chunk_index": index,
            "text": chunk["text"],
            "source_refs": chunk["source_refs"],
            "embedding": vectors[index],
            "embedding_provider": settings.embedding_provider,
            "embedding_model": embedding_model,
        }
        for index, chunk in enumerate(chunks)
    ]


class RAGService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.chunks = DocumentChunkRepository(db)

    async def index_document(self, document: dict) -> None:
        await self.chunks.replace_for_document(document, await chunks_for_document(document))

    async def remove_document(self, document_id: str) -> None:
        await self.chunks.delete_for_document(document_id)

    async def ask(self, user_id: str, query: str, limit: int = 5) -> dict:
        workspaces = {workspace["id"]: workspace for workspace in await WorkspaceRepository(self.db).list_for_user(user_id)}
        for membership in await WorkspaceMemberRepository(self.db).list_for_user(user_id):
            workspace = await WorkspaceRepository(self.db).get(membership["workspace_id"])
            if workspace:
                workspaces[workspace["id"]] = workspace
        workspace_ids = list(workspaces)
        if not workspace_ids or not query.strip():
            return {"answer": "", "citations": []}

        candidates = await self.chunks.keyword_search(workspace_ids, query, limit=40)
        if len(candidates) < limit:
            seen = {candidate["id"] for candidate in candidates}
            extra = await self.chunks.list_for_workspaces(workspace_ids)
            candidates.extend(candidate for candidate in extra if candidate["id"] not in seen)

        query_embedding = await EmbeddingService().embed(query)
        ranked = sorted(
            candidates,
            key=lambda chunk: cosine(query_embedding, chunk.get("embedding", [])),
            reverse=True,
        )[:limit]
        citations = [
            {
                "document_id": chunk["document_id"],
                "workspace_id": chunk["workspace_id"],
                "document_title": chunk["document_title"],
                "chunk_index": chunk["chunk_index"],
                "source_refs": chunk.get("source_refs", []),
                "text": chunk["text"],
            }
            for chunk in ranked
        ]
        answer = await self._answer(query, citations)
        return {"answer": answer, "citations": citations}

    async def _answer(self, query: str, citations: list[dict]) -> str:
        if not citations:
            return "No matching knowledge base material was found."
        context = "\n\n".join(
            f"[{index + 1}] {citation['document_title']} ({self._citation_label(citation)}): {citation['text']}"
            for index, citation in enumerate(citations)
        )
        prompt = (
            "Answer the question using only the cited context. "
            "If the context is insufficient, say what is missing.\n\n"
            f"Question: {query}\n\nContext:\n{context}"
        )
        try:
            result = await AIService().analyze("Knowledge base question", prompt)
            return result.get("summary") or self._fallback_answer(citations)
        except Exception:
            return self._fallback_answer(citations)

    def _fallback_answer(self, citations: list[dict]) -> str:
        return " ".join(citation["text"] for citation in citations[:2])[:900]

    def _citation_label(self, citation: dict) -> str:
        refs = citation.get("source_refs") or []
        if not refs:
            return f"chunk {citation['chunk_index'] + 1}"
        labels = [ref.get("label") for ref in refs if ref.get("label")]
        return "; ".join(labels[:3])
