from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LoanAccount(Base):
    """
    Loan account representing an active/disbursed loan.

    Tracks principal, interest, fees, and repayment status.
    """
    __tablename__ = "loan_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("loan_applications.id"), index=True)
    account_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    principal_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    principal_outstanding: Mapped[float] = mapped_column(Numeric(18, 2))
    interest_outstanding: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fees_outstanding: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_rate: Mapped[float] = mapped_column(Numeric(10, 4))
    interest_rate_type: Mapped[str] = mapped_column(String(20), default="fixed")
    schedule_type: Mapped[str] = mapped_column(String(20), default="emi")
    repayment_frequency: Mapped[str] = mapped_column(String(20), default="monthly")
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    tenure_months: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[Date] = mapped_column(Date)
    disbursed_at: Mapped[DateTime | None] = mapped_column(DateTime)
    next_due_date: Mapped[Date | None] = mapped_column(Date)
    next_due_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    dpd: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Phase 1: Day-count and calendar support
    day_count_convention: Mapped[str] = mapped_column(String(20), default="act/365")
    holiday_calendar_id: Mapped[int | None] = mapped_column(
        ForeignKey("holiday_calendars.id"),
        nullable=True
    )
    business_day_adjustment: Mapped[str] = mapped_column(
        String(30), default="modified_following"
    )

    # Phase 2: Floating rate support
    benchmark_rate_id: Mapped[int | None] = mapped_column(
        ForeignKey("benchmark_rates.id"),
        nullable=True
    )
    spread: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    rate_reset_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    next_rate_reset_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    floor_rate: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    cap_rate: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Phase 6: Loan closure and lifecycle
    closure_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    closure_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # normal, foreclosure, write_off, settlement
    settlement_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    maturity_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    last_restructure_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    restructure_count: Mapped[int] = mapped_column(Integer, default=0)

    # Write-off flags (critical for all reporting)
    is_written_off: Mapped[bool] = mapped_column(Boolean, default=False)
    write_off_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    write_off_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    write_off_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # NPA flags
    is_npa: Mapped[bool] = mapped_column(Boolean, default=False)
    npa_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    npa_category: Mapped[str | None] = mapped_column(String(30), nullable=True)  # substandard, doubtful, loss

    # Restructure flags
    is_restructured: Mapped[bool] = mapped_column(Boolean, default=False)

    # Fraud flag
    is_fraud: Mapped[bool] = mapped_column(Boolean, default=False)
    fraud_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    # ECL staging (IFRS 9 / Ind AS 109)
    ecl_stage: Mapped[int] = mapped_column(Integer, default=1)  # 1, 2, or 3
    ecl_stage_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    ecl_provision: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    ecl_provision_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    # SICR (Significant Increase in Credit Risk) flag
    sicr_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    sicr_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    # Recovery tracking post write-off
    recovered_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    recovery_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Co-lending / Partnership flags
    is_co_lent: Mapped[bool] = mapped_column(Boolean, default=False)
    co_lending_ratio: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g., "80:20"
    has_fldg_coverage: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    application = relationship("LoanApplication")
    holiday_calendar = relationship("HolidayCalendar")
    benchmark_rate = relationship("BenchmarkRate")
    write_off = relationship("WriteOff", back_populates="loan_account", uselist=False)
    selldown_transactions = relationship("SelldownTransaction", back_populates="loan_account")
