"""
FLDG (First Loss Default Guarantee) models.

FLDGArrangement: FLDG arrangement between originator and lender
FLDGUtilization: Utilization of FLDG when defaults occur
FLDGRecovery: Recovery of FLDG amounts post write-off collection
"""

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FLDGArrangement(Base):
    """
    First Loss Default Guarantee arrangement.

    FLDG Types:
    - first_loss: First Loss Default Guarantee (absorbs losses first)
    - second_loss: Second Loss Default Guarantee (absorbs after first loss is exhausted)

    The originator provides a guarantee (cash/bank guarantee) that absorbs
    default losses up to a specified percentage of the portfolio.
    """
    __tablename__ = "fldg_arrangements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Arrangement identification
    arrangement_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    # Parties
    originator_id: Mapped[int] = mapped_column(
        ForeignKey("loan_partners.id"),
        index=True
    )  # Originator providing FLDG
    lender_id: Mapped[int] = mapped_column(
        ForeignKey("loan_partners.id"),
        index=True
    )  # Lender receiving protection

    # FLDG type: first_loss, second_loss
    fldg_type: Mapped[str] = mapped_column(String(20), index=True)

    # FLDG limits - can be percentage-based or absolute
    fldg_percent: Mapped[float | None] = mapped_column(Numeric(8, 4))  # % of portfolio
    fldg_absolute_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))

    # Effective limit (max of % calculation or absolute)
    effective_fldg_limit: Mapped[float] = mapped_column(Numeric(18, 2))

    # For second loss - specify first loss threshold
    first_loss_threshold: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Coverage scope
    covers_principal: Mapped[bool] = mapped_column(Boolean, default=True)
    covers_interest: Mapped[bool] = mapped_column(Boolean, default=True)
    covers_fees: Mapped[bool] = mapped_column(Boolean, default=False)

    # Guarantee form: cash_deposit, bank_guarantee, corporate_guarantee
    guarantee_form: Mapped[str] = mapped_column(String(30), default="cash_deposit")

    # For bank guarantee
    bank_guarantee_number: Mapped[str | None] = mapped_column(String(100))
    bank_guarantee_expiry: Mapped[Date | None] = mapped_column(Date)
    guarantor_bank_name: Mapped[str | None] = mapped_column(String(200))

    # Cash deposit details
    cash_deposit_account: Mapped[str | None] = mapped_column(String(50))
    cash_deposit_bank: Mapped[str | None] = mapped_column(String(200))

    # Current status
    current_fldg_balance: Mapped[float] = mapped_column(Numeric(18, 2))  # Available FLDG
    total_utilized: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_recovered: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Utilization caps (per period)
    max_utilization_per_month: Mapped[float | None] = mapped_column(Numeric(18, 2))
    max_utilization_per_quarter: Mapped[float | None] = mapped_column(Numeric(18, 2))

    # Dates
    effective_date: Mapped[Date] = mapped_column(Date)
    expiry_date: Mapped[Date | None] = mapped_column(Date)

    # Portfolio reference (can be linked to pool or all loans with partner)
    pool_id: Mapped[int | None] = mapped_column(
        ForeignKey("securitization_pools.id"),
        nullable=True
    )  # If linked to specific pool

    # Trigger conditions for utilization
    trigger_dpd: Mapped[int] = mapped_column(Integer, default=90)  # DPD to trigger FLDG
    trigger_on_write_off: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_on_npa: Mapped[bool] = mapped_column(Boolean, default=False)

    # Top-up requirements
    requires_top_up: Mapped[bool] = mapped_column(Boolean, default=True)
    top_up_threshold_percent: Mapped[float] = mapped_column(Numeric(8, 4), default=50)

    # Status: active, expired, exhausted, terminated
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    originator = relationship("LoanPartner", foreign_keys=[originator_id])
    lender = relationship("LoanPartner", foreign_keys=[lender_id])
    pool = relationship("SecuritizationPool")
    utilizations: Mapped[list["FLDGUtilization"]] = relationship(
        "FLDGUtilization",
        back_populates="arrangement",
        cascade="all, delete-orphan"
    )


class FLDGUtilization(Base):
    """
    FLDG utilization when a loan defaults.

    Records each instance of FLDG being invoked for a defaulted loan.
    """
    __tablename__ = "fldg_utilizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    arrangement_id: Mapped[int] = mapped_column(
        ForeignKey("fldg_arrangements.id", ondelete="CASCADE"),
        index=True
    )
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id"),
        index=True
    )

    # Utilization details
    utilization_date: Mapped[Date] = mapped_column(Date, index=True)
    trigger_reason: Mapped[str] = mapped_column(String(30))  # npa, write_off, dpd_threshold

    # Amounts claimed
    principal_claimed: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_claimed: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fees_claimed: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_claimed: Mapped[float] = mapped_column(Numeric(18, 2))

    # Amounts approved (may be less than claimed)
    principal_approved: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_approved: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fees_approved: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_approved: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Adjustment reason if approved != claimed
    adjustment_reason: Mapped[str | None] = mapped_column(Text)

    # Reference to write-off if applicable
    write_off_id: Mapped[int | None] = mapped_column(
        ForeignKey("write_offs.id"),
        nullable=True
    )

    # DPD at time of utilization
    dpd_at_utilization: Mapped[int] = mapped_column(Integer)

    # Balance snapshot
    fldg_balance_before: Mapped[float] = mapped_column(Numeric(18, 2))
    fldg_balance_after: Mapped[float] = mapped_column(Numeric(18, 2))

    # Status: pending, approved, rejected, settled, recovered
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    # Approval details
    approved_by: Mapped[str | None] = mapped_column(String(100))
    approved_at: Mapped[DateTime | None] = mapped_column(DateTime)

    # Settlement details
    settlement_date: Mapped[Date | None] = mapped_column(Date)
    settlement_reference: Mapped[str | None] = mapped_column(String(100))

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    arrangement: Mapped["FLDGArrangement"] = relationship(
        "FLDGArrangement",
        back_populates="utilizations"
    )
    loan_account = relationship("LoanAccount")
    write_off = relationship("WriteOff")
    recoveries: Mapped[list["FLDGRecovery"]] = relationship(
        "FLDGRecovery",
        back_populates="utilization",
        cascade="all, delete-orphan"
    )


class FLDGRecovery(Base):
    """
    Recovery of FLDG amounts after collection from defaulted loan.

    When amounts are recovered from a written-off loan, the FLDG pool
    needs to be replenished (subject to arrangement terms).
    """
    __tablename__ = "fldg_recoveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    utilization_id: Mapped[int] = mapped_column(
        ForeignKey("fldg_utilizations.id", ondelete="CASCADE"),
        index=True
    )

    # Recovery details
    recovery_date: Mapped[Date] = mapped_column(Date, index=True)

    # Amounts recovered
    principal_recovered: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_recovered: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_recovered: Mapped[float] = mapped_column(Numeric(18, 2))

    # Amount returned to FLDG pool
    amount_returned_to_fldg: Mapped[float] = mapped_column(Numeric(18, 2))

    # Recovery source: borrower, guarantor, collateral, legal
    recovery_source: Mapped[str] = mapped_column(String(30))

    # Reference to write-off recovery if applicable
    write_off_recovery_id: Mapped[int | None] = mapped_column(
        ForeignKey("write_off_recoveries.id"),
        nullable=True
    )

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    utilization: Mapped["FLDGUtilization"] = relationship(
        "FLDGUtilization",
        back_populates="recoveries"
    )
    write_off_recovery = relationship("WriteOffRecovery")
