import os
import unittest

from app.core.config import get_settings
from app.services import scheduler


class FakeBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args):
        self.tasks.append((func, args))


class FakeAnalysisService:
    calls = []

    def __init__(self, db):
        self.db = db

    async def enqueue_document_analysis(self, document_id, requested_by):
        self.calls.append(("enqueue", document_id, requested_by))

    async def run_document_analysis(self, document_id, requested_by):
        self.calls.append(("run", document_id, requested_by))


class SchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.previous_mode = os.environ.get("ANALYSIS_EXECUTION_MODE")
        self.original_service = scheduler.AnalysisService
        scheduler.AnalysisService = FakeAnalysisService
        FakeAnalysisService.calls = []

    async def asyncTearDown(self):
        scheduler.AnalysisService = self.original_service
        if self.previous_mode is None:
            os.environ.pop("ANALYSIS_EXECUTION_MODE", None)
        else:
            os.environ["ANALYSIS_EXECUTION_MODE"] = self.previous_mode
        get_settings.cache_clear()

    async def test_background_mode_schedules_fastapi_task(self):
        os.environ["ANALYSIS_EXECUTION_MODE"] = "background"
        get_settings.cache_clear()
        background = FakeBackgroundTasks()

        await scheduler.schedule_document_analysis(background, object(), "doc-1", "user-1")

        self.assertEqual(len(background.tasks), 1)
        self.assertEqual(background.tasks[0][1], ("doc-1", "user-1"))

    async def test_worker_mode_enqueues_job(self):
        os.environ["ANALYSIS_EXECUTION_MODE"] = "worker"
        get_settings.cache_clear()

        await scheduler.schedule_document_analysis(FakeBackgroundTasks(), object(), "doc-1", "user-1")

        self.assertEqual(FakeAnalysisService.calls, [("enqueue", "doc-1", "user-1")])


if __name__ == "__main__":
    unittest.main()
