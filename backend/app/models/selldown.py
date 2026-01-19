"""Selldown models for loan/investment transfers and partial/full sales."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SelldownBuyer(Base):
    """Entity that purchases loans or investments (banks, NBFCs, AIFs, etc.)."""

    __tablename__ = "selldown_buyers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Basic info
    buyer_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    buyer_name: Mapped[str] = mapped_column(String(200))
    buyer_type: Mapped[str] = mapped_column(
        String(50)
    )  # bank, nbfc, aif, insurance, mutual_fund, foreign_investor

    # Registration details
    registration_number: Mapped[Optional[str]] = mapped_column(String(100))
    regulatory_category: Mapped[Optional[str]] = mapped_column(String(50))  # scheduled_bank, nbfc_nd, nbfc_d, aif_cat1, aif_cat2

    # Contact
    contact_person: Mapped[Optional[str]] = mapped_column(String(200))
    contact_email: Mapped[Optional[str]] = mapped_column(String(200))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[Optional[str]] = mapped_column(Text)

    # Banking details for settlements
    bank_name: Mapped[Optional[str]] = mapped_column(String(200))
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(50))
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(20))

    # Limits and exposure
    total_exposure_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    current_exposure: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Preferences
    preferred_asset_types: Mapped[Optional[str]] = mapped_column(Text)  # JSON: ["retail_loans", "corporate_loans", "ncds"]
    min_ticket_size: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    max_ticket_size: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    preferred_rating: Mapped[Optional[str]] = mapped_column(String(50))  # min rating accepted

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarded_date: Mapped[Optional[date]] = mapped_column(Date)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    selldown_transactions: Mapped[list["SelldownTransaction"]] = relationship(
        back_populates="buyer"
    )


class SelldownTransaction(Base):
    """Records sale/transfer of loan or investment to a buyer."""

    __tablename__ = "selldown_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Transaction identification
    transaction_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    transaction_type: Mapped[str] = mapped_column(
        String(30)
    )  # full_selldown, partial_selldown, assignment, participation_sale

    # Asset being sold (either loan or investment)
    asset_type: Mapped[str] = mapped_column(String(30))  # loan, investment
    loan_account_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("loan_accounts.id"), nullable=True
    )
    investment_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("investments.id"), nullable=True
    )

    # Buyer
    buyer_id: Mapped[int] = mapped_column(Integer, ForeignKey("selldown_buyers.id"))

    # Seller (original holder)
    seller_partner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("loan_partners.id"), nullable=True
    )

    # Sale details
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    value_date: Mapped[date] = mapped_column(Date)  # settlement date

    # Amounts - Original position
    original_principal: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    outstanding_principal: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    accrued_interest: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    outstanding_fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_outstanding: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Sale amounts
    selldown_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4))  # 100.0000 for full, <100 for partial
    selldown_principal: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    selldown_interest: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    selldown_fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Pricing
    sale_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))  # actual consideration
    price_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4))  # % of outstanding (e.g., 98.50%)
    premium_discount: Mapped[Decimal] = mapped_column(Numeric(18, 2))  # +ve premium, -ve discount

    # Yield/Rate
    original_yield: Mapped[Decimal] = mapped_column(Numeric(8, 4))  # original interest rate
    sale_yield: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))  # implied yield at sale price
    yield_spread: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))  # spread earned/given up

    # Gain/Loss calculation
    book_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))  # carrying value at sale
    gain_loss: Mapped[Decimal] = mapped_column(Numeric(18, 2))  # sale_price - book_value
    gain_loss_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4))

    # Remaining position (for partial selldown)
    retained_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    retained_principal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Servicing arrangement post-sale
    servicing_retained: Mapped[bool] = mapped_column(Boolean, default=True)  # seller continues servicing
    servicer_fee_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))  # annual rate

    # FLDG/Credit enhancement
    fldg_transferred: Mapped[bool] = mapped_column(Boolean, default=False)
    fldg_amount_transferred: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    credit_enhancement_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))

    # Risk transfer assessment
    risk_transfer_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    derecognition_applicable: Mapped[bool] = mapped_column(Boolean, default=True)

    # Documentation
    agreement_reference: Mapped[Optional[str]] = mapped_column(String(100))
    agreement_date: Mapped[Optional[date]] = mapped_column(Date)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(30), default="initiated"
    )  # initiated, approved, settled, cancelled, reversed

    # Approval workflow
    initiated_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Settlement
    settlement_reference: Mapped[Optional[str]] = mapped_column(String(100))
    settlement_bank_reference: Mapped[Optional[str]] = mapped_column(String(100))

    # Remarks
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    buyer: Mapped["SelldownBuyer"] = relationship(back_populates="selldown_transactions")
    loan_account: Mapped[Optional["LoanAccount"]] = relationship(
        "LoanAccount", back_populates="selldown_transactions"
    )
    investment: Mapped[Optional["Investment"]] = relationship(
        "Investment", back_populates="selldown_transactions"
    )


class SelldownSettlement(Base):
    """Tracks settlement of selldown transactions."""

    __tablename__ = "selldown_settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Link to transaction
    selldown_transaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("selldown_transactions.id")
    )

    # Settlement details
    settlement_date: Mapped[date] = mapped_column(Date)
    settlement_type: Mapped[str] = mapped_column(String(30))  # principal, interest, fees, adjustment

    # Amounts
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    tds_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    gst_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Payment direction
    payment_direction: Mapped[str] = mapped_column(String(20))  # buyer_to_seller, seller_to_buyer

    # Bank details
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100))
    payment_mode: Mapped[Optional[str]] = mapped_column(String(30))  # rtgs, neft, cheque
    payment_date: Mapped[Optional[date]] = mapped_column(Date)

    # Status
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending, completed, failed

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SelldownCollectionSplit(Base):
    """Tracks collection splits post-selldown for servicing arrangements."""

    __tablename__ = "selldown_collection_splits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Link to transaction
    selldown_transaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("selldown_transactions.id")
    )

    # Collection details
    collection_date: Mapped[date] = mapped_column(Date)
    collection_reference: Mapped[Optional[str]] = mapped_column(String(100))

    # Total collection
    total_principal_collected: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    total_interest_collected: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    total_fees_collected: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_collection: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Buyer's share
    buyer_principal_share: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    buyer_interest_share: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    buyer_fees_share: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    buyer_total_share: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Seller's retained share (if partial selldown)
    seller_principal_share: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    seller_interest_share: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    seller_fees_share: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    seller_total_share: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Servicer fee deduction
    servicer_fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    servicer_fee_gst: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Net to buyer after servicer fee
    net_to_buyer: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Remittance tracking
    remittance_status: Mapped[str] = mapped_column(String(30), default="pending")
    remittance_date: Mapped[Optional[date]] = mapped_column(Date)
    remittance_reference: Mapped[Optional[str]] = mapped_column(String(100))

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SelldownPortfolioSummary(Base):
    """Daily/periodic summary of selldown portfolio."""

    __tablename__ = "selldown_portfolio_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Summary date
    summary_date: Mapped[date] = mapped_column(Date, index=True)
    buyer_id: Mapped[int] = mapped_column(Integer, ForeignKey("selldown_buyers.id"))

    # Portfolio metrics
    total_transactions: Mapped[int] = mapped_column(Integer, default=0)
    total_loans_sold: Mapped[int] = mapped_column(Integer, default=0)
    total_investments_sold: Mapped[int] = mapped_column(Integer, default=0)

    # Outstanding amounts
    total_principal_outstanding: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_interest_outstanding: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Collection metrics
    total_collections_mtd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_collections_ytd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Servicer fee metrics
    servicer_fee_accrued_mtd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    servicer_fee_collected_mtd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Delinquency in sold portfolio
    dpd_0_count: Mapped[int] = mapped_column(Integer, default=0)
    dpd_1_30_count: Mapped[int] = mapped_column(Integer, default=0)
    dpd_31_60_count: Mapped[int] = mapped_column(Integer, default=0)
    dpd_61_90_count: Mapped[int] = mapped_column(Integer, default=0)
    dpd_90_plus_count: Mapped[int] = mapped_column(Integer, default=0)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
