import aio_pika
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractQueue

from app.core.config import get_settings


settings = get_settings()


async def declare_jobs_topology(
    channel: AbstractChannel,
) -> tuple[AbstractExchange, AbstractQueue]:
    # Main exchange and queue
    jobs_exchange = await channel.declare_exchange(
        settings.amqp_jobs_exchange,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    jobs_queue = await channel.declare_queue(
        settings.amqp_jobs_queue,
        durable=True,
    )

    await jobs_queue.bind(
        jobs_exchange,
        routing_key=settings.amqp_job_created_routing_key,
    )

    # Retry exchange
    retry_exchange = await channel.declare_exchange(
        settings.amqp_jobs_retry_exchange,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    # Retry queue: 2 seconds
    retry_2s_queue = await channel.declare_queue(
        settings.amqp_jobs_retry_2s_queue,
        durable=True,
        arguments={
            "x-message-ttl": 2000,
            "x-dead-letter-exchange": settings.amqp_jobs_exchange,
            "x-dead-letter-routing-key": settings.amqp_job_created_routing_key,
        },
    )

    await retry_2s_queue.bind(
        retry_exchange,
        routing_key=settings.amqp_jobs_retry_2s_routing_key,
    )

    # Retry queue: 4 seconds
    retry_4s_queue = await channel.declare_queue(
        settings.amqp_jobs_retry_4s_queue,
        durable=True,
        arguments={
            "x-message-ttl": 4000,
            "x-dead-letter-exchange": settings.amqp_jobs_exchange,
            "x-dead-letter-routing-key": settings.amqp_job_created_routing_key,
        },
    )

    await retry_4s_queue.bind(
        retry_exchange,
        routing_key=settings.amqp_jobs_retry_4s_routing_key,
    )

    # Retry queue: 8 seconds
    retry_8s_queue = await channel.declare_queue(
        settings.amqp_jobs_retry_8s_queue,
        durable=True,
        arguments={
            "x-message-ttl": 8000,
            "x-dead-letter-exchange": settings.amqp_jobs_exchange,
            "x-dead-letter-routing-key": settings.amqp_job_created_routing_key,
        },
    )

    await retry_8s_queue.bind(
        retry_exchange,
        routing_key=settings.amqp_jobs_retry_8s_routing_key,
    )

    # Final DLQ exchange and queue
    dlq_exchange = await channel.declare_exchange(
        settings.amqp_jobs_dlq_exchange,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    dlq_queue = await channel.declare_queue(
        settings.amqp_jobs_dlq_queue,
        durable=True,
    )

    await dlq_queue.bind(
        dlq_exchange,
        routing_key=settings.amqp_jobs_dlq_routing_key,
    )

    return jobs_exchange, jobs_queue