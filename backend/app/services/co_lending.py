"""
Co-lending service for payment splitting and partner share management.

Handles:
- Splitting payments to co-lending partners
- Recording disbursement splits
- Calculating partner shares
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import and_
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.loan_account import LoanAccount
    from app.models.payment import Payment
    from app.models.payment_allocation import PaymentAllocation

from app.models.loan_participation import LoanParticipation
from app.models.partner_ledger import PartnerLedgerEntry

CENT = Decimal("0.01")


def _to_decimal(value: float | Decimal | int | None) -> Decimal:
    """Convert numeric value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def get_participations_for_loan(
    loan_account_id: int,
    db: Session
) -> list[LoanParticipation]:
    """Get all active participations for a loan account."""
    return db.query(LoanParticipation).filter(
        and_(
            LoanParticipation.loan_account_id == loan_account_id,
            LoanParticipation.status == "active"
        )
    ).all()


def calculate_partner_share(
    loan_account_id: int,
    amount: Decimal,
    share_type: str,
    db: Session
) -> dict[int, Decimal]:
    """
    Calculate each partner's share of an amount.

    Args:
        loan_account_id: Loan account ID
        amount: Total amount to split
        share_type: "principal", "interest", or "fees"
        db: Database session

    Returns:
        Dictionary mapping partner_id to their share amount
    """
    participations = get_participations_for_loan(loan_account_id, db)

    if not participations:
        return {}

    shares: dict[int, Decimal] = {}
    total_allocated = Decimal("0")

    for i, participation in enumerate(participations):
        # Determine share percentage based on type
        if share_type == "fees" and participation.fee_share_percent is not None:
            share_pct = _to_decimal(participation.fee_share_percent)
        else:
            share_pct = _to_decimal(participation.share_percent)

        # Calculate share
        share = (amount * share_pct / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)

        # Last partner gets remainder to avoid rounding issues
        if i == len(participations) - 1:
            share = amount - total_allocated

        shares[participation.partner_id] = share
        total_allocated += share

    return shares


def split_payment_to_partners(
    payment: "Payment",
    allocations: list["PaymentAllocation"],
    db: Session
) -> list[PartnerLedgerEntry]:
    """
    Split a payment's allocations to co-lending partners.

    Creates ledger entries for each partner's share of principal,
    interest, and fees collected.

    Args:
        payment: Payment record
        allocations: Payment allocations to schedule items
        db: Database session

    Returns:
        List of created PartnerLedgerEntry records
    """
    loan_account_id = payment.loan_account_id
    participations = get_participations_for_loan(loan_account_id, db)

    if not participations:
        return []

    ledger_entries = []

    # Sum up total principal, interest, fees from allocations
    total_principal = sum(_to_decimal(a.principal_allocated) for a in allocations)
    total_interest = sum(_to_decimal(a.interest_allocated) for a in allocations)
    total_fees = sum(_to_decimal(a.fees_allocated) for a in allocations)

    # Calculate and record shares for each partner
    for participation in participations:
        # Get current running balance
        latest_entry = db.query(PartnerLedgerEntry).filter(
            PartnerLedgerEntry.participation_id == participation.id
        ).order_by(PartnerLedgerEntry.id.desc()).first()

        running_balance = _to_decimal(latest_entry.running_balance) if latest_entry else Decimal("0")

        # Principal share
        if total_principal > 0:
            principal_share = (total_principal * _to_decimal(participation.share_percent) / Decimal("100")).quantize(CENT)
            running_balance += principal_share

            entry = PartnerLedgerEntry(
                participation_id=participation.id,
                entry_type="principal_collection",
                entry_date=payment.paid_at.date() if payment.paid_at else date.today(),
                amount=float(principal_share),
                payment_id=payment.id,
                running_balance=float(running_balance),
                description=f"Principal collection from payment {payment.reference or payment.id}"
            )
            db.add(entry)
            ledger_entries.append(entry)

            # Update participation tracking
            participation.principal_collected = float(
                _to_decimal(participation.principal_collected or 0) + principal_share
            )

        # Interest share (may use different rate)
        if total_interest > 0:
            interest_share = (total_interest * _to_decimal(participation.share_percent) / Decimal("100")).quantize(CENT)
            running_balance += interest_share

            entry = PartnerLedgerEntry(
                participation_id=participation.id,
                entry_type="interest_collection",
                entry_date=payment.paid_at.date() if payment.paid_at else date.today(),
                amount=float(interest_share),
                payment_id=payment.id,
                running_balance=float(running_balance),
                description=f"Interest collection from payment {payment.reference or payment.id}"
            )
            db.add(entry)
            ledger_entries.append(entry)

            participation.interest_collected = float(
                _to_decimal(participation.interest_collected or 0) + interest_share
            )

        # Fees share
        if total_fees > 0:
            fee_pct = _to_decimal(participation.fee_share_percent or participation.share_percent)
            fee_share = (total_fees * fee_pct / Decimal("100")).quantize(CENT)
            running_balance += fee_share

            entry = PartnerLedgerEntry(
                participation_id=participation.id,
                entry_type="fee_collection",
                entry_date=payment.paid_at.date() if payment.paid_at else date.today(),
                amount=float(fee_share),
                payment_id=payment.id,
                running_balance=float(running_balance),
                description=f"Fee collection from payment {payment.reference or payment.id}"
            )
            db.add(entry)
            ledger_entries.append(entry)

            participation.fees_collected = float(
                _to_decimal(participation.fees_collected or 0) + fee_share
            )

    db.commit()

    for entry in ledger_entries:
        db.refresh(entry)

    return ledger_entries


