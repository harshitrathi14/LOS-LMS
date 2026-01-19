"""
Prepayment model.

Prepayment: Tracks prepayment transactions and their impact
"""

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Prepayment(Base):
    """
    Prepayment transaction record.

    Tracks partial or full prepayments and their effect on the loan.
    """
    __tablename__ = "prepayments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id", ondelete="CASCADE"),
        index=True
    )
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id"),
        index=True
    )

    # Prepayment details
    prepayment_date: Mapped[Date] = mapped_column(Date, index=True)
    prepayment_amount: Mapped[float] = mapped_column(Numeric(18, 2))

    # Penalty
    penalty_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))
    penalty_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    penalty_waived: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    net_penalty: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Applied amounts
    principal_reduced: Mapped[float] = mapped_column(Numeric(18, 2))
    interest_paid: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Action type: reduce_emi, reduce_tenure, foreclosure
    action_type: Mapped[str] = mapped_column(String(30), index=True)

    # Before prepayment
    old_outstanding: Mapped[float] = mapped_column(Numeric(18, 2))
    old_emi: Mapped[float | None] = mapped_column(Numeric(18, 2))
    old_remaining_tenure: Mapped[int | None] = mapped_column(Integer)

    # After prepayment
    new_outstanding: Mapped[float] = mapped_column(Numeric(18, 2))
    new_emi: Mapped[float | None] = mapped_column(Numeric(18, 2))
    new_remaining_tenure: Mapped[int | None] = mapped_column(Integer)

    # For foreclosure
    is_foreclosure: Mapped[bool] = mapped_column(default=False)
    foreclosure_charges: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Status: pending, completed, reversed
    status: Mapped[str] = mapped_column(String(20), default="completed", index=True)

    notes: Mapped[str | None] = mapped_column(Text)
    processed_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    loan_account = relationship("LoanAccount")
    payment = relationship("Payment")
