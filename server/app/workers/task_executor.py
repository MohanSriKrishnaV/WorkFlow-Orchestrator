import asyncio
from typing import Any


async def execute_task(
    task_type: str,
    payload: dict[str, Any],
) -> None:
    if task_type == "echo":
        text = payload.get("text", "")
        print(f"Echo task received text: {text}")

        await asyncio.sleep(1)

        print("Echo task completed successfully")
        return

    if task_type == "fail":
        await asyncio.sleep(1)
        raise RuntimeError("Intentional failure from fail task")

    raise ValueError(f"Unsupported task_type: {task_type}")