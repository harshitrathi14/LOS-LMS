from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LoanParticipation(Base):
    """
    Loan participation/co-lending arrangement.

    Supports various co-lending ratios:
    - 80:20 (Lender 80%, Originator 20%)
    - 90:10 (Lender 90%, Originator 10%)
    - 100:0 (Fully backed by lender - DA/Assignment)

    Tracks FLDG coverage, servicer arrangements, and write-off status.
    """
    __tablename__ = "loan_participations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id"), index=True
    )
    partner_id: Mapped[int] = mapped_column(ForeignKey("loan_partners.id"), index=True)

    # Participation type: co_lending, assignment, participation
    participation_type: Mapped[str] = mapped_column(String(30), default="co_lending")

    # Share percentages
    share_percent: Mapped[float] = mapped_column(Numeric(7, 4))  # Principal share
    interest_rate: Mapped[float | None] = mapped_column(Numeric(10, 4))  # Partner's yield rate
    fee_share_percent: Mapped[float | None] = mapped_column(Numeric(7, 4))

    # For fully backed (0:100) arrangements
    is_fully_backed: Mapped[bool] = mapped_column(Boolean, default=False)

    # FLDG linkage
    fldg_arrangement_id: Mapped[int | None] = mapped_column(
        ForeignKey("fldg_arrangements.id"),
        nullable=True
    )
    fldg_covered: Mapped[bool] = mapped_column(Boolean, default=False)
    fldg_coverage_percent: Mapped[float | None] = mapped_column(Numeric(8, 4))

    # Servicer arrangement linkage
    servicer_arrangement_id: Mapped[int | None] = mapped_column(
        ForeignKey("servicer_arrangements.id"),
        nullable=True
    )

    # Disbursement tracking
    principal_disbursed: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    principal_outstanding: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Collection tracking
    principal_collected: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_collected: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fees_collected: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Excess spread tracking
    excess_spread_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))  # Borrower rate - Lender yield
    cumulative_excess_spread: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Write-off flags
    is_written_off: Mapped[bool] = mapped_column(Boolean, default=False)
    write_off_date: Mapped[Date | None] = mapped_column(Date)
    write_off_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fldg_utilized: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    net_write_off: Mapped[float] = mapped_column(Numeric(18, 2), default=0)  # After FLDG

    # Recovery after write-off
    recovery_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fldg_recovered: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # ECL staging for partner's share
    ecl_stage: Mapped[int | None] = mapped_column(Integer)
    ecl_provision: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Status: active, closed, written_off
    status: Mapped[str] = mapped_column(String(20), default="active")

    # Dates
    effective_date: Mapped[Date | None] = mapped_column(Date)
    termination_date: Mapped[Date | None] = mapped_column(Date)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    loan_account = relationship("LoanAccount")
    partner = relationship("LoanPartner")
    fldg_arrangement = relationship("FLDGArrangement")
    servicer_arrangement = relationship("ServicerArrangement")
