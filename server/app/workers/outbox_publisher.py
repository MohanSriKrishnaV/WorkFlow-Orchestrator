import asyncio 
from datetime import datetime

from app.amqp.job_publisher import publish_job_created
from app.db.database import AsyncSessionLocal
from app.models.outbox_event import OutboxEvent,OutboxEventStatus
from app.services.job_service import get_job_by_id, mark_job_queued
from app.services.outbox_service import (
    claim_next_pending_outbox_event,
    get_pending_outbox_events,
    mark_outbox_event_failed,
    mark_outbox_event_published,
    mark_outbox_event_publishing,
    reset_failed_outbox_events_to_pending,
    reset_stuck_publishing_outbox_events_to_pending,
)

from app.services.job_service import get_job_by_id, mark_job_queued
from app.services.outbox_service import claim_next_pending_outbox_event


async def publish_outbox_event(db, event: OutboxEvent) -> None:
    if event.event_type == "job.created":
        job_id = int(event.payload["job_id"])
        task_type = str(event.payload["task_type"])

        await publish_job_created(
            job_id=job_id,
            task_type=task_type,
        )

        job = await get_job_by_id(db, job_id)

        if job is None:
            raise ValueError(f"Job not found for outbox event: {job_id}")

        await mark_job_queued(db, job)

        return

    raise ValueError(f"Unsupported outbox event_type: {event.event_type}")



async def process_pending_events_once() -> int:
    processed_count = 0

    while True:
        async with AsyncSessionLocal() as db:
            event = await claim_next_pending_outbox_event(db)

            if event is None:
                break

            try:
                await publish_outbox_event(db,event)

                await mark_outbox_event_published(db, event)

                print(
                    f"[{datetime.now().isoformat()}] "
                    f"Published outbox event {event.id}."
                )

            except Exception as exc:
                await mark_outbox_event_failed(db, event.id, str(exc))

                print(
                    f"[{datetime.now().isoformat()}] "
                    f"Failed to publish outbox event {event.id}: {exc}"
                )

            processed_count += 1

    return processed_count

async def recover_outbox_events_once() -> int:
    async with AsyncSessionLocal() as db:
        failed_reset_count = await reset_failed_outbox_events_to_pending(
            db=db,
            max_attempts=5,
        )

        stuck_reset_count = await reset_stuck_publishing_outbox_events_to_pending(
            db=db,
            older_than_seconds=60,
        )

        total_reset_count = failed_reset_count + stuck_reset_count

        if total_reset_count > 0:
            print(
                f"[{datetime.now().isoformat()}] "
                f"Recovered {total_reset_count} outbox event(s): "
                f"{failed_reset_count} FAILED, "
                f"{stuck_reset_count} stuck PUBLISHING"
            )

        return total_reset_count


async def main() -> None:
    print("Outbox publisher started.")
    print("Polling outbox_events for PENDING events.")
    print("Recovering FAILED and stuck PUBLISHING events.")
    print("Press CTRL+C to stop.")

    while True:
        await recover_outbox_events_once()

        processed_count = await process_pending_events_once()

        if processed_count == 0:
            await asyncio.sleep(1)




if __name__ == "__main__":
    asyncio.run(main())