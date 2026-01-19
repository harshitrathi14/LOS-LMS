from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RepaymentSchedule(Base):
    __tablename__ = "repayment_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id"), index=True
    )
    installment_number: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[Date] = mapped_column(Date)
    principal_due: Mapped[float] = mapped_column(Numeric(18, 2))
    interest_due: Mapped[float] = mapped_column(Numeric(18, 2))
    fees_due: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_due: Mapped[float] = mapped_column(Numeric(18, 2))
    principal_paid: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_paid: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fees_paid: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    loan_account = relationship("LoanAccount")
