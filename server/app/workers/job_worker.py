import asyncio
import json
from datetime import datetime

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from app.amqp.job_publisher import publish_job_dead_letter, publish_job_retry
from app.amqp.topology import declare_jobs_topology
from app.core.config import get_settings
from app.db.database import AsyncSessionLocal
from app.models.job import JobStatus
from app.services.job_service import (
    claim_job_for_processing,
    get_job_by_id,
    mark_job_failed,
    mark_job_retrying,
    mark_job_success,
)
from app.services.workflow_service import update_workflow_step_status_for_job,create_next_step_after_success,update_workflow_step_status_for_job,refresh_csv_workflow_status

from app.workers.task_executor import execute_task
from sqlalchemy import select
from app.models.workflow import WorkflowStep

settings = get_settings()


async def handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process():
        body = message.body.decode("utf-8")
        payload = json.loads(body)

        print(f"[{datetime.now().isoformat()}] Received job message:")
        print(payload)

        job_id = payload.get("job_id")

        if job_id is None:
            raise ValueError("Job message missing job_id")

        async with AsyncSessionLocal() as db:
            job = await claim_job_for_processing(db, job_id)

            if job is None:
                existing_job = await get_job_by_id(db, job_id)

                if existing_job is None:
                    print(f"Job {job_id} not found. Ignoring message.")
                    return

                print(
                    f"Job {job_id} is already {existing_job.status}. "
                    "Ignoring duplicate/non-claimable message."
                )
                return

            await update_workflow_step_status_for_job(
                db=db,
                job_id=job.id,
                job_status=JobStatus.RUNNING,
            )

            await _refresh_parent_workflow_for_job(db, job.id)

            await db.commit()

            try:
                task_result = await execute_task(
                    task_type=job.task_type,
                    payload=job.payload,
                    db=db,
                )
            except Exception as exc:
                error_message = str(exc)

                if job.retry_count < job.max_retries:
                    job = await mark_job_retrying(db, job, error_message)

                    await publish_job_retry(
                        job_id=job.id,
                        task_type=job.task_type,
                        retry_count=job.retry_count,
                        error_message=error_message,
                    )

                    print(
                        f"[{datetime.now().isoformat()}] "
                        f"Job {job.id} failed: {error_message}. "
                        f"Retry {job.retry_count}/{job.max_retries} sent to retry queue."
                    )
                    return

                job = await mark_job_failed(db, job, error_message)

                await update_workflow_step_status_for_job(
                    db=db,
                    job_id=job.id,
                    job_status=JobStatus.FAILED,
                )

                await _refresh_parent_workflow_for_job(db, job.id)

                await db.commit()

                await publish_job_dead_letter(
                    job_id=job.id,
                    task_type=job.task_type,
                    retry_count=job.retry_count,
                    error_message=error_message,
                )

                print(
                    f"[{datetime.now().isoformat()}] "
                    f"Job {job.id} failed permanently: {error_message}. "
                    f"Sent to DLQ."
                )
                return

            job = await mark_job_success(db, job, task_result)

            await update_workflow_step_status_for_job(
                db=db,
                job_id=job.id,
                job_status=JobStatus.SUCCESS,
            )

            await _refresh_parent_workflow_for_job(db, job.id)

            await db.commit()

            await create_next_step_after_success(
                db=db,
                completed_job_id=job.id,
            )

            print(
                f"[{datetime.now().isoformat()}] "
                f"Job {job.id} completed successfully."
            )


async def main() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    async with connection:
        channel = await connection.channel()

        await channel.set_qos(prefetch_count=1)

        _exchange, queue = await declare_jobs_topology(channel)

        await queue.consume(handle_message)

        print("Job worker started.")
        print(f"Listening on queue: {settings.amqp_jobs_queue}")
        print("Press CTRL+C to stop.")

        await asyncio.Future()



async def _refresh_parent_workflow_for_job(db, job_id: int) -> None:
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.job_id == job_id)
    )
    step = result.scalar_one_or_none()
    if step is not None:
        await refresh_csv_workflow_status(db, step.workflow_id)

if __name__ == "__main__":
    asyncio.run(main())