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

3. Build the backend image:

```bash
docker compose build backend
```

4. Prefetch local models on the server:

```bash
docker compose run --rm backend python scripts/prefetch_models.py
```

5. Start the stack:

```bash
docker compose up -d
```

## Persistent Data

Docker Compose defines persistent volumes for:

- `mongo_data`: MongoDB data
- `backend_uploads`: uploaded original files
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

- Put the frontend behind HTTPS.
- Restrict backend access to trusted origins.
- Use MongoDB Atlas or a secured MongoDB server for production data.
- Use external object storage for large uploaded files if server disk is limited.
- Keep `OPENAI_API_KEY` empty for zero billing risk.
- Keep `ZERO_COST_MODE=true` unless you intentionally want paid hosted AI calls.
- Monitor disk usage for uploaded files and model cache.
