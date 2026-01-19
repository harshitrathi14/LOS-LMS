"""
Collection management models.

CollectionCase: Collection case for delinquent loans
CollectionAction: Actions taken on a case
PromiseToPay: Customer promises to pay
EscalationRule: Rules for automatic escalation
"""

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CollectionCase(Base):
    """
    Collection case for a delinquent loan.

    One loan can have multiple cases over time (closed and reopened).
    """
    __tablename__ = "collection_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loan_account_id: Mapped[int] = mapped_column(
        ForeignKey("loan_accounts.id", ondelete="CASCADE"),
        index=True
    )

    # Case identification
    case_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)

    # Status: open, in_progress, resolved, closed, written_off
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)

    # Priority: low, medium, high, critical
    priority: Mapped[str] = mapped_column(String(20), default="medium")

    # Assignment
    assigned_to: Mapped[str | None] = mapped_column(String(100))  # User ID or name
    assigned_queue: Mapped[str | None] = mapped_column(String(50))  # Collection queue

    # Case dates
    opened_date: Mapped[Date] = mapped_column(Date, index=True)
    last_action_date: Mapped[Date | None] = mapped_column(Date)
    next_action_date: Mapped[Date | None] = mapped_column(Date)

    # Resolution
    resolution_date: Mapped[Date | None] = mapped_column(Date)
    resolution_type: Mapped[str | None] = mapped_column(String(30))  # paid, settled, restructured, written_off

    # Amounts at case opening
    dpd_at_open: Mapped[int] = mapped_column(Integer)
    overdue_at_open: Mapped[float] = mapped_column(Numeric(18, 2))

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    loan_account = relationship("LoanAccount")
    actions: Mapped[list["CollectionAction"]] = relationship(
        "CollectionAction",
        back_populates="case",
        cascade="all, delete-orphan"
    )
    promises: Mapped[list["PromiseToPay"]] = relationship(
        "PromiseToPay",
        back_populates="case",
        cascade="all, delete-orphan"
    )


class CollectionAction(Base):
    """
    Action taken on a collection case.

    Action types: call, sms, email, letter, visit, legal_notice, etc.
    """
    __tablename__ = "collection_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("collection_cases.id", ondelete="CASCADE"),
        index=True
    )

    # Action details
    action_type: Mapped[str] = mapped_column(String(30), index=True)
    action_date: Mapped[DateTime] = mapped_column(DateTime, index=True)
    performed_by: Mapped[str] = mapped_column(String(100))

    # Outcome: contacted, no_answer, promise_to_pay, refused, wrong_number, etc.
    outcome: Mapped[str | None] = mapped_column(String(30))
    outcome_details: Mapped[str | None] = mapped_column(Text)

    # Follow-up
    next_action_date: Mapped[Date | None] = mapped_column(Date)
    next_action_type: Mapped[str | None] = mapped_column(String(30))

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    case: Mapped["CollectionCase"] = relationship(
        "CollectionCase",
        back_populates="actions"
    )


class PromiseToPay(Base):
    """
    Customer's promise to pay by a certain date.
    """
    __tablename__ = "promise_to_pay"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("collection_cases.id", ondelete="CASCADE"),
        index=True
    )

    # Promise details
    promise_date: Mapped[Date] = mapped_column(Date)  # Date promise was made
    payment_due_date: Mapped[Date] = mapped_column(Date)  # Date payment is promised
    promised_amount: Mapped[float] = mapped_column(Numeric(18, 2))

    # Actual payment
    actual_payment_date: Mapped[Date | None] = mapped_column(Date)
    actual_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))

    # Status: pending, kept, broken, partial
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    case: Mapped["CollectionCase"] = relationship(
        "CollectionCase",
        back_populates="promises"
    )


class EscalationRule(Base):
    """
    Rule for automatic escalation based on delinquency.
    """
    __tablename__ = "escalation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    # Trigger conditions
    trigger_dpd: Mapped[int | None] = mapped_column(Integer)  # DPD threshold
    trigger_bucket: Mapped[str | None] = mapped_column(String(20))  # Bucket threshold
    trigger_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))  # Min overdue amount

    # Action to take
    action_type: Mapped[str] = mapped_column(String(30))  # assign_queue, send_sms, send_email, etc.
    action_config: Mapped[str | None] = mapped_column(Text)  # JSON config for action

    # Rule settings
    priority: Mapped[int] = mapped_column(Integer, default=100)  # Lower = evaluated first
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    applies_to_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_products.id"),
        nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())
