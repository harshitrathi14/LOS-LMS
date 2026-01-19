from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class BorrowerBase(BaseModel):
    external_id: str | None = None
    first_name: str
    last_name: str
    date_of_birth: date | None = None
    email: str | None = None
    phone: str | None = None
    kyc_status: str = "pending"


class BorrowerCreate(BorrowerBase):
    pass


class BorrowerRead(BorrowerBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
