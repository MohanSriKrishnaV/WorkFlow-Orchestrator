import csv
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.file_service import (
    OUTPUT_DIR,
    create_file_record_for_existing_path,
    get_file_by_id,
)


def _get_bool_option(
    payload: dict[str, Any],
    name: str,
    default: bool,
) -> bool:
    value = payload.get(name, default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "y", "on"}

    return bool(value)


def _clean_header(
    header: str,
    *,
    trim_whitespace: bool,
    lowercase_headers: bool,
) -> str:
    cleaned_header = header

    if trim_whitespace:
        cleaned_header = cleaned_header.strip()

    if lowercase_headers:
        cleaned_header = cleaned_header.lower()

    return cleaned_header


def _clean_value(
    value: str | None,
    *,
    trim_whitespace: bool,
) -> str:
    if value is None:
        return ""

    if trim_whitespace:
        return value.strip()

    return value


async def run_csv_clean_basic_task(
    db: AsyncSession,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if payload is None:
        raise ValueError("csv_clean_basic payload is required")

    file_id = payload.get("file_id")

    if file_id is None:
        raise ValueError("csv_clean_basic payload missing file_id")

    drop_missing_rows = _get_bool_option(
        payload,
        "drop_missing_rows",
        True,
    )
    trim_whitespace = _get_bool_option(
        payload,
        "trim_whitespace",
        True,
    )
    lowercase_headers = _get_bool_option(
        payload,
        "lowercase_headers",
        False,
    )

    input_file = await get_file_by_id(db, int(file_id))

    if input_file is None:
        raise ValueError(f"File {file_id} not found")

    input_path = Path(input_file.storage_path)

    if not input_path.exists() or not input_path.is_file():
        raise ValueError(f"File {file_id} is missing from storage")

    if input_path.suffix.lower() != ".csv":
        raise ValueError("csv_clean_basic only supports .csv files")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_stored_filename = f"{uuid.uuid4().hex}_cleaned.csv"
    output_path = OUTPUT_DIR / output_stored_filename

    total_rows = 0
    kept_rows = 0
    removed_rows = 0
    original_column_names: list[str] = []
    output_column_names: list[str] = []

    with input_path.open("r", encoding="utf-8-sig", newline="") as input_csv:
        reader = csv.DictReader(input_csv)

        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row")

        original_column_names = list(reader.fieldnames)

        output_column_names = [
            _clean_header(
                column_name,
                trim_whitespace=trim_whitespace,
                lowercase_headers=lowercase_headers,
            )
            for column_name in original_column_names
        ]

        with output_path.open("w", encoding="utf-8", newline="") as output_csv:
            writer = csv.DictWriter(output_csv, fieldnames=output_column_names)
            writer.writeheader()

            for row in reader:
                total_rows += 1

                cleaned_row: dict[str, str] = {}

                for original_column_name, output_column_name in zip(
                    original_column_names,
                    output_column_names,
                    strict=True,
                ):
                    cleaned_row[output_column_name] = _clean_value(
                        row.get(original_column_name),
                        trim_whitespace=trim_whitespace,
                    )

                has_missing_value = any(
                    value == "" for value in cleaned_row.values()
                )

                if drop_missing_rows and has_missing_value:
                    removed_rows += 1
                    continue

                writer.writerow(cleaned_row)
                kept_rows += 1

    output_file = await create_file_record_for_existing_path(
        db=db,
        original_filename=f"cleaned_{input_file.original_filename}",
        stored_filename=output_stored_filename,
        content_type="text/csv",
        storage_path=output_path,
    )

    return {
        "task_type": "csv_clean_basic",
        "input_file_id": input_file.id,
        "output_file_id": output_file.id,
        "original_filename": input_file.original_filename,
        "output_filename": output_file.original_filename,
        "total_rows": total_rows,
        "kept_rows": kept_rows,
        "removed_rows": removed_rows,
        "columns": len(output_column_names),
        "original_column_names": original_column_names,
        "output_column_names": output_column_names,
        "options": {
            "drop_missing_rows": drop_missing_rows,
            "trim_whitespace": trim_whitespace,
            "lowercase_headers": lowercase_headers,
        },
    }