from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class RepaymentScheduleBase(BaseModel):
    loan_account_id: int
    installment_number: int
    due_date: date
    principal_due: float
    interest_due: float
    fees_due: float = 0
    total_due: float
    principal_paid: float = 0
    interest_paid: float = 0
    fees_paid: float = 0
    status: str = "pending"


class RepaymentScheduleRead(RepaymentScheduleBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
