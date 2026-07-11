from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus
from app.schemas.job import JobCreateRequest


async def create_job(
    db: AsyncSession,
    payload: JobCreateRequest,
) -> Job:
    job = Job(
        task_type=payload.task_type,
        payload=payload.payload,
        status=JobStatus.PENDING,
        retry_count=0,
        max_retries=payload.max_retries,
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    return job


async def list_jobs(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> list[Job]:
    stmt = (
        select(Job)
        .order_by(desc(Job.created_at))
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_job_by_id(
    db: AsyncSession,
    job_id: int,
) -> Job | None:
    stmt = select(Job).where(Job.id == job_id)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def mark_job_queued(
    db: AsyncSession,
    job: Job,
) -> Job:
    job.status = JobStatus.QUEUED

    await db.commit()
    await db.refresh(job)

    return job