from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoanApplicationBase(BaseModel):
    borrower_id: int
    product_id: int
    status: str = "submitted"
    channel: str | None = None
    requested_amount: float
    requested_tenure_months: int
    currency: str = "INR"
    credit_score: int | None = None
    approved_amount: float | None = None
    approved_rate: float | None = None
    approved_tenure_months: int | None = None
    decision_reason: str | None = None


class LoanApplicationCreate(LoanApplicationBase):
    pass


class LoanApplicationUpdate(BaseModel):
    status: str | None = None
    credit_score: int | None = None
    approved_amount: float | None = None
    approved_rate: float | None = None
    approved_tenure_months: int | None = None
    decision_reason: str | None = None
    decision_at: datetime | None = None


class LoanApplicationRead(LoanApplicationBase):
    id: int
    created_at: datetime | None = None
    decision_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
