from fastapi import FastAPI
from storage.app.endpoints import elastic, health
from storage.app.es_client import es_client
from contextlib import asynccontextmanager
from storage.app.endpoints import media

@asynccontextmanager
async def lifespan(app: FastAPI):
    await es_client.info()
    yield
    await es_client.close()

app = FastAPI(lifespan=lifespan)
app.include_router(health.health_router, prefix="/health", tags=["health"])
app.include_router(elastic.elastic_router, prefix="/elastic", tags=["elastic"])
app.include_router(media.media_router, prefix="/media", tags=["media"])