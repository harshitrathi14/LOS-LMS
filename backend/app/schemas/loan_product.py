from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoanProductBase(BaseModel):
    code: str
    name: str
    currency: str = "INR"
    interest_rate_type: str = "fixed"
    base_rate: float
    schedule_type: str = "emi"
    repayment_frequency: str = "monthly"
    day_count_convention: str = "act/365"
    processing_fee_rate: float = 0
    penalty_rate: float = 0
    prepayment_penalty_rate: float = 0
    grace_days: int = 0
    min_tenure_months: int = 6
    max_tenure_months: int = 60


class LoanProductCreate(LoanProductBase):
    pass


class LoanProductRead(LoanProductBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
