from typing import Any

from pydantic import BaseModel, Field


class PeopleAnalysis(BaseModel):
    people_count: int
    people_present: bool
    people_summary: str


class IndexResponse(BaseModel):
    status: str = "ok"
    document_id: str
    kafka_topic: str
    people_analysis: PeopleAnalysis
    scene_description: str
    kafka_result: str


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    services: dict[str, Any] = Field(default_factory=dict)
