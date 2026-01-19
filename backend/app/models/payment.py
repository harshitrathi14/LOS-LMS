from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(ForeignKey("loan_accounts.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    unallocated_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    channel: Mapped[str | None] = mapped_column(String(40))
    reference: Mapped[str | None] = mapped_column(String(100))
    paid_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    loan_account = relationship("LoanAccount")
