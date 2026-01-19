"""
Write-off model.

WriteOff: Tracks loan write-offs and subsequent recoveries
"""

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WriteOff(Base):
    """
    Loan write-off record.

    Tracks write-off of bad debts and any subsequent recoveries.
    """
    __tablename__ = "write_offs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id", ondelete="CASCADE"),
        index=True,
        unique=True  # One write-off per loan
    )

    # Write-off details
    write_off_date: Mapped[Date] = mapped_column(Date, index=True)

    # Amounts written off
    principal_written_off: Mapped[float] = mapped_column(Numeric(18, 2))
    interest_written_off: Mapped[float] = mapped_column(Numeric(18, 2))
    fees_written_off: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    penalties_written_off: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_written_off: Mapped[float] = mapped_column(Numeric(18, 2))

    # DPD at write-off
    dpd_at_write_off: Mapped[int] = mapped_column(Integer)

    # Write-off type: full, partial, technical
    write_off_type: Mapped[str] = mapped_column(String(20), default="full")

    # Reason and approval
    reason: Mapped[str] = mapped_column(Text)
    approved_by: Mapped[str] = mapped_column(String(100))
    approval_date: Mapped[Date] = mapped_column(Date)

    # Recovery tracking
    recovery_status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, in_progress, partial, complete, closed
    recovered_principal: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    recovered_interest: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    recovered_fees: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_recovered: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    last_recovery_date: Mapped[Date | None] = mapped_column(Date)

    # Collection agency assignment
    assigned_to_agency: Mapped[str | None] = mapped_column(String(100))
    agency_fee_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    loan_account = relationship("LoanAccount", back_populates="write_off")
    recoveries: Mapped[list["WriteOffRecovery"]] = relationship(
        "WriteOffRecovery",
        back_populates="write_off",
        cascade="all, delete-orphan"
    )


class WriteOffRecovery(Base):
    """
    Recovery payment against a written-off loan.
    """
    __tablename__ = "write_off_recoveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    write_off_id: Mapped[int] = mapped_column(
        ForeignKey("write_offs.id", ondelete="CASCADE"),
        index=True
    )
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id"),
        index=True
    )

    # Recovery details
    recovery_date: Mapped[Date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))

    # Allocation
    principal_recovered: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_recovered: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fees_recovered: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Source of recovery
    recovery_source: Mapped[str] = mapped_column(String(30))  # borrower, guarantor, collateral, agency

    # Agency commission if applicable
    agency_commission: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    net_recovery: Mapped[float] = mapped_column(Numeric(18, 2))

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    write_off: Mapped["WriteOff"] = relationship(
        "WriteOff",
        back_populates="recoveries"
    )
    payment = relationship("Payment")
