from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LoanParticipation(Base):
    __tablename__ = "loan_participations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id"), index=True
    )
    partner_id: Mapped[int] = mapped_column(ForeignKey("loan_partners.id"), index=True)
    share_percent: Mapped[float] = mapped_column(Numeric(7, 4))
    interest_rate: Mapped[float | None] = mapped_column(Numeric(10, 4))
    fee_share_percent: Mapped[float | None] = mapped_column(Numeric(7, 4))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    loan_account = relationship("LoanAccount")
    partner = relationship("LoanPartner")
