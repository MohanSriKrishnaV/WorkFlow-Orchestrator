import asyncio
import json

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from app.amqp.topology import declare_jobs_topology
from app.core.config import get_settings


settings = get_settings()


async def handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process():
        body = message.body.decode("utf-8")
        payload = json.loads(body)

        print("Received job message:")
        print(payload)

        job_id = payload.get("job_id")
        task_type = payload.get("task_type")

        print(f"Processing job_id={job_id}, task_type={task_type}")

        # Phase 3 only:
        # We are just consuming and printing the message.
        # In Phase 4, we will fetch the job from DB and update status.


async def main() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    async with connection:
        channel = await connection.channel()

        # Process one message at a time for now.
        await channel.set_qos(prefetch_count=1)

        _exchange, queue = await declare_jobs_topology(channel)

        await queue.consume(handle_message)

        print("Job worker started.")
        print(f"Listening on queue: {settings.amqp_jobs_queue}")
        print("Press CTRL+C to stop.")

        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())