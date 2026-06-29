from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.routes import activity, auth, collections, dashboard, documents, rag, workspaces
from app.core.config import get_settings
from app.core.metrics import request_metrics
from app.core.middleware import DistributedRateLimitMiddleware, RequestContextMiddleware
from app.db.mongo import close_mongo_connection, connect_to_mongo, get_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(DistributedRateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Unexpected server error", "error": exc.__class__.__name__})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict:
    await get_database().command("ping")
    return {"status": "ready"}


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(request_metrics.prometheus(), media_type="text/plain; version=0.0.4")


@app.get("/metrics.json")
async def metrics_json() -> dict:
    return request_metrics.snapshot()


@app.get("/safety")
async def safety() -> dict:
    return get_settings().safety_snapshot()


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(workspaces.router, prefix=settings.api_prefix)
app.include_router(collections.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(rag.router, prefix=settings.api_prefix)
app.include_router(activity.router, prefix=settings.api_prefix)
