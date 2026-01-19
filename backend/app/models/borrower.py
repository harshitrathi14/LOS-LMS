from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Borrower(Base):
    __tablename__ = "borrowers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[Date | None] = mapped_column(Date)
    email: Mapped[str | None] = mapped_column(String(200), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), index=True)
    kyc_status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())