def record_disbursement_split(
    loan_account: "LoanAccount",
    db: Session
) -> list[PartnerLedgerEntry]:
    """
    Record disbursement splits to co-lending partners.

    Creates ledger entries showing each partner's share of the disbursement.

    Args:
        loan_account: Loan account being disbursed
        db: Database session

    Returns:
        List of created PartnerLedgerEntry records
    """
    participations = get_participations_for_loan(loan_account.id, db)

    if not participations:
        return []

    principal = _to_decimal(loan_account.principal_amount)
    ledger_entries = []

    for participation in participations:
        share_pct = _to_decimal(participation.share_percent)
        disbursement_share = (principal * share_pct / Decimal("100")).quantize(CENT)

        entry = PartnerLedgerEntry(
            participation_id=participation.id,
            entry_type="disbursement",
            entry_date=loan_account.start_date,
            amount=float(-disbursement_share),  # Negative = owed by partner
            running_balance=float(-disbursement_share),
            description=f"Disbursement share for loan {loan_account.account_number}"
        )
        db.add(entry)
        ledger_entries.append(entry)

        # Update participation tracking
        participation.principal_disbursed = float(disbursement_share)

    db.commit()

    for entry in ledger_entries:
        db.refresh(entry)

    return ledger_entries


def get_partner_balance(
    partner_id: int,
    db: Session
) -> Decimal:
    """
    Get the current balance owed to a partner across all participations.

    Args:
        partner_id: Partner ID
        db: Database session

    Returns:
        Net balance (positive = owed to partner)
    """
    from sqlalchemy import func as sql_func

    # Get all participations for this partner
    participations = db.query(LoanParticipation).filter(
        LoanParticipation.partner_id == partner_id
    ).all()

    if not participations:
        return Decimal("0")

    total_balance = Decimal("0")

    for participation in participations:
        # Get latest ledger entry for running balance
        latest = db.query(PartnerLedgerEntry).filter(
            PartnerLedgerEntry.participation_id == participation.id
        ).order_by(PartnerLedgerEntry.id.desc()).first()

        if latest:
            total_balance += _to_decimal(latest.running_balance)

    return total_balance.quantize(CENT)


def get_partner_collections_summary(
    partner_id: int,
    start_date: date,
    end_date: date,
    db: Session
) -> dict:
    """
    Get collections summary for a partner over a period.

    Args:
        partner_id: Partner ID
        start_date: Period start date
        end_date: Period end date
        db: Database session

    Returns:
        Summary dictionary with principal, interest, fees collected
    """
    participations = db.query(LoanParticipation).filter(
        LoanParticipation.partner_id == partner_id
    ).all()

    participation_ids = [p.id for p in participations]

    if not participation_ids:
        return {
            "partner_id": partner_id,
            "period_start": start_date,
            "period_end": end_date,
            "principal_collected": 0.0,
            "interest_collected": 0.0,
            "fees_collected": 0.0,
            "total_collected": 0.0,
        }

    # Get ledger entries for the period
    entries = db.query(PartnerLedgerEntry).filter(
        and_(
            PartnerLedgerEntry.participation_id.in_(participation_ids),
            PartnerLedgerEntry.entry_date >= start_date,
            PartnerLedgerEntry.entry_date <= end_date,
            PartnerLedgerEntry.entry_type.in_(["principal_collection", "interest_collection", "fee_collection"])
        )
    ).all()

    principal = sum(_to_decimal(e.amount) for e in entries if e.entry_type == "principal_collection")
    interest = sum(_to_decimal(e.amount) for e in entries if e.entry_type == "interest_collection")
    fees = sum(_to_decimal(e.amount) for e in entries if e.entry_type == "fee_collection")

    return {
        "partner_id": partner_id,
        "period_start": start_date,
        "period_end": end_date,
        "principal_collected": float(principal),
        "interest_collected": float(interest),
        "fees_collected": float(fees),
        "total_collected": float(principal + interest + fees),
    }
