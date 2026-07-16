from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.workflow import WorkflowStatus, WorkflowStepStatus


class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    input_file_id: int | None = None
    config: dict[str, Any] | None = None



class WorkflowStepResponse(BaseModel):
    id: int
    workflow_id: int
    job_id: int | None
    step_name: str
    step_order: int
    status: WorkflowStepStatus
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class WorkflowResponse(BaseModel):
    id: int
    name: str
    status: WorkflowStatus
    input_file_id: int | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = {
        "from_attributes": True
    }

    config: dict[str, Any] | None



class WorkflowDetailResponse(WorkflowResponse):
    steps: list[WorkflowStepResponse] = []


class CsvCleaningWorkflowCreateRequest(BaseModel):
    input_file_id: int
    clean_options: dict[str, Any] = Field(default_factory=dict)


class CsvCleaningWorkflowStartResponse(BaseModel):
    workflow_id: int
    workflow_status: WorkflowStatus
    first_step_id: int
    first_job_id: int
    message: str


class WorkflowResultStepResponse(BaseModel):
    step_name: str
    step_order: int
    status: WorkflowStepStatus
    job_id: int | None
    job_status: str | None


class WorkflowResultFileResponse(BaseModel):
    id: int
    original_filename: str | None = None
    storage_path: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    download_url: str | None = None



class WorkflowProgressResponse(BaseModel):
    steps_total: int
    steps_completed: int
    progress_percent: int
    current_step: str | None





class WorkflowFailureResponse(BaseModel):
    failed_step: str | None = None
    failed_job_id: int | None = None
    error_message: str | None = None

    
class CsvCleaningWorkflowResultResponse(BaseModel):
    workflow_id: int
    workflow_status: WorkflowStatus
    input_file_id: int | None
    cleaned_file_id: int | None
    input_profile: dict[str, Any] | None
    cleaning_result: dict[str, Any] | None
    output_profile: dict[str, Any] | None
    steps: list[WorkflowResultStepResponse]
    cleaned_file: WorkflowResultFileResponse | None
    progress: WorkflowProgressResponse
    failure: WorkflowFailureResponse | None = None


