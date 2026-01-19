from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PaymentBase(BaseModel):
    loan_account_id: int
    amount: float
    unallocated_amount: float | None = None
    currency: str = "INR"
    channel: str | None = None
    reference: str | None = None
    paid_at: datetime | None = None


class PaymentCreate(BaseModel):
    amount: float
    currency: str = "INR"
    channel: str | None = None
    reference: str | None = None
    paid_at: datetime | None = None


class PaymentRead(PaymentBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
