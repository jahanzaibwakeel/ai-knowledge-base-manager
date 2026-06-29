from fastapi import BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.services.analysis import AnalysisService


async def schedule_document_analysis(
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase,
    document_id: str,
    requested_by: str,
) -> None:
    service = AnalysisService(db)
    if get_settings().analysis_execution_mode.lower() == "worker":
        await service.enqueue_document_analysis(document_id, requested_by)
        return
    background_tasks.add_task(service.run_document_analysis, document_id, requested_by)
