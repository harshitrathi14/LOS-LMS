"""
Settlement service for partner settlement generation.

Handles:
- Generating settlement batches
- Settlement approval workflow
- Settlement payment tracking
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.loan_participation import LoanParticipation
from app.models.partner_ledger import (
    PartnerLedgerEntry,
    PartnerSettlement,
    PartnerSettlementDetail,
)
from app.services.co_lending import get_partner_collections_summary, _to_decimal

CENT = Decimal("0.01")


def generate_settlement(
    partner_id: int,
    period_start: date,
    period_end: date,
    db: Session
) -> PartnerSettlement:
    """
    Generate a settlement for a partner for a given period.

    Aggregates all collections during the period and creates a settlement.

    Args:
        partner_id: Partner ID
        period_start: Period start date
        period_end: Period end date
        db: Database session

    Returns:
        Created PartnerSettlement record
    """
    # Get participations for this partner
    participations = db.query(LoanParticipation).filter(
        LoanParticipation.partner_id == partner_id
    ).all()

    if not participations:
        raise ValueError(f"No participations found for partner {partner_id}")

    participation_ids = [p.id for p in participations]

    # Get unsettled ledger entries for the period
    entries = db.query(PartnerLedgerEntry).filter(
        and_(
            PartnerLedgerEntry.participation_id.in_(participation_ids),
            PartnerLedgerEntry.entry_date >= period_start,
            PartnerLedgerEntry.entry_date <= period_end,
            PartnerLedgerEntry.settlement_id.is_(None),
            PartnerLedgerEntry.entry_type.in_([
                "principal_collection",
                "interest_collection",
                "fee_collection",
                "adjustment"
            ])
        )
    ).all()

    if not entries:
        raise ValueError(f"No unsettled entries found for partner {partner_id} in period")

    # Calculate totals
    total_principal = sum(
        _to_decimal(e.amount) for e in entries
        if e.entry_type == "principal_collection"
    )
    total_interest = sum(
        _to_decimal(e.amount) for e in entries
        if e.entry_type == "interest_collection"
    )
    total_fees = sum(
        _to_decimal(e.amount) for e in entries
        if e.entry_type == "fee_collection"
    )
    total_adjustments = sum(
        _to_decimal(e.amount) for e in entries
        if e.entry_type == "adjustment"
    )

    net_amount = (total_principal + total_interest + total_fees + total_adjustments).quantize(CENT)

    # Create settlement
    settlement = PartnerSettlement(
        partner_id=partner_id,
        settlement_date=date.today(),
        period_start=period_start,
        period_end=period_end,
        total_principal=float(total_principal),
        total_interest=float(total_interest),
        total_fees=float(total_fees),
        total_adjustments=float(total_adjustments),
        net_amount=float(net_amount),
        status="pending"
    )
    db.add(settlement)
    db.flush()  # Get the settlement ID

    # Create settlement details per loan account
    loan_account_totals: dict[int, dict] = {}
    for entry in entries:
        participation = db.query(LoanParticipation).filter(
            LoanParticipation.id == entry.participation_id
        ).first()

        loan_account_id = participation.loan_account_id
        if loan_account_id not in loan_account_totals:
            loan_account_totals[loan_account_id] = {
                "principal": Decimal("0"),
                "interest": Decimal("0"),
                "fees": Decimal("0"),
                "share_percent": participation.share_percent,
            }

        amount = _to_decimal(entry.amount)
        if entry.entry_type == "principal_collection":
            loan_account_totals[loan_account_id]["principal"] += amount
        elif entry.entry_type == "interest_collection":
            loan_account_totals[loan_account_id]["interest"] += amount
        elif entry.entry_type == "fee_collection":
            loan_account_totals[loan_account_id]["fees"] += amount

    for loan_account_id, totals in loan_account_totals.items():
        detail = PartnerSettlementDetail(
            settlement_id=settlement.id,
            loan_account_id=loan_account_id,
            principal_share=float(totals["principal"]),
            interest_share=float(totals["interest"]),
            fee_share=float(totals["fees"]),
            total_share=float(totals["principal"] + totals["interest"] + totals["fees"]),
            share_percent=totals["share_percent"]
        )
        db.add(detail)

    # Link entries to settlement
    for entry in entries:
        entry.settlement_id = settlement.id

    db.commit()
    db.refresh(settlement)

    return settlement


def approve_settlement(
    settlement_id: int,
    db: Session
) -> PartnerSettlement:
    """
    Approve a settlement for payment.

    Args:
        settlement_id: Settlement ID
        db: Database session

    Returns:
        Updated PartnerSettlement record
    """
    settlement = db.query(PartnerSettlement).filter(
        PartnerSettlement.id == settlement_id
    ).first()

    if not settlement:
        raise ValueError(f"Settlement {settlement_id} not found")

    if settlement.status != "pending":
        raise ValueError(f"Settlement {settlement_id} is not pending")

    settlement.status = "approved"
    db.commit()
    db.refresh(settlement)

    return settlement


def mark_settlement_paid(
    settlement_id: int,
    payment_reference: str,
    payment_date: date,
    payment_mode: str,
    db: Session
) -> PartnerSettlement:
    """
    Mark a settlement as paid.

    Args:
        settlement_id: Settlement ID
        payment_reference: Payment reference number
        payment_date: Date of payment
        payment_mode: Payment mode (NEFT, RTGS, etc.)
        db: Database session

    Returns:
        Updated PartnerSettlement record
    """
    settlement = db.query(PartnerSettlement).filter(
        PartnerSettlement.id == settlement_id
    ).first()

    if not settlement:
        raise ValueError(f"Settlement {settlement_id} not found")

    if settlement.status not in ["pending", "approved"]:
        raise ValueError(f"Settlement {settlement_id} cannot be marked as paid")

    settlement.status = "paid"
    settlement.payment_reference = payment_reference
    settlement.payment_date = payment_date
    settlement.payment_mode = payment_mode

    # Create ledger entries for the settlement
    for detail in settlement.details:
        participation = db.query(LoanParticipation).filter(
            and_(
                LoanParticipation.loan_account_id == detail.loan_account_id,
                LoanParticipation.partner_id == settlement.partner_id
            )
        ).first()

        if participation:
            latest_entry = db.query(PartnerLedgerEntry).filter(
                PartnerLedgerEntry.participation_id == participation.id
            ).order_by(PartnerLedgerEntry.id.desc()).first()

            running_balance = _to_decimal(latest_entry.running_balance) if latest_entry else Decimal("0")
            running_balance -= _to_decimal(detail.total_share)

            entry = PartnerLedgerEntry(
                participation_id=participation.id,
                entry_type="settlement",
                entry_date=payment_date,
                amount=float(-_to_decimal(detail.total_share)),  # Negative = paid out
                settlement_id=settlement.id,
                running_balance=float(running_balance),
                description=f"Settlement payment - Ref: {payment_reference}"
            )
            db.add(entry)

    db.commit()
    db.refresh(settlement)

    return settlement


def cancel_settlement(
    settlement_id: int,
    reason: str,
    db: Session
) -> PartnerSettlement:
    """
    Cancel a settlement.

    Args:
        settlement_id: Settlement ID
        reason: Cancellation reason
        db: Database session

    Returns:
        Updated PartnerSettlement record
    """
    settlement = db.query(PartnerSettlement).filter(
        PartnerSettlement.id == settlement_id
    ).first()

    if not settlement:
        raise ValueError(f"Settlement {settlement_id} not found")

    if settlement.status == "paid":
        raise ValueError(f"Cannot cancel paid settlement {settlement_id}")

    # Unlink ledger entries
    db.query(PartnerLedgerEntry).filter(
        PartnerLedgerEntry.settlement_id == settlement_id
    ).update({"settlement_id": None})

    settlement.status = "cancelled"
    settlement.notes = reason

    db.commit()
    db.refresh(settlement)

    return settlement


def get_pending_settlements(
    partner_id: int | None,
    db: Session
) -> list[PartnerSettlement]:
    """Get all pending settlements, optionally filtered by partner."""
    query = db.query(PartnerSettlement).filter(
        PartnerSettlement.status == "pending"
    )
    if partner_id:
        query = query.filter(PartnerSettlement.partner_id == partner_id)
    return query.order_by(PartnerSettlement.settlement_date).all()
