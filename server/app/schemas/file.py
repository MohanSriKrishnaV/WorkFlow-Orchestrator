from datetime import datetime

from pydantic import BaseModel, ConfigDict

from typing import Any


class FileResponse(BaseModel):
    id: int
    original_filename: str
    stored_filename: str
    content_type: str | None = None
    size_bytes: int
    storage_path: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



class CsvPreviewResponse(BaseModel):
    file_id: int
    original_filename: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count_returned: int

