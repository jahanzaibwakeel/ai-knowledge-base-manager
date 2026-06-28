import asyncio
import json
import re
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.api.deps import current_user, get_db
from app.api.routes.workspaces import accessible_workspaces
from app.repositories.domain import RAGFeedbackRepository
from app.services.rag import RAGService

router = APIRouter(prefix="/rag", tags=["rag"])


class RAGQuery(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)


class RAGFeedback(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    answer: str = Field(min_length=1, max_length=5000)
    rating: str = Field(pattern="^(helpful|not_helpful)$")
    comment: str | None = Field(default=None, max_length=1000)
    citations: list[dict] = Field(default_factory=list)


class RAGFeedbackListQuery(BaseModel):
    rating: str | None = Field(default=None, pattern="^(helpful|not_helpful)$")
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


@router.post("/query")
async def query_knowledge_base(
    payload: RAGQuery,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    return await RAGService(db).ask(user["id"], payload.query, payload.limit)


def sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def answer_chunks(answer: str, chunk_words: int = 8) -> list[str]:
    words = re.findall(r"\S+\s*", answer)
    if not words:
        return []
    return ["".join(words[index : index + chunk_words]) for index in range(0, len(words), chunk_words)]


async def stream_rag_answer(service: RAGService, user_id: str, query: str, limit: int) -> AsyncIterator[str]:
    yield sse_event("status", {"message": "retrieving"})
    result = await service.ask(user_id, query, limit)
    yield sse_event("citations", {"citations": result["citations"]})
    yield sse_event("status", {"message": "answering"})
    for chunk in answer_chunks(result["answer"]):
        yield sse_event("token", {"text": chunk})
        await asyncio.sleep(0)
    yield sse_event("done", {"answer": result["answer"]})


@router.post("/query/stream")
async def stream_knowledge_base_query(
    payload: RAGQuery,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> StreamingResponse:
    return StreamingResponse(
        stream_rag_answer(RAGService(db), user["id"], payload.query, payload.limit),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/feedback", status_code=201)
async def record_rag_feedback(
    payload: RAGFeedback,
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    workspaces = await accessible_workspaces(db, user["id"])
    workspace_ids = [workspace["id"] for workspace in workspaces]
    citation_workspace_ids = sorted(
        {
            citation.get("workspace_id")
            for citation in payload.citations
            if citation.get("workspace_id") in workspace_ids
        }
    )
    feedback = await RAGFeedbackRepository(db).create(
        {
            "user_id": user["id"],
            "workspace_ids": citation_workspace_ids or workspace_ids,
            "query": payload.query,
            "answer": payload.answer,
            "rating": payload.rating,
            "comment": payload.comment,
            "citations": payload.citations[:10],
        }
    )
    return feedback


@router.get("/feedback")
async def list_rag_feedback(
    rating: str | None = Query(default=None, pattern="^(helpful|not_helpful)$"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    query = RAGFeedbackListQuery(rating=rating, limit=limit, offset=offset)
    workspaces = await accessible_workspaces(db, user["id"])
    workspace_ids = [workspace["id"] for workspace in workspaces]
    repository = RAGFeedbackRepository(db)
    return {
        "items": await repository.list_for_workspaces(
            workspace_ids,
            rating=query.rating,
            limit=query.limit,
            skip=query.offset,
        ),
        "total": await repository.count_for_workspaces(workspace_ids, query.rating),
        "limit": query.limit,
        "offset": query.offset,
    }
