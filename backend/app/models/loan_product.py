from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoanProduct(Base):
    __tablename__ = "loan_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    interest_rate_type: Mapped[str] = mapped_column(String(20), default="fixed")
    base_rate: Mapped[float] = mapped_column(Numeric(10, 4))
    schedule_type: Mapped[str] = mapped_column(String(20), default="emi")
    repayment_frequency: Mapped[str] = mapped_column(String(20), default="monthly")
    day_count_convention: Mapped[str] = mapped_column(String(20), default="act/365")
    processing_fee_rate: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    penalty_rate: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    prepayment_penalty_rate: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    grace_days: Mapped[int] = mapped_column(Integer, default=0)
    min_tenure_months: Mapped[int] = mapped_column(Integer, default=6)
    max_tenure_months: Mapped[int] = mapped_column(Integer, default=60)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())
