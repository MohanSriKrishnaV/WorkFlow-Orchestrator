from datetime import datetime, timezone

from sqlalchemy import desc, select,update,update
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.outbox_service import build_outbox_event
from app.models.job import Job, JobStatus
from app.schemas.job import JobCreateRequest
from app.services.outbox_service import create_outbox_event
from sqlalchemy import func, select

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
    status: JobStatus | None = None,
    task_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Job]:
    stmt = select(Job).order_by(Job.created_at.desc())

    if status is not None:
        stmt = stmt.where(Job.status == status)

    if task_type is not None:
        stmt = stmt.where(Job.task_type == task_type)

    stmt = stmt.limit(limit).offset(offset)

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
    result: dict | None = None,
) -> Job:
    now = datetime.now(timezone.utc)
    job.status = JobStatus.SUCCESS
    job.result = result
    job.completed_at = now
    job.updated_at = now
    job.error_message = None

    await db.commit()
    await db.refresh(job)

    return job


async def mark_job_failed(
    db: AsyncSession,
    job: Job,
    error_message: str,
) -> Job:
    now = datetime.now(timezone.utc)
    job.status = JobStatus.FAILED
    job.completed_at = now
    job.updated_at = now
    job.error_message = error_message

    await db.commit()
    await db.refresh(job)

    return job

async def mark_job_retrying(
    db: AsyncSession,
    job: Job,
    error_message: str,
) -> Job:
    now = datetime.now(timezone.utc)
    job.retry_count += 1
    job.status = JobStatus.QUEUED
    job.completed_at = None
    job.updated_at = now
    job.error_message = error_message

    await db.commit()
    await db.refresh(job)

    return job


async def claim_job_for_processing(
    db: AsyncSession,
    job_id: int,
) -> Job | None:
    now = datetime.now(timezone.utc)
    stmt = (
        update(Job)
        .where(Job.id == job_id)
        .where(Job.status.in_([JobStatus.PENDING, JobStatus.QUEUED]))
        .values(
            status=JobStatus.RUNNING,
            started_at=now,
            updated_at=now,
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


# async def retry_failed_job(
#     db: AsyncSession,
#     job: Job,
# ) -> Job:
#     if job.status != JobStatus.FAILED:
#         raise ValueError("Only FAILED jobs can be retried")

#     now = datetime.now(timezone.utc)

#     job.status = JobStatus.QUEUED
#     job.retry_count = 0
#     job.error_message = None
#     job.result = None
#     job.finished_at = None  # use completed_at if that is your actual field
#     job.updated_at = now

#     outbox_event = OutboxEvent(
#         event_type="job.created",
#         payload={
#             "job_id": job.id,
#             "task_type": job.task_type,
#         },
#         status=OutboxEventStatus.PENDING,
#     )

#     db.add(outbox_event)

#     await db.commit()
#     await db.refresh(job)

#     return job


async def retry_failed_job(
    db: AsyncSession,
    job: Job,
) -> Job:
    if job.status != JobStatus.FAILED:
        raise ValueError("Only FAILED jobs can be retried")

    now = datetime.now(timezone.utc)

    job.status = JobStatus.QUEUED
    job.retry_count = 0
    job.error_message = None
    job.result = None
    job.finished_at = None
    job.updated_at = now

    await create_outbox_event(
        db=db,
        event_type="job.created",
        payload={
            "job_id": job.id,
            "task_type": job.task_type,
        },
    )

    await db.commit()
    await db.refresh(job)

    return job

async def cancel_job(
    db: AsyncSession,
    job: Job,
) -> Job:
    if job.status not in [JobStatus.PENDING, JobStatus.QUEUED]:
        raise ValueError(
            f"Only PENDING or QUEUED jobs can be cancelled. Current status: {job.status}"
        )

    now = datetime.now(timezone.utc)

    job.status = JobStatus.CANCELLED
    job.error_message = "Job cancelled by user"
    job.finished_at = now  # use completed_at if your model uses completed_at
    job.updated_at = now

    await db.commit()
    await db.refresh(job)

    return job



async def get_job_summary(
    db: AsyncSession,
) -> dict[str, object]:
    total_result = await db.execute(
        select(func.count()).select_from(Job)
    )
    total_jobs = int(total_result.scalar_one())

    status_result = await db.execute(
        select(Job.status, func.count()).group_by(Job.status)
    )

    by_status = {
        status.value if hasattr(status, "value") else str(status): int(count)
        for status, count in status_result.all()
    }

    task_type_result = await db.execute(
        select(Job.task_type, func.count()).group_by(Job.task_type)
    )

    by_task_type = {
        str(task_type): int(count)
        for task_type, count in task_type_result.all()
    }

    return {
        "total_jobs": total_jobs,
        "by_status": by_status,
        "by_task_type": by_task_type,
    }
