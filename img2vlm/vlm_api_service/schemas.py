from typing import Any

from pydantic import BaseModel, Field


class IndexResponse(BaseModel):
    status: str = "ok"
    document_id: str
    kafka_topic: str
    scene_description: str
    kafka_result: str


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    services: dict[str, Any] = Field(default_factory=dict)
