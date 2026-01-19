"""
Interest Accrual model for daily interest tracking.

Provides an audit trail of daily interest accruals for each loan account.
"""

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InterestAccrual(Base):
    """
    Daily interest accrual record.

    Tracks the interest accrued each day for a loan account.
    Used for:
    - Daily interest tracking on floating rate loans
    - Accurate interest calculation between rate resets
    - Audit trail for interest charges
    - Month-end accrual reporting
    """
    __tablename__ = "interest_accruals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id", ondelete="CASCADE"),
        index=True
    )
    accrual_date: Mapped[Date] = mapped_column(Date, index=True)

    # Balance and rate at time of accrual
    opening_balance: Mapped[float] = mapped_column(Numeric(18, 2))
    interest_rate: Mapped[float] = mapped_column(Numeric(10, 6))  # Effective rate applied
    benchmark_rate: Mapped[float | None] = mapped_column(Numeric(10, 6))  # Benchmark component
    spread: Mapped[float | None] = mapped_column(Numeric(10, 4))  # Spread component

    # Calculated amounts
    accrued_amount: Mapped[float] = mapped_column(Numeric(18, 6))  # Daily accrual (high precision)
    cumulative_accrued: Mapped[float] = mapped_column(Numeric(18, 2))  # Cumulative since last payment

    # Day count info
    day_count_convention: Mapped[str] = mapped_column(String(20), default="act/365")
    days_in_year: Mapped[int] = mapped_column(Integer, default=365)

    # Processing metadata
    status: Mapped[str] = mapped_column(String(20), default="accrued")  # accrued, posted, reversed
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    loan_account = relationship("LoanAccount")

    # Ensure unique accrual per date per account
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
