import tempfile
import unittest
from io import BytesIO
from pathlib import Path
import os

from fastapi import UploadFile

from app.core.config import get_settings
from app.services.storage import FileStorageService, UploadTooLargeError


class StorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_upload_persists_file_and_rewinds_stream(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            upload = UploadFile(filename="note.md", file=BytesIO(b"# Knowledge"))

            stored = await FileStorageService(temp_dir).save_upload(upload, "workspace-1")

            path = Path(stored["storage_path"])
            self.assertTrue(path.exists())
            self.assertEqual(path.read_bytes(), b"# Knowledge")
            self.assertEqual(stored["size_bytes"], 11)
            self.assertEqual(await upload.read(), b"# Knowledge")

    async def test_save_upload_rejects_files_over_configured_limit(self):
        previous_limit = os.environ.get("MAX_UPLOAD_SIZE_MB")
        os.environ["MAX_UPLOAD_SIZE_MB"] = "1"
        get_settings.cache_clear()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                upload = UploadFile(filename="large.txt", file=BytesIO(b"x" * ((1024 * 1024) + 1)))

                with self.assertRaisesRegex(UploadTooLargeError, "1 MB limit"):
                    await FileStorageService(temp_dir).save_upload(upload, "workspace-1")

                self.assertEqual(list(Path(temp_dir).rglob("*.*")), [])
                self.assertEqual(await upload.read(), b"x" * ((1024 * 1024) + 1))
        finally:
            if previous_limit is None:
                os.environ.pop("MAX_UPLOAD_SIZE_MB", None)
            else:
                os.environ["MAX_UPLOAD_SIZE_MB"] = previous_limit
            get_settings.cache_clear()

    async def test_delete_stored_file_removes_saved_upload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            upload = UploadFile(filename="note.txt", file=BytesIO(b"hello"))
            service = FileStorageService(temp_dir)
            stored = await service.save_upload(upload, "workspace-1")

            service.delete_stored_file(stored["storage_path"])

            self.assertFalse(Path(stored["storage_path"]).exists())


if __name__ == "__main__":
    unittest.main()
