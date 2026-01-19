"""
Supply chain finance models.

Counterparty: Buyers and suppliers in SCF transactions
Invoice: Invoices for financing
CreditLimit: Credit limits for counterparties
"""

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Counterparty(Base):
    """
    Counterparty in supply chain finance (buyer or supplier).
    """
    __tablename__ = "counterparties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Counterparty type: buyer, supplier, anchor
    counterparty_type: Mapped[str] = mapped_column(String(20), index=True)

    # Identification
    name: Mapped[str] = mapped_column(String(200))
    trading_name: Mapped[str | None] = mapped_column(String(200))
    registration_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    tax_id: Mapped[str | None] = mapped_column(String(50))

    # Contact info
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(50), default="India")
    contact_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))

    # Bank details
    bank_name: Mapped[str | None] = mapped_column(String(100))
    bank_account_number: Mapped[str | None] = mapped_column(String(50))
    bank_ifsc: Mapped[str | None] = mapped_column(String(20))

    # Credit limit
    credit_limit: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    credit_limit_utilized: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    credit_limit_available: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Risk rating: AAA, AA, A, BBB, BB, B, C, D
    risk_rating: Mapped[str | None] = mapped_column(String(10))
    risk_rating_date: Mapped[Date | None] = mapped_column(Date)

    # Status: active, suspended, blacklisted
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    # Linked to a borrower record if applicable
    borrower_id: Mapped[int | None] = mapped_column(
        ForeignKey("borrowers.id"),
        nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    borrower = relationship("Borrower")
    invoices_as_buyer: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        foreign_keys="Invoice.buyer_id",
        back_populates="buyer"
    )
    invoices_as_supplier: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        foreign_keys="Invoice.supplier_id",
        back_populates="supplier"
    )
    credit_limits: Mapped[list["CreditLimit"]] = relationship(
        "CreditLimit",
        back_populates="counterparty",
        cascade="all, delete-orphan"
    )


class Invoice(Base):
    """
    Invoice for supply chain financing.
    """
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Invoice identification
    invoice_number: Mapped[str] = mapped_column(String(100), index=True)
    external_reference: Mapped[str | None] = mapped_column(String(100))

    # Parties
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("counterparties.id"),
        index=True
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("counterparties.id"),
        index=True
    )

    # Dates
    invoice_date: Mapped[Date] = mapped_column(Date, index=True)
    due_date: Mapped[Date] = mapped_column(Date, index=True)
    acceptance_date: Mapped[Date | None] = mapped_column(Date)

    # Amounts
    invoice_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    tax_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    # Financing
    financed_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    advance_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=80)  # % of invoice
    financing_date: Mapped[Date | None] = mapped_column(Date)
    loan_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_accounts.id"),
        nullable=True
    )

    # Payment tracking
    paid_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    payment_date: Mapped[Date | None] = mapped_column(Date)

    # Status: pending, accepted, financed, partially_paid, paid, overdue, cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    # Dilution/adjustment
    dilution_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    dilution_reason: Mapped[str | None] = mapped_column(Text)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Unique constraint
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    # Relationships
    buyer: Mapped["Counterparty"] = relationship(
        "Counterparty",
        foreign_keys=[buyer_id],
        back_populates="invoices_as_buyer"
    )
    supplier: Mapped["Counterparty"] = relationship(
        "Counterparty",
        foreign_keys=[supplier_id],
        back_populates="invoices_as_supplier"
    )
    loan_account = relationship("LoanAccount")


class CreditLimit(Base):
    """
    Credit limit for a counterparty.
    """
    __tablename__ = "credit_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    counterparty_id: Mapped[int] = mapped_column(
        ForeignKey("counterparties.id", ondelete="CASCADE"),
        index=True
    )

    # Limit type: overall, buyer, supplier, product_specific
    limit_type: Mapped[str] = mapped_column(String(30))

    # For product-specific limits
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_products.id"),
        nullable=True
    )

    # Amounts
    limit_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    utilized_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    available_amount: Mapped[float] = mapped_column(Numeric(18, 2))

    # Validity
    effective_date: Mapped[Date] = mapped_column(Date)
    expiry_date: Mapped[Date] = mapped_column(Date)

    # Status: active, suspended, expired
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    # Approval
    approved_by: Mapped[str | None] = mapped_column(String(100))
    approved_at: Mapped[DateTime | None] = mapped_column(DateTime)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    counterparty: Mapped["Counterparty"] = relationship(
        "Counterparty",
        back_populates="credit_limits"
    )
    product = relationship("LoanProduct")
