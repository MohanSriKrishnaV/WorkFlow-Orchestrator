import csv
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.file_service import get_file_by_id


async def run_csv_profile_task(
    db: AsyncSession,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if payload is None:
        raise ValueError("csv_profile payload is required")

    file_id = payload.get("file_id")

    if file_id is None:
        raise ValueError("csv_profile payload missing file_id")

    file_row = await get_file_by_id(db, int(file_id))

    if file_row is None:
        raise ValueError(f"File {file_id} not found")

    storage_path = Path(file_row.storage_path)

    if not storage_path.exists() or not storage_path.is_file():
        raise ValueError(f"File {file_id} is missing from storage")

    if storage_path.suffix.lower() != ".csv":
        raise ValueError("csv_profile only supports .csv files")

    row_count = 0
    column_names: list[str] = []
    missing_values: dict[str, int] = {}

    with storage_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row")

        column_names = list(reader.fieldnames)
        missing_values = {column_name: 0 for column_name in column_names}

        for row in reader:
            row_count += 1

            for column_name in column_names:
                value = row.get(column_name)

                if value is None or value.strip() == "":
                    missing_values[column_name] += 1

    return {
        "task_type": "csv_profile",
        "file_id": file_row.id,
        "original_filename": file_row.original_filename,
        "rows": row_count,
        "columns": len(column_names),
        "column_names": column_names,
        "missing_values": missing_values,
    }