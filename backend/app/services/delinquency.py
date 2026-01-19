"""
Delinquency tracking service.

Handles:
- DPD bucket calculation
- Daily delinquency snapshots
- Portfolio delinquency reporting
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import and_
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.loan_account import LoanAccount

from app.models.delinquency import DelinquencySnapshot
from app.models.repayment_schedule import RepaymentSchedule

CENT = Decimal("0.01")


def _to_decimal(value: float | Decimal | int | None) -> Decimal:
    """Convert numeric value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


# Delinquency bucket definitions
BUCKET_DEFINITIONS = [
    (0, 0, "current"),
    (1, 30, "1-30"),
    (31, 60, "31-60"),
    (61, 90, "61-90"),
    (91, 999999, "90+"),
]


def get_bucket_for_dpd(dpd: int) -> str:
    """
    Get the delinquency bucket for a given DPD.

    Args:
        dpd: Days past due

    Returns:
        Bucket string (current, 1-30, 31-60, 61-90, 90+)
    """
    for min_dpd, max_dpd, bucket_name in BUCKET_DEFINITIONS:
        if min_dpd <= dpd <= max_dpd:
            return bucket_name
    return "90+"


def is_npa(dpd: int) -> bool:
    """
    Check if a loan is NPA (Non-Performing Asset).

    By default, loans are considered NPA at 90+ DPD.

    Args:
        dpd: Days past due

    Returns:
        True if NPA
    """
    return dpd >= 90


def calculate_delinquency_metrics(
    loan_account: "LoanAccount",
    as_of_date: date,
    db: Session
) -> dict:
    """
    Calculate comprehensive delinquency metrics for a loan.

    Args:
        loan_account: Loan account
        as_of_date: Date for calculation
        db: Database session

    Returns:
        Dictionary with delinquency metrics
    """
    # Get unpaid schedule items
    unpaid_items = db.query(RepaymentSchedule).filter(
        and_(
            RepaymentSchedule.loan_account_id == loan_account.id,
            RepaymentSchedule.status.in_(["pending", "partial"]),
            RepaymentSchedule.due_date <= as_of_date
        )
    ).order_by(RepaymentSchedule.due_date).all()

    if not unpaid_items:
        return {
            "dpd": 0,
            "bucket": "current",
            "overdue_principal": 0.0,
            "overdue_interest": 0.0,
            "overdue_fees": 0.0,
            "total_overdue": 0.0,
            "missed_installments": 0,
            "oldest_due_date": None,
            "is_npa": False,
        }

    # Calculate DPD from oldest unpaid
    oldest_due_date = unpaid_items[0].due_date
    dpd = (as_of_date - oldest_due_date).days
    if dpd < 0:
        dpd = 0

    # Calculate overdue amounts
    overdue_principal = Decimal("0")
    overdue_interest = Decimal("0")
    overdue_fees = Decimal("0")

    for item in unpaid_items:
        principal_remaining = _to_decimal(item.principal_due) - _to_decimal(item.principal_paid or 0)
        interest_remaining = _to_decimal(item.interest_due) - _to_decimal(item.interest_paid or 0)
        fees_remaining = _to_decimal(item.fees_due or 0) - _to_decimal(item.fees_paid or 0)

        overdue_principal += max(Decimal("0"), principal_remaining)
        overdue_interest += max(Decimal("0"), interest_remaining)
        overdue_fees += max(Decimal("0"), fees_remaining)

    total_overdue = (overdue_principal + overdue_interest + overdue_fees).quantize(CENT)

    return {
        "dpd": dpd,
        "bucket": get_bucket_for_dpd(dpd),
        "overdue_principal": float(overdue_principal.quantize(CENT)),
        "overdue_interest": float(overdue_interest.quantize(CENT)),
        "overdue_fees": float(overdue_fees.quantize(CENT)),
        "total_overdue": float(total_overdue),
        "missed_installments": len(unpaid_items),
        "oldest_due_date": oldest_due_date,
        "is_npa": is_npa(dpd),
    }


