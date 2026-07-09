import json
import aio_pika

from app.amqp.connection import get_amqp_connection
from app.core.config import get_settings


async def publish_test_message(message: str) -> None:
    settings = get_settings()

    connection = await get_amqp_connection()

    async with connection:
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
            settings.amqp_exchange,
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )

        queue = await channel.declare_queue(
            settings.amqp_queue,
            durable=True,
        )

        await queue.bind(
            exchange,
            routing_key=settings.amqp_routing_key,
        )

        payload = {
            "message": message,
        }

        amqp_message = aio_pika.Message(
            body=json.dumps(payload).encode("utf-8"),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        )

        await exchange.publish(
            amqp_message,
            routing_key=settings.amqp_routing_key,
        )