"""Investment models for NCDs, CPs, Bonds, and other fixed income instruments."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InvestmentIssuer(Base):
    """Issuer of investment instruments (corporates, banks, govt, etc.)."""

    __tablename__ = "investment_issuers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Basic info
    issuer_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    issuer_name: Mapped[str] = mapped_column(String(200))
    issuer_type: Mapped[str] = mapped_column(
        String(50)
    )  # corporate, bank, nbfc, psu, government, state_govt, municipal

    # Registration
    cin: Mapped[Optional[str]] = mapped_column(String(50))  # Corporate ID Number
    pan: Mapped[Optional[str]] = mapped_column(String(20))
    lei: Mapped[Optional[str]] = mapped_column(String(30))  # Legal Entity Identifier

    # Industry classification
    industry_sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry_sub_sector: Mapped[Optional[str]] = mapped_column(String(100))

    # Credit ratings
    long_term_rating: Mapped[Optional[str]] = mapped_column(String(20))  # AAA, AA+, AA, etc.
    short_term_rating: Mapped[Optional[str]] = mapped_column(String(20))  # A1+, A1, A2, etc.
    rating_agency: Mapped[Optional[str]] = mapped_column(String(50))  # CRISIL, ICRA, CARE, etc.
    rating_date: Mapped[Optional[date]] = mapped_column(Date)
    rating_outlook: Mapped[Optional[str]] = mapped_column(String(20))  # stable, positive, negative

    # Exposure limits
    internal_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    current_exposure: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    group_exposure: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Contact
    registered_address: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String(200))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    blacklist_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    investments: Mapped[List["Investment"]] = relationship(back_populates="issuer")


class InvestmentProduct(Base):
    """Configuration for investment product types."""

    __tablename__ = "investment_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Product identification
    product_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    product_type: Mapped[str] = mapped_column(
        String(50)
    )  # ncd, cp, bond, gsec, tbill, cd, debenture, psu_bond, state_loan

    # Product category
    category: Mapped[str] = mapped_column(
        String(50)
    )  # fixed_income, money_market, government_securities

    # Interest/Coupon structure
    coupon_type: Mapped[str] = mapped_column(
        String(30)
    )  # fixed, floating, zero_coupon, step_up, step_down
    coupon_frequency: Mapped[str] = mapped_column(
        String(20)
    )  # monthly, quarterly, semi_annual, annual, at_maturity, none

    # Day count convention
    day_count_convention: Mapped[str] = mapped_column(
        String(20), default="ACT/365"
    )  # ACT/365, ACT/360, 30/360, ACT/ACT

    # Default tenures
    min_tenure_days: Mapped[Optional[int]] = mapped_column(Integer)
    max_tenure_days: Mapped[Optional[int]] = mapped_column(Integer)
    typical_tenure_days: Mapped[Optional[int]] = mapped_column(Integer)

    # Minimum investment
    min_investment_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    lot_size: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))  # face value per unit

    # Tax treatment
    tds_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    tds_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=10)  # percentage
    tax_free: Mapped[bool] = mapped_column(Boolean, default=False)

    # Listing
    listed: Mapped[bool] = mapped_column(Boolean, default=False)
    exchange: Mapped[Optional[str]] = mapped_column(String(20))  # NSE, BSE

    # Secured/Unsecured
    secured: Mapped[bool] = mapped_column(Boolean, default=False)
    security_type: Mapped[Optional[str]] = mapped_column(String(100))

    # Call/Put options
    callable: Mapped[bool] = mapped_column(Boolean, default=False)
    puttable: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Investment(Base):
    """Individual investment holding (NCD, CP, Bond, etc.)."""

    __tablename__ = "investments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Investment identification
    investment_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    isin: Mapped[Optional[str]] = mapped_column(String(20), index=True)  # ISIN code
    security_name: Mapped[str] = mapped_column(String(200))

    # Product and Issuer
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("investment_products.id"))
    issuer_id: Mapped[int] = mapped_column(Integer, ForeignKey("investment_issuers.id"))

    # Investment holder (internal entity)
    holder_partner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("loan_partners.id"), nullable=True
    )

    # Instrument details
    instrument_type: Mapped[str] = mapped_column(
        String(50)
    )  # ncd, cp, bond, gsec, tbill, cd, debenture
    series: Mapped[Optional[str]] = mapped_column(String(50))  # Series identifier

    # Face value and units
    face_value_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 2))  # typically 100, 1000, 100000
    units_held: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total_face_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Purchase details
    purchase_date: Mapped[date] = mapped_column(Date, index=True)
    purchase_price_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    purchase_yield: Mapped[Decimal] = mapped_column(Numeric(8, 4))  # YTM at purchase
    total_purchase_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    purchase_premium_discount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Acquisition type
    acquisition_type: Mapped[str] = mapped_column(
        String(30)
    )  # primary, secondary, private_placement

    # Coupon/Interest details
    coupon_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4))  # annual rate
    coupon_type: Mapped[str] = mapped_column(String(30))  # fixed, floating, zero_coupon
    coupon_frequency: Mapped[str] = mapped_column(String(20))  # monthly, quarterly, semi_annual, annual
    next_coupon_date: Mapped[Optional[date]] = mapped_column(Date)
    last_coupon_date: Mapped[Optional[date]] = mapped_column(Date)

    # For floating rate
    benchmark_rate_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("benchmark_rates.id"), nullable=True
    )
    spread_over_benchmark: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    rate_reset_frequency: Mapped[Optional[str]] = mapped_column(String(20))
    next_reset_date: Mapped[Optional[date]] = mapped_column(Date)
    current_effective_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))

    # For step-up/step-down
    step_schedule: Mapped[Optional[str]] = mapped_column(Text)  # JSON: [{"from_date": "2024-01-01", "rate": 9.5}, ...]

    # Maturity
    issue_date: Mapped[date] = mapped_column(Date)
    maturity_date: Mapped[date] = mapped_column(Date, index=True)
    original_tenure_days: Mapped[int] = mapped_column(Integer)
    remaining_tenure_days: Mapped[int] = mapped_column(Integer)

    # Call/Put options
    callable: Mapped[bool] = mapped_column(Boolean, default=False)
    call_date: Mapped[Optional[date]] = mapped_column(Date)
    call_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    puttable: Mapped[bool] = mapped_column(Boolean, default=False)
    put_date: Mapped[Optional[date]] = mapped_column(Date)
    put_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))

    # Current valuation
    current_market_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    current_ytm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    current_market_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    last_valuation_date: Mapped[Optional[date]] = mapped_column(Date)

    # Amortized cost (for HTM)
    amortized_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    amortization_per_period: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))

    # Accrued interest
    accrued_interest: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    last_accrual_date: Mapped[Optional[date]] = mapped_column(Date)

    # Classification (accounting)
    classification: Mapped[str] = mapped_column(
        String(30), default="HTM"
    )  # HTM (Held to Maturity), AFS (Available for Sale), HFT (Held for Trading)

    # Credit rating at investment
    rating_at_investment: Mapped[Optional[str]] = mapped_column(String(20))
    current_rating: Mapped[Optional[str]] = mapped_column(String(20))
    rating_downgraded: Mapped[bool] = mapped_column(Boolean, default=False)

    # Encumbrance
    pledged: Mapped[bool] = mapped_column(Boolean, default=False)
    pledged_to: Mapped[Optional[str]] = mapped_column(String(200))
    pledge_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Status
    status: Mapped[str] = mapped_column(
        String(30), default="active"
    )  # active, matured, sold, defaulted, called, put
    closure_date: Mapped[Optional[date]] = mapped_column(Date)
    closure_type: Mapped[Optional[str]] = mapped_column(String(30))  # maturity, sale, call, put, default

    # Amounts received
    total_coupon_received: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_principal_received: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_tds_deducted: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # For partial sales
    original_units: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    sold_units: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)

    # ECL/Provisioning
    ecl_stage: Mapped[int] = mapped_column(Integer, default=1)
    ecl_provision: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    is_impaired: Mapped[bool] = mapped_column(Boolean, default=False)
    impairment_date: Mapped[Optional[date]] = mapped_column(Date)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    product: Mapped["InvestmentProduct"] = relationship()
    issuer: Mapped["InvestmentIssuer"] = relationship(back_populates="investments")
    coupon_schedules: Mapped[List["InvestmentCouponSchedule"]] = relationship(
        back_populates="investment"
    )
    accruals: Mapped[List["InvestmentAccrual"]] = relationship(back_populates="investment")
    transactions: Mapped[List["InvestmentTransaction"]] = relationship(
        back_populates="investment"
    )
    valuations: Mapped[List["InvestmentValuation"]] = relationship(back_populates="investment")
    selldown_transactions: Mapped[List["SelldownTransaction"]] = relationship(
        back_populates="investment"
    )


class InvestmentCouponSchedule(Base):
    """Coupon payment schedule for an investment."""

    __tablename__ = "investment_coupon_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    investment_id: Mapped[int] = mapped_column(Integer, ForeignKey("investments.id"))

    # Schedule details
    coupon_number: Mapped[int] = mapped_column(Integer)
    period_start_date: Mapped[date] = mapped_column(Date)
    period_end_date: Mapped[date] = mapped_column(Date)
    coupon_date: Mapped[date] = mapped_column(Date, index=True)  # payment date
    record_date: Mapped[Optional[date]] = mapped_column(Date)

    # Coupon calculation
    coupon_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    face_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    days_in_period: Mapped[int] = mapped_column(Integer)
    coupon_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Tax
    tds_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=10)
    tds_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    net_coupon: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Principal (for amortizing instruments)
    principal_component: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Status
    status: Mapped[str] = mapped_column(
        String(30), default="scheduled"
    )  # scheduled, accrued, received, missed, written_off
    received_date: Mapped[Optional[date]] = mapped_column(Date)
    received_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    investment: Mapped["Investment"] = relationship(back_populates="coupon_schedules")


class InvestmentAccrual(Base):
    """Daily interest accrual for investments."""

    __tablename__ = "investment_accruals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    investment_id: Mapped[int] = mapped_column(Integer, ForeignKey("investments.id"))

    # Accrual period
    accrual_date: Mapped[date] = mapped_column(Date, index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)

    # Calculation inputs
    face_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    coupon_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    day_count_convention: Mapped[str] = mapped_column(String(20))
    days_accrued: Mapped[int] = mapped_column(Integer)

    # Accrual amounts
    interest_accrued: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cumulative_accrued: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Premium/discount amortization
    premium_discount_amortized: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    cumulative_amortization: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Net interest income (accrued interest +/- amortization)
    net_interest_income: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    # Posting status
    posted_to_gl: Mapped[bool] = mapped_column(Boolean, default=False)
    gl_posting_date: Mapped[Optional[date]] = mapped_column(Date)
    gl_reference: Mapped[Optional[str]] = mapped_column(String(50))

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    investment: Mapped["Investment"] = relationship(back_populates="accruals")


class InvestmentTransaction(Base):
    """Transactions related to an investment (purchase, sale, coupon, maturity)."""

    __tablename__ = "investment_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    investment_id: Mapped[int] = mapped_column(Integer, ForeignKey("investments.id"))

    # Transaction details
    transaction_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    transaction_type: Mapped[str] = mapped_column(
        String(30)
    )  # purchase, sale, coupon, maturity, call, put, partial_sale
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    value_date: Mapped[date] = mapped_column(Date)

    # Units and amounts
    units: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    face_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    consideration: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    accrued_interest: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # For sales
    book_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    gain_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))

    # Yield
    yield_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))

    # Tax
    tds_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Counterparty (for secondary market)
    counterparty: Mapped[Optional[str]] = mapped_column(String(200))
    broker: Mapped[Optional[str]] = mapped_column(String(200))
    brokerage: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Settlement
    settlement_status: Mapped[str] = mapped_column(String(30), default="pending")
    settlement_date: Mapped[Optional[date]] = mapped_column(Date)
    settlement_reference: Mapped[Optional[str]] = mapped_column(String(100))

    # Remarks
    remarks: Mapped[Optional[str]] = mapped_column(Text)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    investment: Mapped["Investment"] = relationship(back_populates="transactions")


class InvestmentValuation(Base):
    """Periodic mark-to-market valuation for investments."""

    __tablename__ = "investment_valuations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    investment_id: Mapped[int] = mapped_column(Integer, ForeignKey("investments.id"))

    # Valuation details
    valuation_date: Mapped[date] = mapped_column(Date, index=True)
    valuation_type: Mapped[str] = mapped_column(
        String(30)
    )  # daily, monthly, quarterly, adhoc

    # Book value
    face_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    amortized_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    accrued_interest: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    book_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Market value
    market_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    price_source: Mapped[Optional[str]] = mapped_column(String(50))  # exchange, dealer_quote, model

    # Yield
    book_yield: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    market_yield: Mapped[Decimal] = mapped_column(Numeric(8, 4))

    # MTM impact
    mtm_gain_loss: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    cumulative_mtm: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    # Duration and risk metrics
    modified_duration: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    macaulay_duration: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    convexity: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    investment: Mapped["Investment"] = relationship(back_populates="valuations")


class InvestmentPortfolioSummary(Base):
    """Daily summary of investment portfolio."""

    __tablename__ = "investment_portfolio_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Summary date
    summary_date: Mapped[date] = mapped_column(Date, index=True)
    holder_partner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("loan_partners.id"), nullable=True
    )

    # By instrument type
    instrument_type: Mapped[str] = mapped_column(String(50))  # ncd, cp, bond, gsec, all

    # Holdings
    total_investments: Mapped[int] = mapped_column(Integer, default=0)
    total_face_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_book_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_accrued_interest: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Yield metrics
    weighted_avg_coupon: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    weighted_avg_ytm: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)

    # Duration
    weighted_avg_duration: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    weighted_avg_maturity_days: Mapped[int] = mapped_column(Integer, default=0)

    # MTM
    total_mtm_gain_loss: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Rating distribution
    aaa_exposure: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    aa_exposure: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    a_exposure: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    bbb_exposure: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    below_bbb_exposure: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    unrated_exposure: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Maturity buckets
    maturing_0_30_days: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    maturing_31_90_days: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    maturing_91_180_days: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    maturing_181_365_days: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    maturing_1_3_years: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    maturing_3_plus_years: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Income metrics (MTD/YTD)
    coupon_income_mtd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    coupon_income_ytd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    amortization_income_mtd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    trading_gain_loss_mtd: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
