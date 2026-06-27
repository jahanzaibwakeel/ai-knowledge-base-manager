from app.services.ai import AIService
from app.core.config import get_settings
from app.services.embeddings import EmbeddingService


def embedding_download_target(provider: str, fastembed_model: str, sentence_transformer_model: str) -> str | None:
    normalized = provider.lower()
    if normalized == "fastembed":
        return fastembed_model
    if normalized in {"sentence-transformers", "sentence_transformers", "huggingface-local"}:
        return sentence_transformer_model
    return None


def transformers_download_target(provider: str, model: str) -> str | None:
    if provider.lower() in {"transformers", "huggingface-local", "local-transformers"}:
        return model
    return None


def main() -> None:
    settings = get_settings()
    print("Prefetching local AI models for server deployment...")
    print(f"Embedding provider: {settings.embedding_provider}")

    embedding_service = EmbeddingService()
    embedding_target = embedding_download_target(
        settings.embedding_provider, settings.fastembed_model, settings.sentence_transformer_model
    )
    if settings.embedding_provider.lower() == "fastembed" and embedding_target:
        embedding_service._load_fastembed(embedding_target)
        print(f"Downloaded FastEmbed model: {embedding_target}")
    elif embedding_target:
        embedding_service._load_sentence_transformer(embedding_target)
        print(f"Downloaded Sentence Transformers model: {embedding_target}")
    else:
        print("No embedding model download needed for this provider.")

    print(f"AI provider: {settings.ai_provider}")
    transformers_target = transformers_download_target(settings.ai_provider, settings.transformers_summary_model)
    if transformers_target:
        AIService()._load_transformers_pipeline(transformers_target)
        print(f"Downloaded Transformers model: {transformers_target}")
    else:
        print("No Transformers model download needed for this AI provider.")

    print("Model prefetch complete.")


if __name__ == "__main__":
    main()
