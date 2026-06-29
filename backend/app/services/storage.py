from pathlib import Path
from uuid import uuid4

import boto3
from fastapi import UploadFile

from app.core.config import get_settings


class UploadTooLargeError(ValueError):
    pass


class FileStorageService:
    def __init__(self, base_dir: str | None = None, s3_client=None):
        self.settings = get_settings()
        self.base_dir = Path(base_dir or self.settings.file_storage_dir)
        self.s3_client = s3_client

    async def save_upload(self, upload: UploadFile, workspace_id: str) -> dict:
        settings = self.settings
        filename = upload.filename or "document"
        suffix = Path(filename).suffix.lower()
        storage_name = f"{uuid4().hex}{suffix}"

        content = await upload.read()
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            await upload.seek(0)
            raise UploadTooLargeError(f"Upload exceeds {settings.max_upload_size_mb} MB limit.")
        if settings.storage_backend.lower() == "s3":
            key = f"{workspace_id}/{storage_name}"
            self._s3().put_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Body=content,
                ContentType=upload.content_type or "application/octet-stream",
            )
            storage_path = f"s3://{settings.s3_bucket}/{key}"
        else:
            workspace_dir = self.base_dir / workspace_id
            workspace_dir.mkdir(parents=True, exist_ok=True)
            path = workspace_dir / storage_name
            path.write_bytes(content)
            storage_path = str(path)
        await upload.seek(0)
        return {
            "original_filename": filename,
            "storage_path": storage_path,
            "content_type": upload.content_type,
            "size_bytes": len(content),
        }

    def delete_stored_file(self, storage_path: str | None) -> None:
        if not storage_path:
            return
        if storage_path.startswith("s3://"):
            try:
                bucket, key = storage_path.removeprefix("s3://").split("/", 1)
                self._s3().delete_object(Bucket=bucket, Key=key)
            except Exception:
                pass
            return
        path = Path(storage_path)
        try:
            if path.exists() and path.is_file():
                path.unlink()
        except OSError:
            pass

    def _s3(self):
        if self.s3_client is not None:
            return self.s3_client
        settings = self.settings
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
            use_ssl=settings.s3_secure_urls,
        )
        return self.s3_client
