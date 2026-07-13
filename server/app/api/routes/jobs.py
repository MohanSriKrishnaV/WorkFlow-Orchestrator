from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.models.job import Job
from app.schemas.job import JobCreateRequest, JobListResponse, JobResponse
from app.services.job_service import (
    create_job,
    get_job_by_id,
    list_jobs,
    mark_job_queued,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])
@router.post("", response_model=JobResponse)
async def create_job_endpoint(
    job_in: JobCreateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Job:
    job = await create_job(
        db=db,
        task_type=job_in.task_type,
        payload=job_in.payload,
        max_retries=job_in.max_retries,
    )

    return job


@router.get("", response_model=list[JobListResponse])
async def list_jobs_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
):
    return await list_jobs(db, limit=limit, offset=offset)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_endpoint(
    job_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    job = await get_job_by_id(db, job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job