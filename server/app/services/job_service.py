from datetime import datetime, timezone

from sqlalchemy import desc, select,update
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.outbox_service import build_outbox_event
from app.models.job import Job, JobStatus
from app.schemas.job import JobCreateRequest

# async def create_job(
#     db: AsyncSession,
#     payload: JobCreateRequest,
# ) -> Job:
#     job = Job(
#         task_type=payload.task_type,
#         payload=payload.payload,
#         status=JobStatus.PENDING,
#         retry_count=0,
#         max_retries=payload.max_retries,
#     )

#     db.add(job)
#     await db.commit()
#     await db.refresh(job)

#     return job



async def create_job(
    db: AsyncSession,
    task_type: str,
    payload: dict,
    max_retries: int = 3,
) -> Job:
    job = Job(
        task_type=task_type,
        payload=payload,
        status=JobStatus.PENDING,
        retry_count=0,
        max_retries=max_retries,
    )

    db.add(job)

    # Flush assigns job.id without committing yet.
    await db.flush()

    outbox_event = build_outbox_event(
        event_type="job.created",
        payload={
            "job_id": job.id,
            "task_type": job.task_type,
        },
    )

    db.add(outbox_event)

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
    job.error_message = None

    await db.commit()
    await db.refresh(job)

    return job


async def mark_job_running(
    db: AsyncSession,
    job: Job,
) -> Job:
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)
    job.error_message = None

    await db.commit()
    await db.refresh(job)

    return job


async def mark_job_success(
    db: AsyncSession,
    job: Job,
) -> Job:
    job.status = JobStatus.SUCCESS
    job.completed_at = datetime.now(timezone.utc)
    job.error_message = None

    await db.commit()
    await db.refresh(job)

    return job


async def mark_job_failed(
    db: AsyncSession,
    job: Job,
    error_message: str,
) -> Job:
    job.status = JobStatus.FAILED
    job.completed_at = datetime.now(timezone.utc)
    job.error_message = error_message

    await db.commit()
    await db.refresh(job)

    return job

async def mark_job_retrying(
    db: AsyncSession,
    job: Job,
    error_message: str,
) -> Job:
    job.retry_count += 1
    job.status = JobStatus.QUEUED
    job.completed_at = None
    job.error_message = error_message

    await db.commit()
    await db.refresh(job)

    return job


async def claim_job_for_processing(
    db: AsyncSession,
    job_id: int,
) -> Job | None:
    stmt = (
        update(Job)
        .where(Job.id == job_id)
        .where(Job.status.in_([JobStatus.PENDING, JobStatus.QUEUED]))
        .values(
            status=JobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            error_message=None,
        )
        .returning(Job)
    )

    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    await db.commit()

    if job is None:
        return None

    await db.refresh(job)
    return job