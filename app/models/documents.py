from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator

class MediaDocument(BaseModel):
    document_id: str = Field(..., alias="_id")  # будем использовать как ID документа
    description: str
    dense_vector: List[float]  # размерность 384
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    updated_at: Optional[datetime] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def set_created_at(cls, v):
        return v or datetime.now(datetime.UTC)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }