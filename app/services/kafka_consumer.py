import json
import asyncio
from aiokafka import AIOKafkaConsumer
from app.core.config import settings
from app.crud.media import create_document
from app.models.documents import MediaDocument
from app.services.embedding_service import embedding_service

class KafkaESConsumer:
    def __init__(self):
        self.consumer = None
        self.task = None

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            settings.KAFKA_CONSUME_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
            enable_auto_commit=settings.KAFKA_ENABLE_AUTO_COMMIT,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await self.consumer.start()
        self.task = asyncio.create_task(self._consume())
        print("Kafka consumer started")

    async def _consume(self):
        try:
            async for msg in self.consumer:
                payload = msg.value
                doc_id = payload["document_id"]
                description = payload["scene_description"]

                # Формируем документ для Elasticsearch
                doc_data = {
                    "_id": doc_id,
                    "description": description,
                    "dense_vector": None,
                    "created_at": payload.get("created_at"),
                    "updated_at": None,
                }
                # Валидируем через Pydantic модель
                doc = MediaDocument(**doc_data)
                await create_document(doc)
                print(f"Indexed document {doc_id}")
        except asyncio.CancelledError:
            print("Kafka consumer cancelled")
            await self.stop()

    async def stop(self):
        if self.consumer:
            await self.consumer.stop()
        if self.task and not self.task.done():
            self.task.cancel()