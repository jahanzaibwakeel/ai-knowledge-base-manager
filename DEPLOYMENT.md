# Deployment Guide

## Zero-Cost AI Mode

The default configuration avoids paid hosted AI APIs:

```env
ZERO_COST_MODE=true
AI_PROVIDER=local
EMBEDDING_PROVIDER=fastembed
FASTEMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
OPENAI_API_KEY=
```

This uses local semantic embeddings with FastEmbed. It may download model files once on the server, but it does not call a paid inference API.
With `ZERO_COST_MODE=true`, accidental OpenAI configuration is blocked at runtime.

## Server Setup

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Set a production JWT secret:

```env
JWT_SECRET=replace-with-a-long-random-secret
```

3. Review ingestion limits for your server size:

```env
MAX_UPLOAD_SIZE_MB=25
MAX_DOCUMENT_CHARS=200000
```

4. Build the backend image:

```bash
docker compose build backend
```

5. Prefetch local models on the server:

```bash
docker compose run --rm backend python scripts/prefetch_models.py
```

6. Start the stack:

```bash
docker compose up -d
```

Optional worker mode for AI/RAG analysis:

```env
ANALYSIS_EXECUTION_MODE=worker
```

```bash
docker compose --profile worker up -d --build
```

Optional local object storage with MinIO:

```env
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=replace-me
S3_SECRET_ACCESS_KEY=replace-me
S3_BUCKET=knowledge-base-uploads
```

```bash
docker compose --profile object-storage up -d --build
```

Optional Caddy reverse proxy:

```env
CADDY_SITE_ADDRESS=your-domain.example.com
```

```bash
docker compose --profile proxy up -d --build
```

## Persistent Data

Docker Compose defines persistent volumes for:

- `mongo_data`: MongoDB data
- `backend_uploads`: uploaded original files
- `minio_data`: uploaded original files when `STORAGE_BACKEND=s3` is used with local MinIO
- `caddy_data` and `caddy_config`: Caddy certificates and proxy state
- `model_cache`: local Hugging Face/FastEmbed model cache
- `ollama_data`: Ollama models if Ollama is enabled

Do not delete these volumes during upgrades unless you intentionally want to remove stored data or downloaded models.

## Backups

Create a timestamped backup of MongoDB data and uploaded files:

```powershell
.\scripts\backup.ps1
```

Restore from a backup:

```powershell
.\scripts\restore.ps1 -BackupDir backups\YYYYMMDD-HHMMSS -ConfirmRestore
```

Restore is destructive: it drops MongoDB collections and replaces uploaded files. See `scripts/README.md` for volume-name options.

## Production Notes

- Put the frontend behind HTTPS; the `proxy` profile provides a Caddy-based reverse proxy.
- Restrict backend access to trusted origins.
- Use MongoDB Atlas or a secured MongoDB server for production data.
- Use MinIO or another S3-compatible object store for large uploaded files if server disk is limited.
- Keep `OPENAI_API_KEY` empty for zero billing risk.
- Keep `ZERO_COST_MODE=true` unless you intentionally want paid hosted AI calls.
- Monitor disk usage for uploaded files and model cache.
- Keep upload and document-size limits aligned with server memory and disk capacity.
