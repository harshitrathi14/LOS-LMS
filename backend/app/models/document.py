from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    borrower_id: Mapped[int | None] = mapped_column(ForeignKey("borrowers.id"))
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_applications.id")
    )
    loan_account_id: Mapped[int | None] = mapped_column(ForeignKey("loan_accounts.id"))
    document_type: Mapped[str] = mapped_column(String(100))
    file_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    borrower = relationship("Borrower")
    application = relationship("LoanApplication")
    loan_account = relationship("LoanAccount")
