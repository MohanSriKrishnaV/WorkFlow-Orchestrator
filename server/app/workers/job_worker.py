import asyncio
import json

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from app.amqp.job_publisher import publish_job_created
from app.amqp.topology import declare_jobs_topology
from app.core.config import get_settings
from app.db.database import AsyncSessionLocal
from app.services.job_service import (
    get_job_by_id,
    mark_job_failed,
    mark_job_retrying,
    mark_job_running,
    mark_job_success,
)
from app.workers.task_executor import execute_task
from datetime import datetime

settings = get_settings()


async def handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process():
        body = message.body.decode("utf-8")
        payload = json.loads(body)

        print("Received job message:")
        print(payload)

        job_id = payload.get("job_id")

        if job_id is None:
            raise ValueError("Job message missing job_id")

        async with AsyncSessionLocal() as db:
            job = await get_job_by_id(db, int(job_id))

            if job is None:
                raise ValueError(f"Job not found: {job_id}")

            job = await mark_job_running(db, job)

            try:
                await execute_task(
                    task_type=job.task_type,
                    payload=job.payload,
                )
            except Exception as exc:
                error_message = str(exc)

                if job.retry_count < job.max_retries:
                    job = await mark_job_retrying(db, job, error_message)

                    delay_seconds = min(2 ** job.retry_count, 30)

                    print(
                        f"[{datetime.now().isoformat()}] "
                        f"Job {job.id} failed: {error_message}. "
                        f"Retry {job.retry_count}/{job.max_retries} will be queued "
                        f"in {delay_seconds} seconds."
                    )

                    await asyncio.sleep(delay_seconds)

                    await publish_job_created(
                        job_id=job.id,
                        task_type=job.task_type,
                    )

                    print(
                        f"Job {job.id} retry {job.retry_count}/{job.max_retries} queued."
                    )
                    return

                await mark_job_failed(db, job, error_message)
                print(f"Job {job.id} failed permanently: {error_message}")
                return

            await mark_job_success(db, job)
            print(f"Job {job.id} completed successfully")





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


if __name__ == "__main__":
    asyncio.run(main())