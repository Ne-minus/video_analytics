import asyncio
import os
from typing import Any, Dict

import httpx
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from agent.llm.embeddings import get_embeddings


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and str(v).strip() != "" else default


async def main() -> None:
    storage_url = _env("STORAGE_URL", "http://storage:8000").rstrip("/")
    kafka_bootstrap = _env("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    kafka_topic = _env("KAFKA_OUTPUT_TOPIC", "output")
    group_id = _env("KAFKA_OUTPUT_CONSUMER_GROUP", "indexer")

    embeddings = get_embeddings()
    client = httpx.AsyncClient(base_url=storage_url, timeout=30.0)

    consumer = AIOKafkaConsumer(
        kafka_topic,
        bootstrap_servers=kafka_bootstrap,
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda value: __import__("json").loads(value.decode("utf-8")),
    )

    # Kafka might start a bit later than us.
    for _ in range(30):
        try:
            await consumer.start()
            break
        except KafkaConnectionError:
            await asyncio.sleep(2)
    else:
        raise RuntimeError("Kafka is not ready (indexer)")

    try:
        async for message in consumer:
            payload: Dict[str, Any] = message.value or {}
            doc_id = str(payload.get("document_id") or "").strip()
            scene = str(payload.get("scene_description") or "").strip()
            created_at = payload.get("created_at")

            if not doc_id or not scene:
                continue

            aembed_query = getattr(embeddings, "aembed_query", None)
            if callable(aembed_query):
                vec = await aembed_query(scene)
            else:
                vec = await asyncio.to_thread(embeddings.embed_query, scene)

            doc = {
                "_id": doc_id,
                "description": scene,
                "dense_vector": vec,
                "created_at": created_at,
            }

            # Idempotent: ES id == document_id. If already exists, index overwrites.
            await client.post("/media/", json=doc)
    finally:
        await consumer.stop()
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())

