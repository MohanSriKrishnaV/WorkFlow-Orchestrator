from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.job import JobStatus


class JobCreateRequest(BaseModel):
    task_type: str = Field(..., min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    max_retries: int = Field(default=3, ge=0, le=10)


class JobResponse(BaseModel):
    id: int
    task_type: str
    payload: dict[str, Any]
    status: JobStatus
    retry_count: int
    max_retries: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {
        "from_attributes": True
    }


class JobListResponse(BaseModel):
    id: int
    task_type: str
    status: JobStatus
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }