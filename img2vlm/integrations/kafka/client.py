import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

from img2vlm.integrations.s3.client import S3StorageService
from img2vlm.integrations.gigachat.client import VLMClient
from img2vlm.shared.config import settings

logger = logging.getLogger(__name__)


class KafkaService:
    def __init__(self, *, enable_input_consumer: bool = True) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
        )
        self._input_consumer = (
            AIOKafkaConsumer(
                settings.kafka_input_topic,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_input_consumer_group,
                auto_offset_reset=settings.kafka_auto_offset_reset,
                enable_auto_commit=True,
                value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            )
            if enable_input_consumer
            else None
        )

    async def start(self) -> None:
        last_error: Exception | None = None
        for attempt in range(1, settings.kafka_start_retries + 1):
            try:
                await self._producer.start()
                if self._input_consumer is not None:
                    await self._input_consumer.start()
                return
            except KafkaConnectionError as exc:
                last_error = exc
                logger.warning(
                    "Kafka is not ready yet, retrying start (%s/%s) in %s seconds",
                    attempt,
                    settings.kafka_start_retries,
                    settings.kafka_retry_delay_seconds,
                )
                await asyncio.sleep(settings.kafka_retry_delay_seconds)

        raise RuntimeError(f"Failed to connect to Kafka after retries: {last_error}")

    async def close(self) -> None:
        await self._producer.stop()
        if self._input_consumer is not None:
            await self._input_consumer.stop()

    async def publish_image(
        self,
        *,
        filename: str,
        content_type: str | None,
        s3_bucket: str,
        s3_key: str,
        document_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "document_id": document_id,
            "filename": filename,
            "content_type": content_type or guess_mime_type(filename),
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._producer.send_and_wait(settings.kafka_input_topic, payload)

    async def publish_description(
        self,
        *,
        document_id: str,
        filename: str,
        content_type: str | None,
        scene_description: str,
        metadata: dict[str, Any] | None,
        created_at: str | None = None,
    ) -> None:
        payload = {
            "scene_description": scene_description,
            "document_id": document_id,
            "filename": filename,
            "content_type": content_type,
            "metadata": metadata or {},
            "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        }
        await self._producer.send_and_wait(settings.kafka_output_topic, payload)

    async def consume_input_forever(self, vlm_client: VLMClient, s3_service: S3StorageService) -> None:
        if self._input_consumer is None:
            raise RuntimeError("Kafka input consumer is disabled")
        try:
            async for message in self._input_consumer:
                payload = message.value
                try:
                    image_bytes = await s3_service.download_bytes(
                        bucket=payload["s3_bucket"],
                        key=payload["s3_key"],
                    )
                    analysis = await vlm_client.describe_image(
                        image_bytes=image_bytes,
                        filename=payload["filename"],
                        content_type=payload.get("content_type"),
                    )
                    await self.publish_description(
                        document_id=payload["document_id"],
                        filename=payload["filename"],
                        content_type=payload.get("content_type"),
                        scene_description=analysis["scene_description"],
                        metadata=payload.get("metadata"),
                        created_at=payload.get("created_at"),
                    )
                except Exception:
                    logger.exception("Failed to process input Kafka message: %s", payload)
        except asyncio.CancelledError:
            logger.info("Kafka input consumer task cancelled")
            raise

    def health(self) -> dict[str, Any]:
        return {
            "bootstrap_servers": settings.kafka_bootstrap_servers,
            "input_topic": settings.kafka_input_topic,
            "output_topic": settings.kafka_output_topic,
            "producer_started": getattr(self._producer, "_sender", None) is not None,
            "input_consumer_enabled": self._input_consumer is not None,
            "input_consumer_started": (
                getattr(self._input_consumer, "_fetcher", None) is not None
                if self._input_consumer is not None
                else False
            ),
        }


def generate_document_id() -> str:
    import uuid
    return str(uuid.uuid4())


def guess_mime_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"
