from datetime import datetime, timezone, timedelta
from sqlalchemy import select,update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox_event import OutboxEvent, OutboxEventStatus
from datetime import datetime, timedelta, timezone



def build_outbox_event(
    event_type: str,
    payload: dict,
) -> OutboxEvent:
    return OutboxEvent(
        event_type=event_type,
        payload=payload,
        status=OutboxEventStatus.PENDING,
    )


async def create_outbox_event(
    db: AsyncSession,
    event_type: str,
    payload: dict,
) -> OutboxEvent:
    event = build_outbox_event(
        event_type=event_type,
        payload=payload,
    )

    db.add(event)
    await db.commit()
    await db.refresh(event)

    return event


async def get_pending_outbox_events(
    db: AsyncSession,
    limit: int = 10,
) -> list[OutboxEvent]:
    result = await db.execute(
        select(OutboxEvent)
        .where(OutboxEvent.status == OutboxEventStatus.PENDING)
        .order_by(OutboxEvent.created_at.asc())
        .limit(limit)
    )

    return list(result.scalars().all())


async def mark_outbox_event_publishing(
    db: AsyncSession,
    event: OutboxEvent,
) -> OutboxEvent:
    event.status = OutboxEventStatus.PUBLISHING
    event.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(event)

    return event


async def mark_outbox_event_published(
    db: AsyncSession,
    event: OutboxEvent,
) -> OutboxEvent:
    event.status = OutboxEventStatus.PUBLISHED
    event.published_at = datetime.now(timezone.utc)
    event.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(event)

    return event


async def mark_outbox_event_failed(
    db: AsyncSession,
    event_id: int,
    error_message: str,
) -> None:
    now = datetime.now(timezone.utc)

    event = await db.get(OutboxEvent, event_id)

    if event is None:
        return

    next_attempt_count = event.attempt_count + 1
    delay_seconds = calculate_outbox_retry_delay_seconds(next_attempt_count)

    event.status = OutboxEventStatus.FAILED
    event.attempt_count = next_attempt_count
    event.last_error = error_message
    event.next_attempt_at = now + timedelta(seconds=delay_seconds)
    event.updated_at = now

    await db.commit()

async def reset_failed_outbox_events_to_pending(
    db: AsyncSession,
    max_attempts: int,
) -> int:
    now = datetime.now(timezone.utc)

    stmt = (
        update(OutboxEvent)
        .where(OutboxEvent.status == OutboxEventStatus.FAILED)
        .where(OutboxEvent.attempt_count < max_attempts)
        .where(
            (OutboxEvent.next_attempt_at.is_(None))
            | (OutboxEvent.next_attempt_at <= now)
        )
        .values(
            status=OutboxEventStatus.PENDING,
            updated_at=now,
        )
    )

    result = await db.execute(stmt)
    await db.commit()

    return result.rowcount or 0


async def reset_stuck_publishing_outbox_events_to_pending(
    db: AsyncSession,
    older_than_seconds: int = 60,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)

    result = await db.execute(
        select(OutboxEvent)
        .where(OutboxEvent.status == OutboxEventStatus.PUBLISHING)
        .where(OutboxEvent.updated_at < cutoff)
    )

    events = list(result.scalars().all())

    for event in events:
        event.status = OutboxEventStatus.PENDING
        event.last_error = "Reset from stuck PUBLISHING state"

    await db.commit()

    return len(events)



def calculate_outbox_retry_delay_seconds(attempt_count: int) -> int:
    delays = [5, 30, 120, 300]

    index = max(0, min(attempt_count - 1, len(delays) - 1))
    return delays[index]

async def claim_next_pending_outbox_event(
    db: AsyncSession,
) -> OutboxEvent | None:
    now = datetime.now(timezone.utc)

    event_id_subquery = (
        select(OutboxEvent.id)
        .where(OutboxEvent.status == OutboxEventStatus.PENDING)
        .where(
            (OutboxEvent.next_attempt_at.is_(None))
            | (OutboxEvent.next_attempt_at <= now)
        )
        .order_by(OutboxEvent.created_at.asc())
        .limit(1)
        .scalar_subquery()
    )

    stmt = (
        update(OutboxEvent)
        .where(OutboxEvent.id == event_id_subquery)
        .where(OutboxEvent.status == OutboxEventStatus.PENDING)
        .values(
            status=OutboxEventStatus.PUBLISHING,
            updated_at=now,
            last_error=None,
            next_attempt_at=None,
        )
        .returning(OutboxEvent)
    )

    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    await db.commit()

    if event is None:
        return None

    await db.refresh(event)
    return event