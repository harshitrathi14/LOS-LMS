from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("repayment_schedules.id"), index=True
    )
    principal_allocated: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_allocated: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fees_allocated: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    payment = relationship("Payment")
    schedule = relationship("RepaymentSchedule")
