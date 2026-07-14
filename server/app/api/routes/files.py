from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File as FastAPIFile, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse as FastAPIFileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.models.file import File
from app.schemas.file import CsvPreviewResponse, FileResponse
from app.services.file_service import (
    get_file_by_id,
    list_files,
    preview_csv_file,
    save_uploaded_file,
)
router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: AsyncSession = Depends(get_db_session),
) -> File:
    try:
        return await save_uploaded_file(db, file)
    except ValueError as exc:
        # Ensure invalid uploads return a bad request response
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[FileResponse])
async def list_file_metadata(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    content_type: str | None = None,
    filename: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[File]:
    return await list_files(
        db=db,
        limit=limit,
        offset=offset,
        content_type=content_type,
        filename=filename,
    )


@router.get("/{file_id}/preview", response_model=CsvPreviewResponse)
async def preview_file(
    file_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    try:
        return await preview_csv_file(
            db=db,
            file_id=file_id,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/{file_id}", response_model=FileResponse)
async def get_file_metadata(
    file_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> File:
    file_row = await get_file_by_id(db, file_id)

    if file_row is None:
        raise HTTPException(status_code=404, detail="File not found")

    return file_row


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> FastAPIFileResponse:
    file_row = await get_file_by_id(db, file_id)

    if file_row is None:
        raise HTTPException(status_code=404, detail="File not found")

    storage_path = Path(file_row.storage_path)

    if not storage_path.exists() or not storage_path.is_file():
        raise HTTPException(status_code=404, detail="File missing from storage")

    return FastAPIFileResponse(
        path=storage_path,
        filename=file_row.original_filename,
        media_type=file_row.content_type or "application/octet-stream",
    )

