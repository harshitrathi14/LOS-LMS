from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
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
    collateral_id: Mapped[int | None] = mapped_column(
        ForeignKey("collaterals.id"), nullable=True
    )
    document_type: Mapped[str] = mapped_column(String(100))
    file_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="uploaded")

    # Media categorization
    media_type: Mapped[str] = mapped_column(String(20), default="document")  # photo, video, document
    section: Mapped[str | None] = mapped_column(String(50))  # collateral_exterior, collateral_interior, site_visit, due_diligence, title_deed, valuation_report, legal_opinion

    # File metadata
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    thumbnail_path: Mapped[str | None] = mapped_column(String(500))

    # Geo-tagging
    capture_latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    capture_longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    captured_at: Mapped[DateTime | None] = mapped_column(DateTime)
    captured_by: Mapped[str | None] = mapped_column(String(200))

    # Description
    description: Mapped[str | None] = mapped_column(String(1000))

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    borrower = relationship("Borrower")
    application = relationship("LoanApplication")
    loan_account = relationship("LoanAccount")
    collateral = relationship("Collateral", back_populates="documents")
