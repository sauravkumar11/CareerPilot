"""
Storage abstraction for uploaded resumes and generated documents.

`LocalFileStorage` is the only implementation wired up today (writes under
STORAGE_ROOT, mounted as a Docker volume in docker-compose). Swapping to
S3/GCS later means implementing `StorageBackend` again — nothing above this
layer (services, tasks, endpoints) should ever construct a raw file path.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, key: str, data: bytes) -> str:
        """Persist bytes under `key`, return the path/URI to store on the record."""
        raise NotImplementedError

    @abstractmethod
    async def read(self, path: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, path: str) -> None:
        raise NotImplementedError


class LocalFileStorage(StorageBackend):
    def __init__(self, root: str | None = None):
        settings = get_settings()
        self.root = Path(root or settings.STORAGE_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Reject path traversal — key must resolve inside root.
        candidate = (self.root / key).resolve()
        if self.root.resolve() not in candidate.parents and candidate != self.root.resolve():
            raise ValueError("Invalid storage key")
        return candidate

    async def save(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    async def read(self, path: str) -> bytes:
        resolved = Path(path)
        if not resolved.exists():
            raise FileNotFoundError(path)
        return resolved.read_bytes()

    async def delete(self, path: str) -> None:
        resolved = Path(path)
        if resolved.exists():
            resolved.unlink()


def generate_storage_key(user_id: uuid.UUID, category: str, extension: str) -> str:
    """e.g. users/<uuid>/resumes/<uuid>.pdf"""
    return f"users/{user_id}/{category}/{uuid.uuid4()}.{extension.lstrip('.')}"


_storage_singleton: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _storage_singleton
    if _storage_singleton is None:
        _storage_singleton = LocalFileStorage()
    return _storage_singleton
