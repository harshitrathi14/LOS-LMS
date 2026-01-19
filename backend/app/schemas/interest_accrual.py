"""
Pydantic schemas for Interest Accrual API.
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class InterestAccrualRead(BaseModel):
    """Schema for reading an interest accrual record."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_account_id: int
    accrual_date: date
    opening_balance: float
    interest_rate: float
    benchmark_rate: float | None = None
    spread: float | None = None
    accrued_amount: float
    cumulative_accrued: float
    day_count_convention: str
    days_in_year: int
    status: str
    created_at: datetime


class AccrualSummary(BaseModel):
    """Summary of accruals for a period."""
    period_start: date
    period_end: date
    total_accrued: float
    average_rate: float
    days_count: int
    opening_balance: float | None = None
    closing_balance: float | None = None


class DailyAccrualBatchRequest(BaseModel):
    """Request for running daily accrual batch."""
    as_of_date: date


class DailyAccrualBatchResponse(BaseModel):
    """Response from daily accrual batch."""
    as_of_date: date
    total_accounts: int
    processed: int
    skipped: int
    errors: list[dict] = []


class AccrualDateRangeRequest(BaseModel):
    """Request for running accruals over a date range."""
    loan_account_id: int
    start_date: date
    end_date: date


class CumulativeAccrualResponse(BaseModel):
    """Response for cumulative accrual query."""
    loan_account_id: int
    as_of_date: date
    cumulative_accrued: float
