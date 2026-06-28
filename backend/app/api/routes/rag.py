import asyncio
import json
import re
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.api.deps import current_user, get_db
from app.services.rag import RAGService

router = APIRouter(prefix="/rag", tags=["rag"])


class RAGQuery(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)


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
