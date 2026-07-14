import csv
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File


UPLOAD_DIR = Path("storage/uploads")
OUTPUT_DIR = Path("storage/outputs")

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024

ALLOWED_CSV_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "text/plain",
    "application/octet-stream",
}

def validate_csv_upload_file(upload_file: UploadFile) -> None:
    original_filename = upload_file.filename or ""

    if not original_filename.lower().endswith(".csv"):
        raise ValueError("Only .csv files are supported")

    if upload_file.content_type not in ALLOWED_CSV_CONTENT_TYPES:
        raise ValueError("Uploaded file content type is not supported for CSV")

async def save_uploaded_file(
    db: AsyncSession,
    upload_file: UploadFile,
) -> File:
    
    validate_csv_upload_file(upload_file)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    original_filename = upload_file.filename or "uploaded_file"
    file_extension = Path(original_filename).suffix.lower()

    stored_filename = f"{uuid.uuid4().hex}{file_extension}"
    storage_path = UPLOAD_DIR / stored_filename

    size_bytes = 0

    try:
        with storage_path.open("wb") as buffer:
            while True:
                chunk = await upload_file.read(1024 * 1024)
                if not chunk:
                    break

                size_bytes += len(chunk)

                if size_bytes > MAX_UPLOAD_SIZE_BYTES:
                    raise ValueError(
                        f"Uploaded file exceeds {MAX_UPLOAD_SIZE_BYTES} bytes"
                    )

                buffer.write(chunk)

        if size_bytes == 0:
            raise ValueError("Uploaded file is empty")
    except Exception:
        if storage_path.exists():
            storage_path.unlink()

        raise

    file_row = File(
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=upload_file.content_type,
        size_bytes=size_bytes,
        storage_path=str(storage_path),
    )

    db.add(file_row)
    await db.commit()
    await db.refresh(file_row)

    return file_row



async def get_file_by_id(
    db: AsyncSession,
    file_id: int,
) -> File | None:
    result = await db.execute(
        select(File).where(File.id == file_id)
    )

    return result.scalar_one_or_none()


async def create_file_record_for_existing_path(
    db: AsyncSession,
    original_filename: str,
    stored_filename: str,
    content_type: str | None,
    storage_path: Path,
) -> File:
    size_bytes = storage_path.stat().st_size

    file_row = File(
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_path=str(storage_path),
    )

    db.add(file_row)
    await db.flush()
    await db.refresh(file_row)

    return file_row



async def list_files(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    content_type: str | None = None,
    filename: str | None = None,
) -> list[File]:
    stmt = select(File).order_by(File.created_at.desc())

    if content_type is not None:
        stmt = stmt.where(File.content_type == content_type)

    if filename is not None:
        stmt = stmt.where(File.original_filename.ilike(f"%{filename}%"))

    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)

    return list(result.scalars().all())

async def preview_csv_file(
    db: AsyncSession,
    file_id: int,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    file_row = await get_file_by_id(db, file_id)

    if file_row is None:
        raise ValueError("File not found")

    storage_path = Path(file_row.storage_path)

    if not storage_path.exists() or not storage_path.is_file():
        raise ValueError("File missing from storage")

    if storage_path.suffix.lower() != ".csv":
        raise ValueError("Preview only supports .csv files")

    rows: list[dict[str, Any]] = []

    with storage_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row")

        columns = list(reader.fieldnames)

        for index, row in enumerate(reader):
            if index >= limit:
                break

            rows.append(dict(row))

    return {
        "file_id": file_row.id,
        "original_filename": file_row.original_filename,
        "columns": columns,
        "rows": rows,
        "row_count_returned": len(rows),
    }