from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    borrower_id: int | None = None
    application_id: int | None = None
    loan_account_id: int | None = None
    document_type: str
    file_name: str
    storage_path: str
    status: str = "uploaded"


class DocumentCreate(DocumentBase):
    pass


class DocumentRead(DocumentBase):
    id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
