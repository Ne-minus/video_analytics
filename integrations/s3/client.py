from contextlib import asynccontextmanager
from typing import Any

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from shared.config import settings


class S3StorageService:
    def __init__(self) -> None:
        self._bucket_name = settings.s3_bucket_name
        self._session = aioboto3.Session()

    @asynccontextmanager
    async def client(self):
        async with self._session.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region_name,
            use_ssl=settings.s3_use_ssl,
            config=Config(signature_version="s3v4"),
        ) as client:
            yield client

    async def ensure_bucket(self) -> None:
        async with self.client() as client:
            try:
                await client.head_bucket(Bucket=self._bucket_name)
            except ClientError:
                await client.create_bucket(Bucket=self._bucket_name)

    async def upload_bytes(
        self,
        *,
        data: bytes,
        key: str,
        content_type: str | None,
    ) -> dict[str, str]:
        async with self.client() as client:
            await client.put_object(
                Bucket=self._bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type or "application/octet-stream",
            )
        return {"bucket": self._bucket_name, "key": key}

    async def download_bytes(self, *, bucket: str, key: str) -> bytes:
        async with self.client() as client:
            response = await client.get_object(Bucket=bucket, Key=key)
            return await response["Body"].read()

    def health(self) -> dict[str, Any]:
        return {
            "endpoint_url": settings.s3_endpoint_url,
            "bucket_name": self._bucket_name,
        }
