from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoanParticipationBase(BaseModel):
    loan_account_id: int
    partner_id: int
    share_percent: float
    interest_rate: float | None = None
    fee_share_percent: float | None = None
    status: str = "active"


class LoanParticipationCreate(LoanParticipationBase):
    pass


class LoanParticipationRead(LoanParticipationBase):
    id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
