"""
Securitization models.

SecuritizationPool: Pool of loans for securitization (PTC/DA)
PoolLoan: Loans included in a pool
Investor: Investors in securitized pools
PoolInvestment: Investment in a pool
InvestorCashFlow: Cash flow distributions to investors
"""

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SecuritizationPool(Base):
    """
    Pool of loans for securitization.

    Types: PTC (Pass-Through Certificate), DA (Direct Assignment)
    """
    __tablename__ = "securitization_pools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Pool identification
    pool_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    # Pool type: ptc (Pass-Through Certificate), da (Direct Assignment)
    pool_type: Mapped[str] = mapped_column(String(20), index=True)

    # Dates
    cutoff_date: Mapped[Date] = mapped_column(Date, index=True)
    settlement_date: Mapped[Date | None] = mapped_column(Date)
    maturity_date: Mapped[Date | None] = mapped_column(Date)

    # Pool characteristics
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_products.id"),
        nullable=True
    )

    # Pool statistics
    total_loans: Mapped[int] = mapped_column(Integer, default=0)
    total_principal: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    weighted_avg_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))
    weighted_avg_tenure: Mapped[int | None] = mapped_column(Integer)  # months
    weighted_avg_ltv: Mapped[float | None] = mapped_column(Numeric(8, 4))

    # Pool performance
    current_principal: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    cumulative_collections: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    cumulative_prepayments: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    cumulative_defaults: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    current_delinquency_rate: Mapped[float] = mapped_column(Numeric(8, 4), default=0)

    # Credit enhancement
    cash_collateral: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    excess_spread: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    first_loss_piece: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Servicer info
    servicer_name: Mapped[str | None] = mapped_column(String(200))
    servicer_fee_rate: Mapped[float] = mapped_column(Numeric(8, 4), default=0)

    # Trustee info
    trustee_name: Mapped[str | None] = mapped_column(String(200))
    trustee_fee_rate: Mapped[float] = mapped_column(Numeric(8, 4), default=0)

    # Status: draft, active, closed, terminated
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    product = relationship("LoanProduct")
    pool_loans: Mapped[list["PoolLoan"]] = relationship(
        "PoolLoan",
        back_populates="pool",
        cascade="all, delete-orphan"
    )
    investments: Mapped[list["PoolInvestment"]] = relationship(
        "PoolInvestment",
        back_populates="pool",
        cascade="all, delete-orphan"
    )


class PoolLoan(Base):
    """
    Loan included in a securitization pool.
    """
    __tablename__ = "pool_loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pool_id: Mapped[int] = mapped_column(
        ForeignKey("securitization_pools.id", ondelete="CASCADE"),
        index=True
    )
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id"),
        index=True
    )

    # Inclusion details
    inclusion_date: Mapped[Date] = mapped_column(Date)
    principal_at_inclusion: Mapped[float] = mapped_column(Numeric(18, 2))
    rate_at_inclusion: Mapped[float] = mapped_column(Numeric(8, 4))
    tenure_at_inclusion: Mapped[int] = mapped_column(Integer)  # remaining months

    # Current status
    current_principal: Mapped[float] = mapped_column(Numeric(18, 2))
    dpd_at_inclusion: Mapped[int] = mapped_column(Integer, default=0)
    current_dpd: Mapped[int] = mapped_column(Integer, default=0)

    # Status: active, prepaid, defaulted, removed
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    removal_date: Mapped[Date | None] = mapped_column(Date)
    removal_reason: Mapped[str | None] = mapped_column(String(50))

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    pool: Mapped["SecuritizationPool"] = relationship(
        "SecuritizationPool",
        back_populates="pool_loans"
    )
    loan_account = relationship("LoanAccount")


class Investor(Base):
    """
    Investor in securitization pools.
    """
    __tablename__ = "investors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identification
    name: Mapped[str] = mapped_column(String(200))
    investor_type: Mapped[str] = mapped_column(String(50))  # bank, nbfc, mutual_fund, insurance
    external_code: Mapped[str | None] = mapped_column(String(50), unique=True)

    # Contact
    contact_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)

    # Bank details for payouts
    bank_name: Mapped[str | None] = mapped_column(String(100))
    bank_account_number: Mapped[str | None] = mapped_column(String(50))
    bank_ifsc: Mapped[str | None] = mapped_column(String(20))

    # Regulatory
    pan: Mapped[str | None] = mapped_column(String(20))
    gst_number: Mapped[str | None] = mapped_column(String(20))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    investments: Mapped[list["PoolInvestment"]] = relationship(
        "PoolInvestment",
        back_populates="investor",
        cascade="all, delete-orphan"
    )


class PoolInvestment(Base):
    """
    Investment in a securitization pool.
    """
    __tablename__ = "pool_investments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pool_id: Mapped[int] = mapped_column(
        ForeignKey("securitization_pools.id", ondelete="CASCADE"),
        index=True
    )
    investor_id: Mapped[int] = mapped_column(
        ForeignKey("investors.id"),
        index=True
    )

    # Investment details
    investment_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    investment_percent: Mapped[float] = mapped_column(Numeric(8, 4))  # % of pool
    expected_yield: Mapped[float] = mapped_column(Numeric(8, 4))  # annual %
    investment_date: Mapped[Date] = mapped_column(Date)

    # Tranche (for structured deals)
    tranche: Mapped[str] = mapped_column(String(20), default="senior")  # senior, mezzanine, junior

    # Current position
    current_principal: Mapped[float] = mapped_column(Numeric(18, 2))
    accrued_interest: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_distributions: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Status: active, fully_redeemed, written_off
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    pool: Mapped["SecuritizationPool"] = relationship(
        "SecuritizationPool",
        back_populates="investments"
    )
    investor: Mapped["Investor"] = relationship(
        "Investor",
        back_populates="investments"
    )
    cash_flows: Mapped[list["InvestorCashFlow"]] = relationship(
        "InvestorCashFlow",
        back_populates="investment",
        cascade="all, delete-orphan"
    )


class InvestorCashFlow(Base):
    """
    Cash flow distribution to an investor.
    """
    __tablename__ = "investor_cash_flows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investment_id: Mapped[int] = mapped_column(
        ForeignKey("pool_investments.id", ondelete="CASCADE"),
        index=True
    )

    # Cash flow details
    cash_flow_date: Mapped[Date] = mapped_column(Date, index=True)
    cash_flow_type: Mapped[str] = mapped_column(String(30))  # principal, interest, prepayment, residual

    # Amounts
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    tax_deducted: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    net_amount: Mapped[float] = mapped_column(Numeric(18, 2))

    # Payment tracking
    payment_reference: Mapped[str | None] = mapped_column(String(100))
    payment_date: Mapped[Date | None] = mapped_column(Date)
    payment_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, paid

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    investment: Mapped["PoolInvestment"] = relationship(
        "PoolInvestment",
        back_populates="cash_flows"
    )
