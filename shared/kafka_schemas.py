from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ImageContentType(StrEnum):
    JPEG = "image/jpeg"
    JPG = "image/jpg"
    PNG = "image/png"
    WEBP = "image/webp"
    GIF = "image/gif"


class KafkaOutputMessage(BaseModel):
    document_id: str
    filename: str
    content_type: ImageContentType | None = None
    scene_description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
