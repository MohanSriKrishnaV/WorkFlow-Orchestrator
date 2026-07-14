import asyncio
from typing import Any
from app.workers.csv_profile_task import run_csv_profile_task
from sqlalchemy.ext.asyncio import AsyncSession
from app.workers.csv_clean_basic_task import run_csv_clean_basic_task
# async def execute_task(
#     task_type: str,
#     payload: dict[str, Any],
# ) -> None:
#     if task_type == "echo":
#         text = payload.get("text", "")
#         print(f"Echo task received text: {text}")

#         await asyncio.sleep(1)

#         print("Echo task completed successfully")
#         return

#     if task_type == "fail":
#         await asyncio.sleep(5)
#         raise RuntimeError("Intentional failure from fail task")

#     raise ValueError(f"Unsupported task_type: {task_type}")


async def execute_task(
    task_type: str,
    payload: dict | None,
    db: AsyncSession | None = None,

) -> dict:
    if task_type == "echo":
        return {
            "task_type": "echo",
            "payload": payload,
        }
    if task_type == "csv_profile":
        if db is None:
            raise ValueError("Database session is required for csv_profile task")

        return await run_csv_profile_task(
            db=db,
            payload=payload,
        )
    
    if task_type == "csv_clean_basic":
        if db is None:
            raise ValueError("Database session is required for csv_clean_basic task")

        return await run_csv_clean_basic_task(
            db=db,
            payload=payload,
        )


    if task_type == "fail":
        raise RuntimeError("Intentional failure for testing")

    raise ValueError(f"Unknown task_type: {task_type}")