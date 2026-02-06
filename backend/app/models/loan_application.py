from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    borrower_id: Mapped[int] = mapped_column(ForeignKey("borrowers.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("loan_products.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="submitted", index=True)
    channel: Mapped[str | None] = mapped_column(String(50))
    requested_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    requested_tenure_months: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    credit_score: Mapped[int | None] = mapped_column(Integer)
    approved_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    approved_rate: Mapped[float | None] = mapped_column(Numeric(10, 4))
    approved_tenure_months: Mapped[int | None] = mapped_column(Integer)
    decision_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    decision_at: Mapped[DateTime | None] = mapped_column(DateTime)

    # Branch info for LAP workflow
    branch_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    branch_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    borrower = relationship("Borrower")
    product = relationship("LoanProduct")
