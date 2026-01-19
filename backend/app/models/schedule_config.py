"""
Schedule Configuration model for advanced repayment schedules.

Supports:
- Step-up EMI (increasing payments over time)
- Step-down EMI (decreasing payments over time)
- Moratorium periods (principal and/or interest)
- Balloon payments
- Custom schedules
"""

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ScheduleConfiguration(Base):
    """
    Advanced schedule configuration for a loan account.

    One loan account can have one schedule configuration defining
    its special repayment terms.
    """
    __tablename__ = "schedule_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id", ondelete="CASCADE"),
        unique=True,  # One config per account
        index=True
    )

    # Schedule type: standard, step_up, step_down, balloon, custom
    schedule_type: Mapped[str] = mapped_column(String(30), default="standard")

    # Moratorium configuration
    moratorium_months: Mapped[int] = mapped_column(Integer, default=0)
    # Moratorium type: full (no principal or interest), principal_only, interest_only
    moratorium_type: Mapped[str | None] = mapped_column(String(30))
    # How to handle moratorium interest: capitalize, accrue, waive
    moratorium_interest_treatment: Mapped[str] = mapped_column(String(30), default="capitalize")

    # Step-up/Step-down configuration
    step_percent: Mapped[float | None] = mapped_column(Numeric(10, 4))  # % increase/decrease
    step_frequency_months: Mapped[int | None] = mapped_column(Integer)  # Every N months
    step_count: Mapped[int | None] = mapped_column(Integer)  # Number of steps (null = continuous)

    # Balloon payment configuration
    balloon_percent: Mapped[float | None] = mapped_column(Numeric(10, 4))  # % of principal as balloon
    balloon_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))  # Fixed balloon amount

    # For custom schedules: JSON array of custom payment amounts
    custom_schedule_json: Mapped[str | None] = mapped_column(Text)

    # Grace period before first EMI
    initial_grace_months: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    loan_account = relationship("LoanAccount", backref="schedule_config")
