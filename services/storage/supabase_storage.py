from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from uuid import uuid4

import httpx

from airbeeps_api.core.config import Settings


class StorageError(Exception):
    pass


@dataclass
class StoredObject:
    bucket: str
    path: str


class SupabaseStorageService:
    def __init__(self, settings: Settings):
        self._base_url = settings.supabase_url.rstrip("/")
        self._secret_key = settings.supabase_secret_key
        self._default_bucket = settings.supabase_storage_bucket

    def build_storage_path(
        self, *, workspace_id: str, project_id: str, filename: str
    ) -> str:
        normalized = filename.replace("\\", "_").replace("/", "_")
        suffix = uuid4().hex[:10]
        return str(PurePosixPath(workspace_id) / project_id / f"{suffix}_{normalized}")

    async def upload_bytes(
        self,
        *,
        workspace_id: str,
        project_id: str,
        filename: str,
        content: bytes,
        content_type: str | None,
        bucket: str | None = None,
    ) -> StoredObject:
        target_bucket = bucket or self._default_bucket
        path = self.build_storage_path(
            workspace_id=workspace_id,
            project_id=project_id,
            filename=filename,
        )
        object_url = f"{self._base_url}/storage/v1/object/{target_bucket}/{path}"
        headers = {
            "Authorization": f"Bearer {self._secret_key}",
            "apikey": self._secret_key,
            "x-upsert": "false",
        }
        if content_type:
            headers["content-type"] = content_type

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(object_url, headers=headers, content=content)
            if response.status_code == 400 and "Bucket not found" in response.text:
                await self._create_bucket_if_missing(
                    client=client, bucket=target_bucket
                )
                response = await client.post(
                    object_url, headers=headers, content=content
                )

        if response.status_code not in (200, 201):
            raise StorageError(
                f"Supabase Storage upload failed ({response.status_code}): {response.text[:200]}"
            )

        return StoredObject(bucket=target_bucket, path=path)

    async def download_bytes(self, *, bucket: str, path: str) -> bytes:
        object_url = f"{self._base_url}/storage/v1/object/{bucket}/{path}"
        headers = {
            "Authorization": f"Bearer {self._secret_key}",
            "apikey": self._secret_key,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(object_url, headers=headers)

        if response.status_code != 200:
            raise StorageError(
                f"Supabase Storage download failed ({response.status_code}): {response.text[:200]}"
            )
        return response.content

    async def _create_bucket_if_missing(
        self,
        *,
        client: httpx.AsyncClient,
        bucket: str,
    ) -> None:
        bucket_url = f"{self._base_url}/storage/v1/bucket"
        headers = {
            "Authorization": f"Bearer {self._secret_key}",
            "apikey": self._secret_key,
            "content-type": "application/json",
        }
        payload = {"id": bucket, "name": bucket, "public": False}
        response = await client.post(bucket_url, headers=headers, json=payload)
        if response.status_code not in (200, 201, 409):
            raise StorageError(
                f"Failed to create storage bucket '{bucket}' ({response.status_code}): "
                f"{response.text[:200]}"
            )
