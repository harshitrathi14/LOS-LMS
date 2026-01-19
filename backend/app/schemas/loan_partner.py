from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoanPartnerBase(BaseModel):
    name: str
    partner_type: str = "lender"
    external_code: str | None = None


class LoanPartnerCreate(LoanPartnerBase):
    pass


class LoanPartnerRead(LoanPartnerBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
