import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from img2vlm.integrations.gigachat.client import VLMClient
from img2vlm.integrations.kafka.client import KafkaService, generate_document_id
from img2vlm.integrations.s3.client import S3StorageService
from img2vlm.shared.config import settings
from img2vlm.vlm_api_service.schemas import HealthResponse, IndexResponse

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

vlm_client = VLMClient()
kafka_service = KafkaService()
s3_service = S3StorageService()
input_consumer_task: asyncio.Task[None] | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global input_consumer_task

    await s3_service.ensure_bucket()
    await kafka_service.start()
    input_consumer_task = asyncio.create_task(kafka_service.consume_input_forever(vlm_client, s3_service))
    yield
    if input_consumer_task is not None:
        input_consumer_task.cancel()
        try:
            await input_consumer_task
        except asyncio.CancelledError:
            pass
        input_consumer_task = None
    await kafka_service.close()
    await vlm_client.close()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    try:
        kafka_info = kafka_service.health()
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            services={"kafka": kafka_info, "s3": s3_service.health()},
        )
    except Exception as exc:
        logger.exception("Healthcheck failed")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {exc}") from exc


@app.post("/describe-and-index", response_model=IndexResponse)
async def describe_and_index(
    file: UploadFile = File(...),
    document_id: str | None = Form(default=None),
    metadata_json: str | None = Form(default=None),
) -> IndexResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    metadata: dict[str, Any] | None = None
    if metadata_json:
        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="metadata_json must be valid JSON") from exc

    resolved_document_id = document_id or generate_document_id()

    try:
        analysis = await vlm_client.describe_image(
            image_bytes=raw_bytes,
            filename=file.filename or resolved_document_id,
            content_type=file.content_type,
        )
        await kafka_service.publish_description(
            document_id=resolved_document_id,
            filename=file.filename or resolved_document_id,
            content_type=file.content_type,
            people_analysis={
                "people_count": analysis["people_count"],
                "people_present": analysis["people_present"],
                "people_summary": analysis["people_summary"],
            },
            scene_description=analysis["scene_description"],
            metadata=metadata,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Processing failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return IndexResponse(
        document_id=resolved_document_id,
        kafka_topic=settings.kafka_output_topic,
        people_analysis={
            "people_count": analysis["people_count"],
            "people_present": analysis["people_present"],
            "people_summary": analysis["people_summary"],
        },
        scene_description=analysis["scene_description"],
        kafka_result="queued",
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception):
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
