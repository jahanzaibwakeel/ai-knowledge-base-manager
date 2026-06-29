import asyncio
import logging

from app.core.config import get_settings
from app.db.mongo import close_mongo_connection, connect_to_mongo, get_database
from app.services.analysis import AnalysisService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("knowledge_base.worker")


async def run_worker() -> None:
    await connect_to_mongo()
    service = AnalysisService(get_database())
    settings = get_settings()
    logger.info("analysis worker started")
    try:
        while True:
            job = await service.next_queued_job()
            if not job:
                await asyncio.sleep(settings.analysis_worker_poll_seconds)
                continue
            logger.info("processing analysis job %s", job["id"])
            await service.run_document_analysis(job["document_id"], job["requested_by"], job["id"])
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(run_worker())
