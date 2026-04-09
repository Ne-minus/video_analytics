from fastapi import FastAPI
from app.services.es_client import es_client
from contextlib import asynccontextmanager
from app.endpoints import health, elastic, media
from app.services.kafka_consumer import KafkaESConsumer


kafka_consumer = KafkaESConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
#    await kafka_consumer.start()
    await es_client.info()
    yield
    await es_client.close()
#    await kafka_consumer.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(health.health_router, prefix="/health", tags=["health"])
app.include_router(elastic.elastic_router, prefix="/elastic", tags=["elastic"])
app.include_router(media.media_router, prefix="/media", tags=["media"])