def create_delinquency_snapshot(
    loan_account: "LoanAccount",
    snapshot_date: date,
    db: Session
) -> DelinquencySnapshot:
    """
    Create a delinquency snapshot for a loan account.

    Args:
        loan_account: Loan account
        snapshot_date: Date of snapshot
        db: Database session

    Returns:
        Created DelinquencySnapshot record
    """
    # Check for existing snapshot
    existing = db.query(DelinquencySnapshot).filter(
        and_(
            DelinquencySnapshot.loan_account_id == loan_account.id,
            DelinquencySnapshot.snapshot_date == snapshot_date
        )
    ).first()

    if existing:
        return existing  # Don't duplicate

    metrics = calculate_delinquency_metrics(loan_account, snapshot_date, db)

    snapshot = DelinquencySnapshot(
        loan_account_id=loan_account.id,
        snapshot_date=snapshot_date,
        dpd=metrics["dpd"],
        bucket=metrics["bucket"],
        overdue_principal=metrics["overdue_principal"],
        overdue_interest=metrics["overdue_interest"],
        overdue_fees=metrics["overdue_fees"],
        total_overdue=metrics["total_overdue"],
        principal_outstanding=float(loan_account.principal_outstanding),
        missed_installments=metrics["missed_installments"],
        oldest_due_date=metrics["oldest_due_date"]
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return snapshot


def run_daily_delinquency_batch(
    snapshot_date: date,
    db: Session
) -> dict:
    """
    Run daily delinquency snapshot for all active loans.

    Args:
        snapshot_date: Date for snapshots
        db: Database session

    Returns:
        Processing statistics
    """
    from app.models.loan_account import LoanAccount

    active_accounts = db.query(LoanAccount).filter(
        LoanAccount.status == "active"
    ).all()

    processed = 0
    delinquent = 0
    npa = 0
    errors = []

    for account in active_accounts:
        try:
            snapshot = create_delinquency_snapshot(account, snapshot_date, db)

            # Update loan account DPD
            account.dpd = snapshot.dpd
            db.commit()

            processed += 1
            if snapshot.dpd > 0:
                delinquent += 1
            if snapshot.dpd >= 90:
                npa += 1

        except Exception as e:
            errors.append({
                "account_id": account.id,
                "account_number": account.account_number,
                "error": str(e)
            })

    return {
        "snapshot_date": snapshot_date,
        "total_processed": processed,
        "delinquent_count": delinquent,
        "npa_count": npa,
        "errors": errors
    }


def get_bucket_distribution(
    snapshot_date: date,
    db: Session,
    product_id: int | None = None
) -> dict:
    """
    Get delinquency bucket distribution for the portfolio.

    Args:
        snapshot_date: Date for analysis
        db: Database session
        product_id: Optional product filter

    Returns:
        Distribution by bucket
    """
    from sqlalchemy import func as sql_func
    from app.models.loan_account import LoanAccount

    query = db.query(
        DelinquencySnapshot.bucket,
        sql_func.count(DelinquencySnapshot.id).label("count"),
        sql_func.sum(DelinquencySnapshot.principal_outstanding).label("principal"),
        sql_func.sum(DelinquencySnapshot.total_overdue).label("overdue")
    ).filter(
        DelinquencySnapshot.snapshot_date == snapshot_date
    )

    if product_id:
        query = query.join(LoanAccount).filter(
            LoanAccount.application.has(product_id=product_id)
        )

    query = query.group_by(DelinquencySnapshot.bucket)

    results = query.all()

    distribution = {}
    for row in results:
        distribution[row.bucket] = {
            "count": row.count,
            "principal_outstanding": float(row.principal or 0),
            "total_overdue": float(row.overdue or 0),
        }

    return distribution


def get_delinquency_trend(
    loan_account_id: int,
    start_date: date,
    end_date: date,
    db: Session
) -> list[dict]:
    """
    Get delinquency trend for a loan over time.

    Args:
        loan_account_id: Loan account ID
        start_date: Start date
        end_date: End date
        db: Database session

    Returns:
        List of daily snapshots
    """
    snapshots = db.query(DelinquencySnapshot).filter(
        and_(
            DelinquencySnapshot.loan_account_id == loan_account_id,
            DelinquencySnapshot.snapshot_date >= start_date,
            DelinquencySnapshot.snapshot_date <= end_date
        )
    ).order_by(DelinquencySnapshot.snapshot_date).all()

    return [
        {
            "date": s.snapshot_date,
            "dpd": s.dpd,
            "bucket": s.bucket,
            "total_overdue": s.total_overdue,
        }
        for s in snapshots
    ]
