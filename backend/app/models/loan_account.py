from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
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

    # Relationships
    application = relationship("LoanApplication")
    holiday_calendar = relationship("HolidayCalendar")
    benchmark_rate = relationship("BenchmarkRate")
    write_off = relationship("WriteOff", back_populates="loan_account", uselist=False)
