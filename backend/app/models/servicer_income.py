"""
Servicer Fee and Income models for co-lending/partnership arrangements.

ServicerArrangement: Master arrangement for servicing terms
ServicerFeeConfig: Fee configuration per arrangement
ServicerIncomeAccrual: Daily/monthly accrual of servicer income
ServicerIncomeDistribution: Distribution of income to parties
ExcessSpreadTracking: Track excess interest spread income
WithholdingTracker: Track withholding of servicer fees from collections
"""

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ServicerArrangement(Base):
    """
    Master arrangement defining servicing terms between originator and lender.

    Covers:
    - Servicer fee rates and calculation methods
    - Excess spread sharing arrangements
    - Income distribution waterfall
    - Withholding mechanisms
    """
    __tablename__ = "servicer_arrangements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Arrangement identification
    arrangement_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    # Parties
    servicer_id: Mapped[int] = mapped_column(
        ForeignKey("loan_partners.id"),
        index=True
    )  # Party providing servicing (usually originator)
    lender_id: Mapped[int] = mapped_column(
        ForeignKey("loan_partners.id"),
        index=True
    )  # Lender/investor being serviced

    # Servicer fee - flat rate on portfolio
    servicer_fee_rate: Mapped[float] = mapped_column(Numeric(8, 4))  # Annual % on outstanding
    servicer_fee_calculation: Mapped[str] = mapped_column(
        String(30), default="outstanding_principal"
    )  # outstanding_principal, original_principal, collections

    # Minimum guaranteed fee
    min_servicer_fee_monthly: Mapped[float | None] = mapped_column(Numeric(18, 2))
    min_servicer_fee_annual: Mapped[float | None] = mapped_column(Numeric(18, 2))

    # Fee frequency: monthly, quarterly
    fee_frequency: Mapped[str] = mapped_column(String(20), default="monthly")

    # Excess spread arrangement
    # Excess spread = Borrower interest rate - Lender yield rate
    has_excess_spread: Mapped[bool] = mapped_column(Boolean, default=True)
    lender_yield_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))  # Fixed yield to lender

    # Excess spread sharing
    excess_spread_servicer_share: Mapped[float] = mapped_column(
        Numeric(8, 4), default=100
    )  # % of excess spread to servicer (rest to lender)

    # Cap on excess spread retained by servicer
    excess_spread_cap_percent: Mapped[float | None] = mapped_column(Numeric(8, 4))
    excess_spread_cap_absolute: Mapped[float | None] = mapped_column(Numeric(18, 2))

    # Withholding mechanism
    withhold_servicer_fee: Mapped[bool] = mapped_column(Boolean, default=True)
    withholding_method: Mapped[str] = mapped_column(
        String(30), default="deduct_from_collections"
    )  # deduct_from_collections, separate_invoice, periodic_settlement

    # Collection shortfall handling
    servicer_fee_priority: Mapped[int] = mapped_column(Integer, default=1)  # Priority in waterfall
    defer_fee_on_shortfall: Mapped[bool] = mapped_column(Boolean, default=False)

    # Performance-linked fees
    has_performance_fee: Mapped[bool] = mapped_column(Boolean, default=False)
    performance_threshold_collection_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))
    performance_fee_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))

    # Penalty for servicing failures
    sla_breach_penalty_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))

    # Dates
    effective_date: Mapped[Date] = mapped_column(Date)
    expiry_date: Mapped[Date | None] = mapped_column(Date)

    # Link to pool or participation arrangement
    pool_id: Mapped[int | None] = mapped_column(
        ForeignKey("securitization_pools.id"),
        nullable=True
    )
    fldg_arrangement_id: Mapped[int | None] = mapped_column(
        ForeignKey("fldg_arrangements.id"),
        nullable=True
    )

    # Status: active, suspended, terminated
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    servicer = relationship("LoanPartner", foreign_keys=[servicer_id])
    lender = relationship("LoanPartner", foreign_keys=[lender_id])
    pool = relationship("SecuritizationPool")
    fldg_arrangement = relationship("FLDGArrangement")
    income_accruals: Mapped[list["ServicerIncomeAccrual"]] = relationship(
        "ServicerIncomeAccrual",
        back_populates="arrangement",
        cascade="all, delete-orphan"
    )


class ServicerIncomeAccrual(Base):
    """
    Accrual of servicer income (daily/monthly basis).

    Tracks all income components:
    - Servicer fee
    - Excess spread
    - Performance fee
    - Other income
    """
    __tablename__ = "servicer_income_accruals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    arrangement_id: Mapped[int] = mapped_column(
        ForeignKey("servicer_arrangements.id", ondelete="CASCADE"),
        index=True
    )

    # Accrual period
    accrual_date: Mapped[Date] = mapped_column(Date, index=True)
    period_start: Mapped[Date] = mapped_column(Date)
    period_end: Mapped[Date] = mapped_column(Date)
    is_month_end: Mapped[bool] = mapped_column(Boolean, default=False)

    # Portfolio snapshot for calculation
    portfolio_outstanding: Mapped[float] = mapped_column(Numeric(18, 2))
    portfolio_original: Mapped[float] = mapped_column(Numeric(18, 2))
    total_loans: Mapped[int] = mapped_column(Integer)
    active_loans: Mapped[int] = mapped_column(Integer)

    # Collections in period
    principal_collected: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_collected: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fees_collected: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_collected: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Servicer fee calculation
    servicer_fee_base: Mapped[float] = mapped_column(Numeric(18, 2))  # Base for calculation
    servicer_fee_rate_applied: Mapped[float] = mapped_column(Numeric(8, 4))
    servicer_fee_accrued: Mapped[float] = mapped_column(Numeric(18, 2))

    # Excess spread calculation
    weighted_avg_borrower_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))
    lender_yield_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))
    excess_spread_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))
    excess_spread_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    servicer_excess_spread_share: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    lender_excess_spread_share: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Performance fee
    collection_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))  # % of expected collected
    performance_fee_earned: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # SLA penalties
    sla_penalty_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Total income
    total_servicer_income: Mapped[float] = mapped_column(Numeric(18, 2))
    total_lender_income: Mapped[float] = mapped_column(Numeric(18, 2))

    # Tax calculations
    gst_on_servicer_fee: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    tds_on_interest: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Net amounts
    net_servicer_income: Mapped[float] = mapped_column(Numeric(18, 2))
    net_lender_income: Mapped[float] = mapped_column(Numeric(18, 2))

    # Status: accrued, distributed, adjusted
    status: Mapped[str] = mapped_column(String(20), default="accrued", index=True)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    arrangement: Mapped["ServicerArrangement"] = relationship(
        "ServicerArrangement",
        back_populates="income_accruals"
    )


