from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Knowledge Base Manager"
    api_prefix: str = "/api/v1"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "knowledge_base"
    jwt_secret: str = "change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    zero_cost_mode: bool = True
    ai_provider: str = "local"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    embedding_provider: str = "fastembed"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 128
    fastembed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    sentence_transformer_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    transformers_summary_model: str = "google/flan-t5-small"
    transformers_device: int = -1
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    file_storage_dir: str = "uploads"
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def paid_ai_blocked(self) -> bool:
        return self.zero_cost_mode and self.ai_provider.lower() == "openai"

    def paid_embeddings_blocked(self) -> bool:
        return self.zero_cost_mode and self.embedding_provider.lower() == "openai"

    def safety_snapshot(self) -> dict:
        return {
            "zero_cost_mode": self.zero_cost_mode,
            "ai_provider": self.ai_provider,
            "embedding_provider": self.embedding_provider,
            "openai_key_configured": bool(self.openai_api_key),
            "paid_ai_blocked": self.paid_ai_blocked(),
            "paid_embeddings_blocked": self.paid_embeddings_blocked(),
            "billing_risk": not self.zero_cost_mode
            and (
                (self.ai_provider.lower() == "openai" and bool(self.openai_api_key))
                or (self.embedding_provider.lower() == "openai" and bool(self.openai_api_key))
            ),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
