import json

import httpx

from app.core.config import get_settings

_transformers_pipelines: dict[str, object] = {}


SYSTEM_PROMPT = """Return compact JSON with keys: summary (string), key_points (array of strings), action_items (array of strings). Keep it useful and factual."""


class AIService:
    async def analyze(self, title: str, content: str) -> dict:
        settings = get_settings()
        if settings.ai_provider.lower() == "openai" and settings.openai_api_key:
            return await self._openai(title, content)
        if settings.ai_provider.lower() == "ollama":
            return await self._ollama(title, content)
        if settings.ai_provider.lower() in {"transformers", "huggingface-local", "local-transformers"}:
            return await self._transformers(title, content)
        return self._fallback(content)

    async def _openai(self, title: str, content: str) -> dict:
        settings = get_settings()
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Title: {title}\n\nContent:\n{content[:12000]}"},
            ],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )
            response.raise_for_status()
        return self._coerce(json.loads(response.json()["choices"][0]["message"]["content"]))

    async def _ollama(self, title: str, content: str) -> dict:
        settings = get_settings()
        prompt = f"{SYSTEM_PROMPT}\n\nTitle: {title}\n\nContent:\n{content[:12000]}"
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/generate",
                json={"model": settings.ollama_model, "prompt": prompt, "format": "json", "stream": False},
            )
            response.raise_for_status()
        return self._coerce(json.loads(response.json().get("response", "{}")))

    async def _transformers(self, title: str, content: str) -> dict:
        import asyncio

        settings = get_settings()
        pipeline = self._load_transformers_pipeline(settings.transformers_summary_model)
        prompt = (
            "Summarize this knowledge-base document in a concise, useful way.\n\n"
            f"Title: {title}\n\nContent:\n{content[:6000]}"
        )

        def generate() -> str:
            result = pipeline(prompt, max_new_tokens=220, do_sample=False)
            first = result[0] if result else {}
            return str(first.get("summary_text") or first.get("generated_text") or "")

        try:
            summary = (await asyncio.to_thread(generate)).strip()
        except Exception:
            return self._fallback(content)

        fallback = self._fallback(content)
        return self._coerce(
            {
                "summary": summary or fallback["summary"],
                "key_points": fallback["key_points"],
                "action_items": fallback["action_items"],
            }
        )

    def _load_transformers_pipeline(self, model_name: str):
        settings = get_settings()
        cache_key = f"{model_name}:{settings.transformers_device}"
        if cache_key not in _transformers_pipelines:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError("Install transformers or use AI_PROVIDER=ollama/local.") from exc
            _transformers_pipelines[cache_key] = pipeline(
                "text2text-generation",
                model=model_name,
                device=settings.transformers_device,
            )
        return _transformers_pipelines[cache_key]

    def _fallback(self, content: str) -> dict:
        preview = " ".join(content.split())[:500]
        sentences = [item.strip() for item in content.replace("\n", " ").split(".") if item.strip()]
        return {
            "summary": preview + ("..." if len(content) > 500 else ""),
            "key_points": sentences[:5],
            "action_items": [],
        }

    def _coerce(self, payload: dict) -> dict:
        return {
            "summary": str(payload.get("summary") or ""),
            "key_points": [str(item) for item in payload.get("key_points", [])][:10],
            "action_items": [str(item) for item in payload.get("action_items", [])][:10],
        }
