"""
Loan restructure model.

LoanRestructure: Tracks loan restructuring events
"""

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LoanRestructure(Base):
    """
    Loan restructuring record.

    Tracks changes to loan terms such as:
    - Rate reduction
    - Tenure extension
    - Principal haircut
    - EMI rescheduling
    """
    __tablename__ = "loan_restructures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id", ondelete="CASCADE"),
        index=True
    )

    # Restructure identification
    restructure_date: Mapped[Date] = mapped_column(Date, index=True)
    effective_date: Mapped[Date] = mapped_column(Date)

    # Restructure type: rate_reduction, tenure_extension, principal_haircut,
    # emi_rescheduling, combination
    restructure_type: Mapped[str] = mapped_column(String(30), index=True)

    # Original terms
    original_principal: Mapped[float] = mapped_column(Numeric(18, 2))
    original_rate: Mapped[float] = mapped_column(Numeric(8, 4))
    original_tenure: Mapped[int] = mapped_column(Integer)  # months
    original_emi: Mapped[float | None] = mapped_column(Numeric(18, 2))

    # New terms
    new_principal: Mapped[float] = mapped_column(Numeric(18, 2))
    new_rate: Mapped[float] = mapped_column(Numeric(8, 4))
    new_tenure: Mapped[int] = mapped_column(Integer)  # months
    new_emi: Mapped[float | None] = mapped_column(Numeric(18, 2))

    # Principal changes
    principal_waived: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_waived: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fees_waived: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Approval
    reason: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[str | None] = mapped_column(String(100))
    approved_by: Mapped[str | None] = mapped_column(String(100))
    approved_date: Mapped[Date | None] = mapped_column(Date)

    # Status: pending, approved, rejected, cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    loan_account = relationship("LoanAccount")
