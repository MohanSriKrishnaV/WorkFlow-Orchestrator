from pydantic import BaseModel
from fastapi import APIRouter

from app.amqp.publisher import publish_test_message


router = APIRouter(prefix="/amqp", tags=["AMQP Test"])


class TestMessageRequest(BaseModel):
    message: str


@router.post("/test")
async def publish_message(payload: TestMessageRequest):
    await publish_test_message(payload.message)

    return {
        "status": "published",
        "message": payload.message,
    }