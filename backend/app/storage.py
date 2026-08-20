import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from app.config import settings


class Storage(ABC):
    """Storage backend abstraction for artwork files and published catalogue JSON."""

    @abstractmethod
    def write_bytes(self, key: str, data: bytes, content_type: str) -> str:
        """Write bytes atomically under `key`. Returns a publicly-servable URL."""

    @abstractmethod
    def read_bytes(self, key: str) -> bytes | None:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abstractmethod
    def url_for(self, key: str) -> str:
        ...


class LocalDiskStorage(Storage):
    def __init__(self, base_dir: str | None = None, public_base_url: str | None = None):
        self.base_dir = Path(base_dir or settings.storage_local_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.public_base_url = (public_base_url or settings.storage_public_base_url).rstrip("/")

    def _path(self, key: str) -> Path:
        p = (self.base_dir / key).resolve()
        if self.base_dir.resolve() not in p.parents and p != self.base_dir.resolve():
            raise ValueError("Invalid storage key")
        return p

    def write_bytes(self, key: str, data: bytes, content_type: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        return self.url_for(key)

    def read_bytes(self, key: str) -> bytes | None:
        path = self._path(key)
        if not path.exists():
            return None
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def url_for(self, key: str) -> str:
        return f"{self.public_base_url}/{key.lstrip('/')}"


class S3Storage(Storage):
    """S3-compatible storage (AWS S3, MinIO, Cloudflare R2) via boto3.

    Stubbed to satisfy the interface; not exercised in tests since no live
    S3-compatible endpoint is available in this environment. Configure via
    STORAGE_BACKEND=s3, S3_BUCKET, S3_ENDPOINT_URL, S3_REGION,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY.
    """

    def __init__(self):
        import boto3

        self.bucket = settings.s3_bucket
        self.public_base_url = settings.storage_public_base_url.rstrip("/")
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )

    def write_bytes(self, key: str, data: bytes, content_type: str) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return self.url_for(key)

    def read_bytes(self, key: str) -> bytes | None:
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=key)
            return obj["Body"].read()
        except self.client.exceptions.NoSuchKey:
            return None

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def url_for(self, key: str) -> str:
        return f"{self.public_base_url}/{key.lstrip('/')}"


_storage_instance: Storage | None = None


def get_storage() -> Storage:
    global _storage_instance
    if _storage_instance is None:
        if settings.storage_backend == "s3":
            _storage_instance = S3Storage()
        else:
            _storage_instance = LocalDiskStorage()
    return _storage_instance
