import json
from datetime import datetime, timezone

import aio_pika

from app.amqp.topology import declare_jobs_topology
from app.core.config import get_settings


settings = get_settings()


def _build_job_message_body(
    job_id: int,
    task_type: str,
    **extra: object,
) -> bytes:
    message_body = {
        "job_id": job_id,
        "task_type": task_type,
        **extra,
    }

    return json.dumps(message_body).encode("utf-8")


def _build_persistent_json_message(body: bytes) -> aio_pika.Message:
    return aio_pika.Message(
        body=body,
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )


async def publish_job_created(
    job_id: int,
    task_type: str,
) -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    async with connection:
        channel = await connection.channel()

        jobs_exchange, _queue = await declare_jobs_topology(channel)

        message = _build_persistent_json_message(
            _build_job_message_body(
                job_id=job_id,
                task_type=task_type,
            )
        )

        await jobs_exchange.publish(
            message,
            routing_key=settings.amqp_job_created_routing_key,
        )


async def publish_job_retry(
    job_id: int,
    task_type: str,
    retry_count: int,
    error_message: str | None = None,
) -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    async with connection:
        channel = await connection.channel()

        await declare_jobs_topology(channel)

        retry_exchange = await channel.get_exchange(
            settings.amqp_jobs_retry_exchange,
        )

        if retry_count == 1:
            routing_key = settings.amqp_jobs_retry_2s_routing_key
        elif retry_count == 2:
            routing_key = settings.amqp_jobs_retry_4s_routing_key
        else:
            routing_key = settings.amqp_jobs_retry_8s_routing_key

        message = _build_persistent_json_message(
            _build_job_message_body(
                job_id=job_id,
                task_type=task_type,
                retry_count=retry_count,
                error_message=error_message,
            )
        )

        await retry_exchange.publish(
            message,
            routing_key=routing_key,
        )


async def publish_job_dead_letter(
    job_id: int,
    task_type: str,
    retry_count: int,
    error_message: str,
) -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    async with connection:
        channel = await connection.channel()

        await declare_jobs_topology(channel)

        dlq_exchange = await channel.get_exchange(
            settings.amqp_jobs_dlq_exchange,
        )

        message = _build_persistent_json_message(
            _build_job_message_body(
                job_id=job_id,
                task_type=task_type,
                retry_count=retry_count,
                error_message=error_message,
                failed_at=datetime.now(timezone.utc).isoformat(),
            )
        )

        await dlq_exchange.publish(
            message,
            routing_key=settings.amqp_jobs_dlq_routing_key,
        )