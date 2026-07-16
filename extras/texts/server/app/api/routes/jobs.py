from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.models.job import Job
from fastapi import Query
from app.schemas.job import JobCreateRequest, JobListResponse, JobResponse ,JobStatus,JobSummaryResponse
from app.services.job_service import (
    create_job,
    get_job_by_id,
    list_jobs,
    mark_job_queued,
    retry_failed_job,
    cancel_job,
    get_job_summary
)

from app.services.job_validation_service import validate_job_create_payload

router = APIRouter(prefix="/jobs", tags=["Jobs"])



@router.get("/summary", response_model=JobSummaryResponse)
async def get_jobs_summary(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    return await get_job_summary(db)



@router.post("", response_model=JobResponse)
async def create_job_endpoint(
    job_create: JobCreateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Job:
    try:
        await validate_job_create_payload(
            db=db,
            task_type=job_create.task_type,
            payload=job_create.payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await create_job(db, job_create)


# @router.get("", response_model=list[JobListResponse])
# async def list_jobs_endpoint(
#     limit: int = Query(default=50, ge=1, le=100),
#     offset: int = Query(default=0, ge=0),
#     db: AsyncSession = Depends(get_db_session),
# ):
#     return await list_jobs(db, limit=limit, offset=offset)


@router.get("", response_model=list[JobResponse])
async def get_jobs(
    status: JobStatus | None = None,
    task_type: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> list[Job]:
    return await list_jobs(
        db=db,
        status=status,
        task_type=task_type,
        limit=limit,
        offset=offset,
    )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_endpoint(
    job_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    job = await get_job_by_id(db, job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job



@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> Job:
    job = await get_job_by_id(db, job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        return await retry_failed_job(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_existing_job(
    job_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> Job:
    job = await get_job_by_id(db, job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        return await cancel_job(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc