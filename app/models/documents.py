from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class MediaDocument(BaseModel):
    document_id: str = Field(..., alias="_id")
    description: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def set_created_at(cls, v):
        return v or datetime.now(timezone.utc)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}