"""
KYC (Know Your Customer) verification models.

KYCVerification: Tracks KYC verification status for borrowers
"""

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KYCVerification(Base):
    """
    KYC verification record for a borrower.

    Tracks verification of identity documents, address, income, etc.
    """
    __tablename__ = "kyc_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    borrower_id: Mapped[int] = mapped_column(
        ForeignKey("borrowers.id", ondelete="CASCADE"),
        index=True
    )

    # Verification type: identity, address, income, employment, bank_statement
    verification_type: Mapped[str] = mapped_column(String(50), index=True)

    # Document reference
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"),
        nullable=True
    )
    document_type: Mapped[str | None] = mapped_column(String(50))  # aadhaar, pan, passport, etc.
    document_number: Mapped[str | None] = mapped_column(String(100))

    # Verification status: pending, in_progress, verified, failed, expired
    verification_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    # Verification details
    verified_at: Mapped[DateTime | None] = mapped_column(DateTime)
    verified_by: Mapped[str | None] = mapped_column(String(100))
    verification_method: Mapped[str | None] = mapped_column(String(50))  # manual, api, ocr

    # External verification
    external_reference: Mapped[str | None] = mapped_column(String(200))
    external_response: Mapped[str | None] = mapped_column(Text)  # JSON response

    # Verification result
    match_score: Mapped[int | None] = mapped_column(Integer)  # 0-100 match score
    verification_data: Mapped[str | None] = mapped_column(Text)  # JSON extracted data

    # Failure details
    failure_reason: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Expiry
    expiry_date: Mapped[Date | None] = mapped_column(Date)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False)

    # Risk flags
    risk_flags: Mapped[str | None] = mapped_column(Text)  # JSON array of flags
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    borrower = relationship("Borrower")
    document = relationship("Document")


class KYCRequirement(Base):
    """
    KYC requirements for a loan product.

    Defines what verifications are required for a product.
    """
    __tablename__ = "kyc_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("loan_products.id", ondelete="CASCADE"),
        index=True
    )

    # Verification type required
    verification_type: Mapped[str] = mapped_column(String(50))

    # Accepted document types (JSON array)
    accepted_documents_json: Mapped[str] = mapped_column(Text)

    # Is this verification mandatory?
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)

    # Minimum requirements
    min_match_score: Mapped[int] = mapped_column(Integer, default=80)

    # Validity period in days (for re-verification)
    validity_days: Mapped[int | None] = mapped_column(Integer)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    product = relationship("LoanProduct")


class CreditBureauReport(Base):
    """
    Credit bureau report for a borrower.
    """
    __tablename__ = "credit_bureau_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    borrower_id: Mapped[int] = mapped_column(
        ForeignKey("borrowers.id", ondelete="CASCADE"),
        index=True
    )
    loan_application_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_applications.id"),
        nullable=True
    )

    # Bureau info
    bureau_name: Mapped[str] = mapped_column(String(50))  # CIBIL, Experian, Equifax
    report_date: Mapped[DateTime] = mapped_column(DateTime, index=True)
    reference_number: Mapped[str] = mapped_column(String(100), unique=True)

    # Score
    credit_score: Mapped[int | None] = mapped_column(Integer)
    score_version: Mapped[str | None] = mapped_column(String(20))

    # Summary
    total_accounts: Mapped[int | None] = mapped_column(Integer)
    active_accounts: Mapped[int | None] = mapped_column(Integer)
    overdue_accounts: Mapped[int | None] = mapped_column(Integer)
    total_outstanding: Mapped[float | None] = mapped_column()
    total_overdue: Mapped[float | None] = mapped_column()
    max_dpd_last_12_months: Mapped[int | None] = mapped_column(Integer)

    # Enquiry summary
    enquiries_last_30_days: Mapped[int | None] = mapped_column(Integer)
    enquiries_last_90_days: Mapped[int | None] = mapped_column(Integer)
    enquiries_last_6_months: Mapped[int | None] = mapped_column(Integer)

    # Full report (JSON)
    report_json: Mapped[str | None] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="received")  # pending, received, error
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    borrower = relationship("Borrower")
    loan_application = relationship("LoanApplication")
