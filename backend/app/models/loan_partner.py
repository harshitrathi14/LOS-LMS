from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoanPartner(Base):
    __tablename__ = "loan_partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    partner_type: Mapped[str] = mapped_column(String(50), default="lender")
    external_code: Mapped[str | None] = mapped_column(String(100), unique=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())
