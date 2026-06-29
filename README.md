# AI Knowledge Base Manager

A production-style full-stack knowledge base app with FastAPI, Next.js, MongoDB, JWT auth, document parsing, and AI insights through free local models, Ollama, or OpenAI.

## Features

- JWT registration and login
- Password reset token flow for local/self-hosted deployments
- Workspace and collection management
- Create, edit, delete, and search notes/documents
- Upload PDF, TXT, Markdown, and store extracted content in MongoDB
- Tags, collection organization, metadata, and activity timeline
- AI summaries, key points, and action items
- RAG-style knowledge base Q&A with document chunk citations and page/paragraph references
- Streaming RAG answers over Server-Sent Events
- RAG answer feedback capture and review for retrieval quality evaluation
- RAG evaluation endpoint for regression checks against expected answer terms and citation counts
- Configurable embeddings: local ONNX/Hugging Face embeddings by default, deterministic local hash fallback, full Sentence Transformers optional, or OpenAI embeddings if enabled
- Background AI/RAG analysis jobs with document status tracking
- Workspace members with `owner`, `editor`, and `viewer` roles
- Owner controls for member role changes, member removal, and workspace ownership transfer
- Original upload retention through a configurable file storage directory
- Configurable upload and extracted-document size limits
- Request IDs, optional Redis/Valkey-backed rate limiting with in-memory fallback, readiness checks, and document version restore
- Lightweight `/metrics` and `/metrics.json` observability endpoints
- Zero-cost safety mode blocks paid OpenAI calls by default
- Paginated document lists, filtered keyword search, soft archive/restore, permanent hard-delete, and JSON export endpoints
- MongoDB text indexes for global keyword search
- Responsive Next.js dashboard and document detail pages
- System status page for health, readiness, safety, and request metrics
- RAG feedback review panel with filters for answer-quality tuning
- Full activity timeline page with workspace, action, and entity filters
- Docker Compose for frontend, backend, MongoDB, and Ollama

## Quick Start

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Start the stack:

```bash
docker compose up --build
```

3. Open the app:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- OpenAPI docs: http://localhost:8000/docs
- MongoDB: mongodb://localhost:27017

### MongoDB Options

Docker Compose starts MongoDB for you, so you do not need to install MongoDB locally for normal development.

MongoDB Atlas also works. Set these values in `.env`:

```bash
MONGO_URI=mongodb+srv://<user>:<password>@<cluster-host>/?retryWrites=true&w=majority
MONGO_DB=knowledge_base
```

Keep credentials out of Git and make sure the Atlas network access rules allow your deployment or development IP.

Uploaded source files are retained under `FILE_STORAGE_DIR` and mounted as a Docker volume by default.
Uploads default to `MAX_UPLOAD_SIZE_MB=25`, and extracted/note content defaults to `MAX_DOCUMENT_CHARS=200000`.

By default, the app uses local embeddings so there is no API bill:

```bash
ZERO_COST_MODE=true
AI_PROVIDER=local
EMBEDDING_PROVIDER=fastembed
FASTEMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

The first run downloads local embedding model files to the container or host cache. That is free, but it needs disk space and an internet connection for the initial download.

To pre-download the configured models on your server instead of waiting for the first user request:

```bash
docker compose build backend
docker compose run --rm backend python scripts/prefetch_models.py
```

Direct model links:

- Fast/default embedding model: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- Optional lightweight summary model: https://huggingface.co/google/flan-t5-small

The default Compose file mounts `model_cache:/app/model-cache` and sets `HF_HOME`, `HF_HUB_CACHE`, and `TRANSFORMERS_CACHE`, so model downloads persist across container restarts and image rebuilds.

For full Hugging Face Transformers variety, install the optional ML requirements in local backend development:

```bash
cd backend
pip install -r requirements-ml.txt
```

Then set:

```bash
AI_PROVIDER=transformers
TRANSFORMERS_SUMMARY_MODEL=google/flan-t5-small
EMBEDDING_PROVIDER=sentence-transformers
SENTENCE_TRANSFORMER_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

This is still free in API cost, but it installs a much larger ML stack and can be slow on CPU.

Ollama is still available as another free local option. Pull a model before relying on Ollama responses:

```bash
docker compose exec ollama ollama pull llama3.1
```

To use OpenAI instead, set these in `.env`:

```bash
ZERO_COST_MODE=false
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

RAG embeddings are separate from answer generation. FastEmbed gives local semantic search while staying lighter than the full PyTorch stack:

```bash
EMBEDDING_PROVIDER=fastembed
FASTEMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

For full Sentence Transformers, use the optional ML install and switch providers:

