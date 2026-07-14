from pathlib import Path
from typing import Any

from app.services.file_service import get_file_by_id
from sqlalchemy.ext.asyncio import AsyncSession


CSV_TASK_TYPES = {"csv_profile", "csv_clean_basic"}

CSV_CLEAN_BOOLEAN_OPTIONS = {
    "drop_missing_rows",
    "trim_whitespace",
    "lowercase_headers",
}


def _is_integer_like(value: Any) -> bool:
    if isinstance(value, bool):
        return False

    if isinstance(value, int):
        return True

    if isinstance(value, str):
        return value.isdigit()

    return False


def _is_boolean_like(value: Any) -> bool:
    if isinstance(value, bool):
        return True

    if isinstance(value, int) and value in {0, 1}:
        return True

    if isinstance(value, str) and value.lower() in {
        "true",
        "false",
        "yes",
        "no",
        "y",
        "n",
        "1",
        "0",
        "on",
        "off",
    }:
        return True

    return False


async def validate_job_create_payload(
    db: AsyncSession,
    task_type: str,
    payload: dict[str, Any] | None,
) -> None:
    if task_type not in CSV_TASK_TYPES:
        return

    if payload is None:
        raise ValueError(f"{task_type} requires payload")

    file_id = payload.get("file_id")

    if file_id is None:
        raise ValueError(f"{task_type} requires payload.file_id")

    if not _is_integer_like(file_id):
        raise ValueError(f"{task_type} payload.file_id must be an integer")

    file_row = await get_file_by_id(db, int(file_id))

    if file_row is None:
        raise ValueError(f"File {file_id} not found")

    storage_path = Path(file_row.storage_path)

    if storage_path.suffix.lower() != ".csv":
        raise ValueError(f"{task_type} requires a .csv file")

    if task_type == "csv_clean_basic":
        for option_name in CSV_CLEAN_BOOLEAN_OPTIONS:
            if option_name in payload and not _is_boolean_like(payload[option_name]):
                raise ValueError(
                    f"csv_clean_basic payload.{option_name} must be boolean-like"
                )