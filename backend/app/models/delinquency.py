"""
Delinquency tracking models.

DelinquencySnapshot: Daily/periodic snapshots of loan delinquency status
"""

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DelinquencySnapshot(Base):
    """
    Point-in-time snapshot of loan delinquency status.

    Created daily or on-demand for portfolio monitoring.
    """
    __tablename__ = "delinquency_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id", ondelete="CASCADE"),
        index=True
    )
    snapshot_date: Mapped[Date] = mapped_column(Date, index=True)

    # Delinquency metrics
    dpd: Mapped[int] = mapped_column(Integer)  # Days past due
    bucket: Mapped[str] = mapped_column(String(20), index=True)  # current, 1-30, 31-60, etc.

    # Overdue amounts
    overdue_principal: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    overdue_interest: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    overdue_fees: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_overdue: Mapped[float] = mapped_column(Numeric(18, 2))

    # Outstanding balance at snapshot
    principal_outstanding: Mapped[float] = mapped_column(Numeric(18, 2))

    # Number of missed installments
    missed_installments: Mapped[int] = mapped_column(Integer, default=0)

    # Oldest unpaid due date
    oldest_due_date: Mapped[Date | None] = mapped_column(Date)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    loan_account = relationship("LoanAccount")

    # Unique constraint on loan + date
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
