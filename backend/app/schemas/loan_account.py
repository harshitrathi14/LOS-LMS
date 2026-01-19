from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class LoanAccountBase(BaseModel):
    application_id: int
    account_number: str
    principal_amount: float
    principal_outstanding: float | None = None
    interest_outstanding: float | None = None
    fees_outstanding: float | None = None
    interest_rate: float
    interest_rate_type: str = "fixed"
    schedule_type: str = "emi"
    repayment_frequency: str = "monthly"
    currency: str | None = None
    tenure_months: int
    start_date: date
    disbursed_at: datetime | None = None
    next_due_date: date | None = None
    next_due_amount: float | None = None
    dpd: int | None = None
    status: str = "active"
    # Phase 1: Day-count and calendar support
    day_count_convention: str = "act/365"
    holiday_calendar_id: int | None = None
    business_day_adjustment: str = "modified_following"
    # Phase 2: Floating rate support
    benchmark_rate_id: int | None = None
    spread: float | None = None
    rate_reset_frequency: str | None = None
    next_rate_reset_date: date | None = None
    floor_rate: float | None = None
    cap_rate: float | None = None


class LoanAccountCreate(BaseModel):
    application_id: int
    account_number: str
    principal_amount: float
    interest_rate: float
    interest_rate_type: str | None = None
    schedule_type: str | None = None
    repayment_frequency: str | None = None
    currency: str = "INR"
    tenure_months: int
    start_date: date
    disbursed_at: datetime | None = None
    # Phase 1: Day-count and calendar support
    day_count_convention: str = "act/365"
    holiday_calendar_id: int | None = None
    business_day_adjustment: str = "modified_following"
    # Phase 2: Floating rate support
    benchmark_rate_id: int | None = None
    spread: float | None = None
    rate_reset_frequency: str | None = None
    next_rate_reset_date: date | None = None
    floor_rate: float | None = None
    cap_rate: float | None = None


class LoanAccountRead(LoanAccountBase):
    id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
