import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from app.services.storage import FileStorageService


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


if __name__ == "__main__":
    unittest.main()
