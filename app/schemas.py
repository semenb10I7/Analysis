import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str | None
    status: str
    created_at: datetime
    updated_at: datetime

class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    extension: str
    size_bytes: int
    status: str
    extraction_error: str | None

class UploadResponse(BaseModel):
    session: SessionOut
    files: list[FileOut]
    skipped: list[str] = []

class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    text: str
    language: str | None
    sentiment_label: str | None
    sentiment_confidence: float | None
    note: str | None

class ResultFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    filename: str
    reviews: list[ReviewOut]

class StatusResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    processed: int
    total: int
    progress: int

class ReviewUpdate(BaseModel):
    sentiment_label: str 