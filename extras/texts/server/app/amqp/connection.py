import aio_pika
from aio_pika.abc import AbstractRobustConnection

from app.core.config import get_settings


async def get_amqp_connection() -> AbstractRobustConnection:
    settings = get_settings()

    if not settings.rabbitmq_url:
        raise RuntimeError("RABBITMQ_URL is not configured")

    return await aio_pika.connect_robust(settings.rabbitmq_url)