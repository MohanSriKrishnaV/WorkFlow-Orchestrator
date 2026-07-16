from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.models.workflow import Workflow
from app.schemas.workflow import (
    CsvCleaningWorkflowCreateRequest,
    CsvCleaningWorkflowResultResponse,
    CsvCleaningWorkflowStartResponse,
    WorkflowCreateRequest,
    WorkflowDetailResponse,
    WorkflowResponse,
)
from app.services.workflow_service import (
    create_workflow,
    get_workflow_by_id,
    get_csv_cleaning_workflow_result,
    list_workflows,
    start_csv_cleaning_workflow,
)


router = APIRouter(prefix="/workflows", tags=["workflows"])



@router.get("/{workflow_id}/result", response_model=CsvCleaningWorkflowResultResponse)
async def get_csv_cleaning_workflow_result_endpoint(
    workflow_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    try:
        result = await get_csv_cleaning_workflow_result(
            db=db,
            workflow_id=workflow_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return result


@router.post("", response_model=WorkflowResponse)
async def create_workflow_endpoint(
    workflow_create: WorkflowCreateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Workflow:
    return await create_workflow(
        db=db,
        workflow_create=workflow_create,
    )


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> list[Workflow]:
    return await list_workflows(
        db=db,
        limit=limit,
        offset=offset,
    )


@router.post("/csv-cleaning", response_model=CsvCleaningWorkflowStartResponse)
async def start_csv_cleaning_workflow_endpoint(
    request: CsvCleaningWorkflowCreateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    try:
        return await start_csv_cleaning_workflow(
            db=db,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow_endpoint(
    workflow_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> Workflow:
    workflow = await get_workflow_by_id(
        db=db,
        workflow_id=workflow_id,
    )

    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return workflow