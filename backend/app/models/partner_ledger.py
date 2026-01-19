"""
Partner Ledger models for co-lending payment tracking and settlements.

PartnerLedgerEntry: Individual ledger entries for partner share tracking
PartnerSettlement: Settlement batches for partners
PartnerSettlementDetail: Line items in a settlement
"""

from sqlalchemy import (
    Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PartnerLedgerEntry(Base):
    """
    Ledger entry tracking partner's share in loan transactions.

    Entry types:
    - disbursement: Partner's share of loan disbursement
    - principal_collection: Principal collected on partner's share
    - interest_collection: Interest collected on partner's share
    - fee_collection: Fees collected on partner's share
    - settlement: Amount settled to partner
    - adjustment: Manual adjustments
    """
    __tablename__ = "partner_ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participation_id: Mapped[int] = mapped_column(
        ForeignKey("loan_participations.id", ondelete="CASCADE"),
        index=True
    )

    # Entry details
    entry_type: Mapped[str] = mapped_column(String(30), index=True)
    entry_date: Mapped[Date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))  # Positive = owed to partner

    # Reference to source transaction
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id"),
        nullable=True
    )
    settlement_id: Mapped[int | None] = mapped_column(
        ForeignKey("partner_settlements.id"),
        nullable=True
    )

    # Running balance for this participation
    running_balance: Mapped[float] = mapped_column(Numeric(18, 2))

    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    participation = relationship("LoanParticipation")
    payment = relationship("Payment")


class PartnerSettlement(Base):
    """
    Settlement batch for a partner.

    Aggregates ledger entries for a period and tracks settlement status.
    """
    __tablename__ = "partner_settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partner_id: Mapped[int] = mapped_column(
        ForeignKey("loan_partners.id"),
        index=True
    )
    settlement_date: Mapped[Date] = mapped_column(Date, index=True)

    # Settlement period
    period_start: Mapped[Date] = mapped_column(Date)
    period_end: Mapped[Date] = mapped_column(Date)

    # Settlement amounts
    total_principal: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_interest: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_fees: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_adjustments: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    net_amount: Mapped[float] = mapped_column(Numeric(18, 2))

    # Status: pending, approved, paid, cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    # Payment details
    payment_reference: Mapped[str | None] = mapped_column(String(100))
    payment_date: Mapped[Date | None] = mapped_column(Date)
    payment_mode: Mapped[str | None] = mapped_column(String(30))

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    partner = relationship("LoanPartner")
    details: Mapped[list["PartnerSettlementDetail"]] = relationship(
        "PartnerSettlementDetail",
        back_populates="settlement",
        cascade="all, delete-orphan"
    )
    ledger_entries: Mapped[list["PartnerLedgerEntry"]] = relationship(
        "PartnerLedgerEntry",
        backref="settlement_ref"
    )


class PartnerSettlementDetail(Base):
    """
    Line item in a partner settlement.

    One entry per loan account included in the settlement.
    """
    __tablename__ = "partner_settlement_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    settlement_id: Mapped[int] = mapped_column(
        ForeignKey("partner_settlements.id", ondelete="CASCADE"),
        index=True
    )
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id"),
        index=True
    )

    # Amounts for this loan
    principal_share: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    interest_share: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    fee_share: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total_share: Mapped[float] = mapped_column(Numeric(18, 2))

    # Share percentage at time of settlement
    share_percent: Mapped[float] = mapped_column(Numeric(10, 4))

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    settlement: Mapped["PartnerSettlement"] = relationship(
        "PartnerSettlement",
        back_populates="details"
    )
    loan_account = relationship("LoanAccount")
