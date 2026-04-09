from typing import Any, List, Optional
from pydantic import BaseModel, Field

class HealthCheck(BaseModel):
    healthy: bool

class MediaSearchRequest(BaseModel):
    text_query: str = ""
    top_k: int = 5


class MediaSearchResult(BaseModel):
    document_id: str
    scene_description: str
    score: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)