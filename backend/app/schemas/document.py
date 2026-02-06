from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    borrower_id: int | None = None
    application_id: int | None = None
    loan_account_id: int | None = None
    collateral_id: int | None = None
    document_type: str
    file_name: str
    storage_path: str
    status: str = "uploaded"
    media_type: str = "document"
    section: str | None = None
    file_size_bytes: int | None = None
    mime_type: str | None = None
    thumbnail_path: str | None = None
    capture_latitude: float | None = None
    capture_longitude: float | None = None
    captured_at: datetime | None = None
    captured_by: str | None = None
    description: str | None = None


class DocumentCreate(DocumentBase):
    pass


class DocumentRead(DocumentBase):
    id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
