import json

import aio_pika

from app.amqp.topology import declare_jobs_topology
from app.core.config import get_settings


settings = get_settings()


async def publish_job_created(
    job_id: int,
    task_type: str,
) -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    async with connection:
        channel = await connection.channel()

        exchange, _queue = await declare_jobs_topology(channel)

        message_body = {
            "job_id": job_id,
            "task_type": task_type,
        }

        message = aio_pika.Message(
            body=json.dumps(message_body).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await exchange.publish(
            message,
            routing_key=settings.amqp_job_created_routing_key,
        )