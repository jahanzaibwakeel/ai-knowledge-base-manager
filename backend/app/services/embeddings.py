import hashlib
import math
import re

import httpx

from app.core.config import get_settings

_sentence_transformer_models: dict[str, object] = {}
_fastembed_models: dict[str, object] = {}


def local_embed_text(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % dimensions
        vector[index] += 1.0
    magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / magnitude for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class EmbeddingService:
    async def embed(self, text: str) -> list[float]:
        settings = get_settings()
        provider = settings.embedding_provider.lower()
        if provider == "openai" and settings.openai_api_key and not settings.paid_embeddings_blocked():
            return await self._openai(text)
        if provider == "fastembed":
            return (await self._fastembed_many([text]))[0]
        if provider in {"sentence-transformers", "sentence_transformers", "huggingface-local"}:
            return (await self._sentence_transformers_many([text]))[0]
        return local_embed_text(text, settings.embedding_dimensions)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        provider = settings.embedding_provider.lower()
        if provider == "openai" and settings.openai_api_key and texts and not settings.paid_embeddings_blocked():
            return await self._openai_many(texts)
        if provider == "fastembed" and texts:
            return await self._fastembed_many(texts)
        if provider in {"sentence-transformers", "sentence_transformers", "huggingface-local"} and texts:
            return await self._sentence_transformers_many(texts)
        return [local_embed_text(text, settings.embedding_dimensions) for text in texts]

    async def _openai(self, text: str) -> list[float]:
        return (await self._openai_many([text]))[0]

    async def _openai_many(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        payload = {"model": settings.openai_embedding_model, "input": texts}
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )
            response.raise_for_status()
        data = sorted(response.json()["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in data]

    async def _fastembed_many(self, texts: list[str]) -> list[list[float]]:
        import asyncio

        settings = get_settings()
        model = self._load_fastembed(settings.fastembed_model)

        def encode() -> list[list[float]]:
            return [vector.tolist() for vector in model.embed(texts)]

        return await asyncio.to_thread(encode)

    def _load_fastembed(self, model_name: str):
        if model_name not in _fastembed_models:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise RuntimeError("Install fastembed or use EMBEDDING_PROVIDER=local.") from exc
            _fastembed_models[model_name] = TextEmbedding(model_name=model_name)
        return _fastembed_models[model_name]

    async def _sentence_transformers_many(self, texts: list[str]) -> list[list[float]]:
        import asyncio

        settings = get_settings()
        model = self._load_sentence_transformer(settings.sentence_transformer_model)

        def encode() -> list[list[float]]:
            vectors = model.encode(texts, normalize_embeddings=True)
            return [vector.tolist() for vector in vectors]

        return await asyncio.to_thread(encode)

    def _load_sentence_transformer(self, model_name: str):
        if model_name not in _sentence_transformer_models:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "Install sentence-transformers or use EMBEDDING_PROVIDER=local."
                ) from exc
            _sentence_transformer_models[model_name] = SentenceTransformer(model_name)
        return _sentence_transformer_models[model_name]