class ServicerIncomeDistribution(Base):
    """
    Distribution of servicer income to parties.

    Records actual payments/settlements of income.
    """
    __tablename__ = "servicer_income_distributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    arrangement_id: Mapped[int] = mapped_column(
        ForeignKey("servicer_arrangements.id"),
        index=True
    )

    # Distribution period
    distribution_date: Mapped[Date] = mapped_column(Date, index=True)
    period_start: Mapped[Date] = mapped_column(Date)
    period_end: Mapped[Date] = mapped_column(Date)

    # Recipient: servicer, lender
    recipient_type: Mapped[str] = mapped_column(String(20), index=True)
    recipient_partner_id: Mapped[int] = mapped_column(
        ForeignKey("loan_partners.id"),
        index=True
    )

    # Income components
    servicer_fee_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    excess_spread_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    performance_fee_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    other_income_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    gross_amount: Mapped[float] = mapped_column(Numeric(18, 2))

    # Deductions
    gst_deducted: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    tds_deducted: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    sla_penalty_deducted: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    other_deductions: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_deductions: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Net amount
    net_amount: Mapped[float] = mapped_column(Numeric(18, 2))

    # Payment details
    payment_mode: Mapped[str | None] = mapped_column(String(30))  # neft, rtgs, internal
    payment_reference: Mapped[str | None] = mapped_column(String(100))
    payment_date: Mapped[Date | None] = mapped_column(Date)

    # Status: pending, paid, cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    arrangement = relationship("ServicerArrangement")
    recipient = relationship("LoanPartner")


class ExcessSpreadTracking(Base):
    """
    Track excess interest spread at loan level.

    Excess spread = Borrower interest rate - Lender yield rate
    This is income for the servicer/originator.
    """
    __tablename__ = "excess_spread_tracking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Loan reference
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id"),
        index=True
    )
    participation_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_participations.id"),
        nullable=True
    )

    # Rate tracking
    tracking_date: Mapped[Date] = mapped_column(Date, index=True)
    period_start: Mapped[Date] = mapped_column(Date)
    period_end: Mapped[Date] = mapped_column(Date)

    # Interest rates
    borrower_interest_rate: Mapped[float] = mapped_column(Numeric(8, 4))
    lender_yield_rate: Mapped[float] = mapped_column(Numeric(8, 4))
    excess_spread_rate: Mapped[float] = mapped_column(Numeric(8, 4))

    # Base for calculation
    principal_outstanding: Mapped[float] = mapped_column(Numeric(18, 2))
    average_principal: Mapped[float] = mapped_column(Numeric(18, 2))

    # Excess spread amounts
    gross_excess_spread: Mapped[float] = mapped_column(Numeric(18, 2))

    # Sharing (if excess spread is shared)
    servicer_share_percent: Mapped[float] = mapped_column(Numeric(8, 4), default=100)
    servicer_share_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    lender_share_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Running totals for the loan
    cumulative_excess_spread: Mapped[float] = mapped_column(Numeric(18, 2))

    # Status: accrued, settled
    status: Mapped[str] = mapped_column(String(20), default="accrued", index=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    loan_account = relationship("LoanAccount")
    participation = relationship("LoanParticipation")


class WithholdingTracker(Base):
    """
    Track withholding of servicer fees from collections.

    When collections are received, servicer fee is withheld before
    passing the balance to the lender.
    """
    __tablename__ = "withholding_tracker"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    arrangement_id: Mapped[int] = mapped_column(
        ForeignKey("servicer_arrangements.id"),
        index=True
    )

    # Collection reference
    collection_date: Mapped[Date] = mapped_column(Date, index=True)
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id"),
        nullable=True
    )

    # Loan reference (if at loan level)
    loan_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_accounts.id"),
        nullable=True
    )

    # Collection amounts
    total_collection: Mapped[float] = mapped_column(Numeric(18, 2))
    principal_collected: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_collected: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fees_collected: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Withholding calculations
    servicer_fee_withheld: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    excess_spread_withheld: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    gst_withheld: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_withheld: Mapped[float] = mapped_column(Numeric(18, 2))

    # Net to lender
    net_to_lender: Mapped[float] = mapped_column(Numeric(18, 2))

    # Lender's share breakdown
    lender_principal_share: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    lender_interest_share: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    lender_fee_share: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Status: withheld, settled, reversed
    status: Mapped[str] = mapped_column(String(20), default="withheld", index=True)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    arrangement = relationship("ServicerArrangement")
    payment = relationship("Payment")
    loan_account = relationship("LoanAccount")
