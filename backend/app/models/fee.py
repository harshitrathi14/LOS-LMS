"""
Fee models for loan fee management.

FeeType: Defines types of fees (processing, late fee, prepayment penalty, etc.)
ProductFee: Links fee types to loan products with configuration
FeeCharge: Actual fee charges applied to loan accounts
"""

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FeeType(Base):
    """
    Definition of a fee type.

    Examples: processing_fee, late_fee, prepayment_penalty, foreclosure_fee,
              documentation_fee, stamp_duty, insurance_premium
    """
    __tablename__ = "fee_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    # Calculation type: flat, percentage, formula
    calculation_type: Mapped[str] = mapped_column(String(20), default="flat")

    # What the fee applies to: disbursement, installment, prepayment, overdue
    applies_to: Mapped[str] = mapped_column(String(30), default="disbursement")

    # When the fee is charged: upfront, on_occurrence, monthly, annually
    charge_timing: Mapped[str] = mapped_column(String(30), default="upfront")

    # Tax treatment
    taxable: Mapped[bool] = mapped_column(Boolean, default=True)
    tax_rate: Mapped[float] = mapped_column(Numeric(10, 4), default=0)

    # Priority in payment waterfall (lower = paid first)
    waterfall_priority: Mapped[int] = mapped_column(Integer, default=100)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    product_fees: Mapped[list["ProductFee"]] = relationship(
        "ProductFee", back_populates="fee_type"
    )


class ProductFee(Base):
    """
    Fee configuration for a loan product.

    Links a fee type to a product with specific amounts/rates.
    """
    __tablename__ = "product_fees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("loan_products.id", ondelete="CASCADE"),
        index=True
    )
    fee_type_id: Mapped[int] = mapped_column(
        ForeignKey("fee_types.id", ondelete="CASCADE"),
        index=True
    )

    # Fee amount configuration
    flat_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    percentage_value: Mapped[float | None] = mapped_column(Numeric(10, 4))
    min_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    max_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))

    # For late fees: grace days before charging
    grace_days: Mapped[int] = mapped_column(Integer, default=0)

    # Is this fee mandatory or optional?
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)

    # Can this fee be waived?
    is_waivable: Mapped[bool] = mapped_column(Boolean, default=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    fee_type: Mapped["FeeType"] = relationship("FeeType", back_populates="product_fees")
    product = relationship("LoanProduct")


class FeeCharge(Base):
    """
    Actual fee charge applied to a loan account.

    Tracks the lifecycle of a fee from charge to payment/waiver.
    """
    __tablename__ = "fee_charges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id", ondelete="CASCADE"),
        index=True
    )
    fee_type_id: Mapped[int] = mapped_column(
        ForeignKey("fee_types.id"),
        index=True
    )
    schedule_id: Mapped[int | None] = mapped_column(
        ForeignKey("repayment_schedules.id"),
        nullable=True
    )

    # Charge details
    charge_date: Mapped[Date] = mapped_column(Date, index=True)
    due_date: Mapped[Date | None] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    tax_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2))  # amount + tax

    # Payment tracking
    paid_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    waived_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    outstanding_amount: Mapped[float] = mapped_column(Numeric(18, 2))

    # Status: pending, partial, paid, waived
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    # Reference information
    reference_type: Mapped[str | None] = mapped_column(String(30))  # prepayment, late_payment, etc.
    reference_id: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    # Waiver details
    waived_by: Mapped[str | None] = mapped_column(String(100))
    waived_at: Mapped[DateTime | None] = mapped_column(DateTime)
    waiver_reason: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    loan_account = relationship("LoanAccount")
    fee_type = relationship("FeeType")
    schedule = relationship("RepaymentSchedule")
