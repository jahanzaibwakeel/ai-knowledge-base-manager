from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.models.common import now_utc
from app.repositories.domain import AnalysisJobRepository, DocumentRepository
from app.services.ai import AIService
from app.services.rag import RAGService


class AnalysisService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.jobs = AnalysisJobRepository(db)
        self.documents = DocumentRepository(db)

    async def enqueue_document_analysis(self, document_id: str, requested_by: str) -> dict:
        document = await self.documents.get(document_id)
        if not document:
            return {}
        job = await self.jobs.create(
            {
                "workspace_id": document["workspace_id"],
                "document_id": document_id,
                "requested_by": requested_by,
                "status": "queued",
                "error": None,
            }
        )
        await self.documents.update(document_id, {"analysis_status": "pending"})
        return job

    async def run_document_analysis(self, document_id: str, requested_by: str, job_id: str | None = None) -> dict:
        document = await self.documents.get(document_id)
        if not document:
            return {}
        if job_id:
            job = await self.jobs.update(job_id, {"status": "running", "error": None})
        else:
            job = await self.jobs.create(
                {
                    "workspace_id": document["workspace_id"],
                    "document_id": document_id,
                    "requested_by": requested_by,
                    "status": "running",
                    "error": None,
                }
            )
        try:
            try:
                ai = await AIService().analyze(document["title"], document["content"])
            except Exception:
                preview = " ".join(document["content"].split())[:500]
                ai = {"summary": preview, "key_points": [], "action_items": []}
            updated = await self.documents.update(document_id, {**ai, "analysis_status": "complete"})
            await RAGService(self.db).index_document(updated)
            await self.jobs.update(job["id"], {"status": "complete"})
            return updated
        except Exception as exc:
            await self.documents.update(document_id, {"analysis_status": "failed"})
            await self.jobs.update(job["id"], {"status": "failed", "error": str(exc)})
            raise

    async def next_queued_job(self) -> dict | None:
        job = await self.db.analysis_jobs.find_one_and_update(
            {"status": "queued"},
            {"$set": {"status": "running", "updated_at": now_utc()}},
            sort=[("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )
        if not job:
            return None
        job["id"] = str(job.pop("_id"))
        return job
