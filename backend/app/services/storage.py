from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


class UploadTooLargeError(ValueError):
    pass


class FileStorageService:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or get_settings().file_storage_dir)

    async def save_upload(self, upload: UploadFile, workspace_id: str) -> dict:
        settings = get_settings()
        filename = upload.filename or "document"
        suffix = Path(filename).suffix.lower()
        workspace_dir = self.base_dir / workspace_id
        workspace_dir.mkdir(parents=True, exist_ok=True)
        storage_name = f"{uuid4().hex}{suffix}"
        path = workspace_dir / storage_name

        content = await upload.read()
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            await upload.seek(0)
            raise UploadTooLargeError(f"Upload exceeds {settings.max_upload_size_mb} MB limit.")
        path.write_bytes(content)
        await upload.seek(0)
        return {
            "original_filename": filename,
            "storage_path": str(path),
            "content_type": upload.content_type,
            "size_bytes": len(content),
        }

    def delete_stored_file(self, storage_path: str | None) -> None:
        if not storage_path:
            return
        path = Path(storage_path)
        try:
            if path.exists() and path.is_file():
                path.unlink()
        except OSError:
            pass
