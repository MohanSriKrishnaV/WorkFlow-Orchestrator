import csv
import re
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


def _normalize_column_name(header: str) -> str:
    normalized = header.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")

    return normalized or "column"


def _make_unique_headers(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    unique_headers: list[str] = []

    for header in headers:
        count = seen.get(header, 0)

        if count == 0:
            unique_headers.append(header)
        else:
            unique_headers.append(f"{header}_{count + 1}")

        seen[header] = count + 1

    return unique_headers


def _clean_header(
    header: str,
    *,
    trim_whitespace: bool,
    lowercase_headers: bool,
    normalize_column_names: bool,
) -> str:
    if normalize_column_names:
        return _normalize_column_name(header)

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


def _detect_csv_dialect(input_csv) -> csv.Dialect:
    sample = input_csv.read(4096)
    input_csv.seek(0)

    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        return csv.excel


async def run_csv_clean_basic_task(
    db: AsyncSession,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if payload is None:
        raise ValueError("csv_clean_basic payload is required")

    file_id = payload.get("file_id")

    if file_id is None:
        raise ValueError("csv_clean_basic payload missing file_id")

    clean_options = payload.get("clean_options", payload)

    if not isinstance(clean_options, dict):
        clean_options = {}

    drop_missing_rows = _get_bool_option(
        clean_options,
        "drop_missing_rows",
        True,
    )
    trim_whitespace = _get_bool_option(
        clean_options,
        "trim_whitespace",
        True,
    )
    lowercase_headers = _get_bool_option(
        clean_options,
        "lowercase_headers",
        False,
    )
    remove_empty_rows = _get_bool_option(
        clean_options,
        "remove_empty_rows",
        True,
    )
    remove_duplicate_rows = _get_bool_option(
        clean_options,
        "remove_duplicate_rows",
        True,
    )
    normalize_column_names = _get_bool_option(
        clean_options,
        "normalize_column_names",
        True,
    )
    remove_empty_columns = _get_bool_option(
        clean_options,
        "remove_empty_columns",
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
    removed_empty_rows = 0
    removed_duplicate_rows = 0
    removed_empty_columns = 0

    original_column_names: list[str] = []
    output_column_names: list[str] = []
    final_column_names: list[str] = []

    seen_rows: set[tuple[str, ...]] = set()

    with input_path.open("r", encoding="utf-8-sig", newline="") as input_csv:
        dialect = _detect_csv_dialect(input_csv)
        reader = csv.DictReader(input_csv, dialect=dialect)

        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row")

        original_column_names = list(reader.fieldnames)

        output_column_names = [
            _clean_header(
                column_name,
                trim_whitespace=trim_whitespace,
                lowercase_headers=lowercase_headers,
                normalize_column_names=normalize_column_names,
            )
            for column_name in original_column_names
        ]

        output_column_names = _make_unique_headers(output_column_names)

        cleaned_rows: list[dict[str, str]] = []

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

            is_empty_row = all(
                value.strip() == "" for value in cleaned_row.values()
            )

            if remove_empty_rows and is_empty_row:
                removed_rows += 1
                removed_empty_rows += 1
                continue

            has_missing_value = any(
                value.strip() == "" for value in cleaned_row.values()
            )

            if drop_missing_rows and has_missing_value:
                removed_rows += 1
                continue

            cleaned_rows.append(cleaned_row)

        final_column_names = output_column_names

        if remove_empty_columns:
            final_column_names = [
                column_name
                for column_name in output_column_names
                if any(
                    row.get(column_name, "").strip() != ""
                    for row in cleaned_rows
                )
            ]

            removed_empty_columns = len(output_column_names) - len(final_column_names)

        with output_path.open("w", encoding="utf-8", newline="") as output_csv:
            writer = csv.DictWriter(output_csv, fieldnames=final_column_names)
            writer.writeheader()

            for cleaned_row in cleaned_rows:
                final_row = {
                    column_name: cleaned_row.get(column_name, "")
                    for column_name in final_column_names
                }

                row_signature = tuple(
                    final_row[column_name] for column_name in final_column_names
                )

                if remove_duplicate_rows and row_signature in seen_rows:
                    removed_rows += 1
                    removed_duplicate_rows += 1
                    continue

                seen_rows.add(row_signature)

                writer.writerow(final_row)
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
        "removed_empty_rows": removed_empty_rows,
        "removed_duplicate_rows": removed_duplicate_rows,
        "removed_empty_columns": removed_empty_columns,
        "columns": len(final_column_names),
        "original_column_names": original_column_names,
        "output_column_names": final_column_names,
        "options": {
            "drop_missing_rows": drop_missing_rows,
            "trim_whitespace": trim_whitespace,
            "lowercase_headers": lowercase_headers,
            "remove_empty_rows": remove_empty_rows,
            "remove_duplicate_rows": remove_duplicate_rows,
            "normalize_column_names": normalize_column_names,
            "remove_empty_columns": remove_empty_columns,
        },
    }