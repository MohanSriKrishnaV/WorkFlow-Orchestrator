import aio_pika
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractQueue

from app.core.config import get_settings


settings = get_settings()


async def declare_jobs_topology(
    channel: AbstractChannel,
) -> tuple[AbstractExchange, AbstractQueue]:
    exchange = await channel.declare_exchange(
        settings.amqp_exchange,
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    queue = await channel.declare_queue(
        settings.amqp_jobs_queue,
        durable=True,
    )

    await queue.bind(
        exchange,
        routing_key=settings.amqp_job_created_routing_key,
    )

    return exchange, queue