```bash
EMBEDDING_PROVIDER=sentence-transformers
SENTENCE_TRANSFORMER_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

For the lightest possible fallback with no model download, use deterministic local hash embeddings:

```bash
EMBEDDING_PROVIDER=local
EMBEDDING_DIMENSIONS=128
```

For paid hosted semantic retrieval, OpenAI embeddings remain supported but disabled by default:

```bash
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...
```

OpenAI embeddings are usage-billed by tokens. Leave `OPENAI_API_KEY` empty if you want zero billing risk.
When `ZERO_COST_MODE=true`, the backend will not call OpenAI even if `AI_PROVIDER=openai` or `EMBEDDING_PROVIDER=openai` is accidentally configured.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend tests:

```bash
cd backend
python -m unittest discover -s tests
```

Mongo integration tests require a reachable MongoDB instance:

```bash
docker compose up -d mongo
docker run --rm --network knowledgebasedmanager_default `
  --entrypoint python `
  -e RUN_INTEGRATION_TESTS=1 `
  -e MONGO_URI=mongodb://mongo:27017 `
  -e MONGO_DB=knowledge_base_test `
  -v "%cd%\backend\tests:/app/tests:ro" `
  knowledgebasedmanager-backend -m unittest discover -s tests
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend checks:

```bash
cd frontend
npm run typecheck
npm run lint
npm run build
npm run test:e2e
```

Use `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` for local frontend development.

## DevOps

- Docker Compose includes healthchecks for MongoDB, Valkey, backend readiness, frontend availability, and Ollama.
- Docker Compose includes persistent volumes for MongoDB data, Valkey rate limiting, uploaded files, Ollama models, and local Hugging Face/FastEmbed model cache.
- PowerShell operations scripts provide Docker-based MongoDB/upload backup and restore.
- Backend startup waits for MongoDB health before serving the API.
- Frontend startup waits for backend readiness.
- CI validates `docker compose config`, builds the backend image, runs backend tests in Docker, then runs frontend typecheck, lint, build, and Playwright E2E.
- Dependabot is configured for Python, npm, Docker, and GitHub Actions updates.

See `DEPLOYMENT.md` for a server deployment checklist focused on zero-cost local AI, model prefetching, and persistent volumes.

## Architecture

```text
backend/app
  api/routes       REST route handlers
  core             configuration and security
  db               MongoDB connection and indexes
  repositories     database access layer
  schemas          Pydantic request/response models
  services         AI, parsing, and activity services

frontend/src
  app              Next.js routes
  components       reusable UI components
  lib              API client and shared types
```

The backend uses a service/repository pattern: route handlers validate ownership and request data, services handle domain workflows, and repositories isolate MongoDB operations.

## API Highlights

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`
- `GET /api/v1/dashboard`
- `GET /api/v1/dashboard/search?q=...&limit=25&offset=0`
- `GET /api/v1/activity?workspace_id=...&action=created&entity_type=document`
- `POST /api/v1/workspaces`
- `GET /api/v1/workspaces/{workspace_id}/documents?limit=25&offset=0&tag=...`
- `GET /api/v1/workspaces/{workspace_id}/export`
- `POST /api/v1/collections`
- `POST /api/v1/documents/notes`
- `POST /api/v1/documents/upload`
- `GET /api/v1/documents/{document_id}`
- `PATCH /api/v1/documents/{document_id}`
- `DELETE /api/v1/documents/{document_id}` soft-archives the document
- `DELETE /api/v1/documents/{document_id}/hard` permanently deletes an owner-authorized document
- `POST /api/v1/documents/{document_id}/restore`
- `GET /api/v1/documents/{document_id}/export`
- `POST /api/v1/documents/{document_id}/analyze`
- `GET /api/v1/documents/{document_id}/analysis-jobs`
- `GET /api/v1/documents/{document_id}/versions`
- `POST /api/v1/documents/{document_id}/versions/{version}/restore`
- `POST /api/v1/rag/query`
- `POST /api/v1/rag/query/stream`
- `POST /api/v1/rag/evaluate`
- `POST /api/v1/rag/feedback`
- `GET /api/v1/rag/feedback?rating=not_helpful&limit=10`
- `GET /api/v1/workspaces/{workspace_id}/members`
- `POST /api/v1/workspaces/{workspace_id}/members`
- `PATCH /api/v1/workspaces/{workspace_id}/members/{member_id}`
- `DELETE /api/v1/workspaces/{workspace_id}/members/{member_id}`
- `POST /api/v1/workspaces/{workspace_id}/transfer-ownership`

Operational endpoints:

- `GET /health`
- `GET /ready`
- `GET /metrics`
- `GET /metrics.json`
- `GET /safety`

## Production Notes

- Replace `JWT_SECRET` with a long random value.
- Set `RETURN_PASSWORD_RESET_TOKEN=false` when an email delivery service is added; the default is convenient for local/self-hosted zero-cost recovery.
- Restrict CORS origins for deployed domains.
- Use `RATE_LIMIT_BACKEND=redis` with Valkey/Redis for multi-instance deployments, or `RATE_LIMIT_BACKEND=memory` for simple local development.
- Run MongoDB with authentication and backups outside local development.
- Consider background jobs for AI analysis on very large documents.
- Local model providers are free in API cost but run on your machine/container. Expect slower responses on CPU and larger Docker images after installing optional ML dependencies.
- Set `EMBEDDING_PROVIDER=openai` only if you intentionally want paid hosted embeddings. Atlas Vector Search can be added later by replacing the repository ranking path with a MongoDB vector index query.
- For cloud object storage, replace `FileStorageService` with S3, MinIO, or Azure Blob while preserving the stored metadata fields.
