import asyncio
import json

import aio_pika

from app.amqp.connection import get_amqp_connection
from app.core.config import get_settings


async def handle_message(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body.decode("utf-8"))

        print("Received message:", body)
        print("ACK sent")


async def main():
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

        print("Test worker started")
        print(f"Waiting for messages from queue: {settings.amqp_queue}")

        await queue.consume(handle_message)

        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())