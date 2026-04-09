import asyncio
import logging
from pathlib import Path
import uuid

from img2vlm.integrations.kafka.client import KafkaService, guess_mime_type
from img2vlm.integrations.s3.client import S3StorageService
from img2vlm.shared.config import settings

logger = logging.getLogger(__name__)


class DatasetImageProducer:
    def __init__(self) -> None:
        self._dataset_dir = Path(settings.simulator_dataset_dir)
        self._s3_service = S3StorageService()
        self._kafka_service = KafkaService(enable_input_consumer=False)

    async def close(self) -> None:
        await self._kafka_service.close()

    async def start(self) -> None:
        await self._s3_service.ensure_bucket()
        await self._kafka_service.start()
        if not self._dataset_dir.exists():
            logger.warning("Dataset directory does not exist yet: %s", self._dataset_dir)
            return
        if not self._dataset_dir.is_dir():
            logger.warning("Dataset path is not a directory: %s", self._dataset_dir)
            return

    async def produce_forever(self) -> None:
        while True:
            if not self._dataset_dir.exists() or not self._dataset_dir.is_dir():
                logger.warning("Waiting for dataset directory: %s", self._dataset_dir)
                await asyncio.sleep(max(1, settings.simulator_interval_seconds))
                continue

            images = sorted(
                path
                for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp")
                for path in self._dataset_dir.glob(pattern)
            )
            if not images:
                logger.warning("No images found in %s. Waiting...", self._dataset_dir)
                await asyncio.sleep(max(1, settings.simulator_interval_seconds))
                continue

            for image_path in images:
                await self._publish_image(image_path)
                logger.info("Published %s to topic %s", image_path.name, settings.kafka_input_topic)
                await asyncio.sleep(settings.simulator_interval_seconds)

    async def _publish_image(self, image_path: Path) -> None:
        s3_key = f"dataset-simulator/{image_path.stem}/{uuid.uuid4()}-{image_path.name}"
        image_bytes = image_path.read_bytes()
        content_type = guess_mime_type(image_path.name)
        uploaded = await self._s3_service.upload_bytes(
            data=image_bytes,
            key=s3_key,
            content_type=content_type,
        )
        await self._kafka_service.publish_image(
            document_id=f"{image_path.stem}-{uuid.uuid4()}",
            filename=image_path.name,
            content_type=content_type,
            s3_bucket=uploaded["bucket"],
            s3_key=uploaded["key"],
            metadata={
                "source": "dataset-simulator",
                "local_path": str(image_path),
            },
        )


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    producer = DatasetImageProducer()
    try:
        await producer.start()
        await producer.produce_forever()
    finally:
        await producer.close()


if __name__ == "__main__":
    asyncio.run(main())
