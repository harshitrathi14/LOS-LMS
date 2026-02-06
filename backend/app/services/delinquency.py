"""
Delinquency tracking service.

Handles:
- DPD bucket calculation
- Daily delinquency snapshots
- Portfolio delinquency reporting
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.loan_account import LoanAccount

from app.models.delinquency import DelinquencySnapshot
from app.models.repayment_schedule import RepaymentSchedule

CENT = Decimal("0.01")
NPA_TRIGGER_DPD = 90


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
    (61, 89, "61-89"),
    (90, 999999, "90+"),
]


def get_bucket_for_dpd(dpd: int) -> str:
    """
    Get the delinquency bucket for a given DPD.

    Args:
        dpd: Days past due

    Returns:
        Bucket string (current, 1-30, 31-60, 61-89, 90+)
    """
    for min_dpd, max_dpd, bucket_name in BUCKET_DEFINITIONS:
        if min_dpd <= dpd <= max_dpd:
            return bucket_name
    return "90+"


def get_dpd_classification(dpd: int, is_npa_flag: bool = False) -> str:
    """
    Classify an account based on DPD.

    Returns one of: standard, sma-0, sma-1, sma-2, npa
    """
    if is_npa_flag or dpd >= NPA_TRIGGER_DPD:
        return "npa"
    if dpd >= 61:
        return "sma-2"
    if dpd >= 31:
        return "sma-1"
    if dpd >= 1:
        return "sma-0"
    return "standard"


def is_npa(dpd: int) -> bool:
    """
    Check if a loan is NPA (Non-Performing Asset).

    By default, loans are considered NPA at 90+ DPD.
    """
    return dpd >= NPA_TRIGGER_DPD


def evaluate_npa_state(
    dpd: int,
    as_of_date: date,
    was_npa: bool,
    existing_npa_date: date | None
) -> dict[str, Any]:
    """
    Evaluate sticky RBI-style NPA state.

    Rule:
    - Account enters NPA when DPD reaches 90 or above.
    - Once in NPA, it stays NPA until DPD cures fully back to 0.
    """
    normalized_dpd = max(int(dpd), 0)
    is_npa_now = bool(was_npa)
    npa_date = existing_npa_date
    entered_npa = False
    exited_npa = False

    if normalized_dpd >= NPA_TRIGGER_DPD:
        if not is_npa_now:
            entered_npa = True
            npa_date = as_of_date
        elif npa_date is None:
            npa_date = as_of_date
        is_npa_now = True
    elif is_npa_now and normalized_dpd > 0:
        # Sticky behavior: remain NPA until full cure (DPD = 0)
        if npa_date is None:
            npa_date = as_of_date
        is_npa_now = True
    else:
        if is_npa_now and normalized_dpd == 0:
            exited_npa = True
        is_npa_now = False
        npa_date = None

    npa_category = None
    if is_npa_now and npa_date:
        npa_age_days = max((as_of_date - npa_date).days, 0)
        if npa_age_days < 365:
            npa_category = "substandard"
        elif npa_age_days < 1095:
            npa_category = "doubtful"
        else:
            npa_category = "loss"

    return {
        "is_npa": is_npa_now,
        "npa_date": npa_date,
        "npa_category": npa_category,
        "entered_npa": entered_npa,
        "exited_npa": exited_npa,
    }


def apply_delinquency_state(
    loan_account: "LoanAccount",
    dpd: int,
    as_of_date: date
) -> dict[str, Any]:
    """
    Apply delinquency and NPA state transitions to a loan account.
    """
    normalized_dpd = max(int(dpd), 0)
    loan_account.dpd = normalized_dpd

    npa_state = evaluate_npa_state(
        dpd=normalized_dpd,
        as_of_date=as_of_date,
        was_npa=bool(loan_account.is_npa),
        existing_npa_date=loan_account.npa_date
    )
    loan_account.is_npa = npa_state["is_npa"]
    loan_account.npa_date = npa_state["npa_date"]
    loan_account.npa_category = npa_state["npa_category"]

    # Do not override terminal statuses.
    if loan_account.status not in {"closed", "written_off"} and not loan_account.is_written_off:
        if loan_account.is_npa:
            loan_account.status = "npa"
        elif normalized_dpd > 0:
            loan_account.status = "delinquent"
        else:
            loan_account.status = "active"

    return {
        "dpd": normalized_dpd,
        "bucket": get_bucket_for_dpd(normalized_dpd),
        "dpd_classification": get_dpd_classification(
            normalized_dpd, bool(loan_account.is_npa)
        ),
        **npa_state,
    }


def calculate_delinquency_metrics(
    loan_account: "LoanAccount",
    as_of_date: date,
    db: Session
) -> dict:
    """
    Calculate comprehensive delinquency metrics for a loan.
    """
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
            "dpd_classification": "standard",
        }

    oldest_due_date = unpaid_items[0].due_date
    dpd = (as_of_date - oldest_due_date).days
    if dpd < 0:
        dpd = 0

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
    npa_flag = is_npa(dpd)

    return {
        "dpd": dpd,
        "bucket": get_bucket_for_dpd(dpd),
        "overdue_principal": float(overdue_principal.quantize(CENT)),
        "overdue_interest": float(overdue_interest.quantize(CENT)),
        "overdue_fees": float(overdue_fees.quantize(CENT)),
        "total_overdue": float(total_overdue),
        "missed_installments": len(unpaid_items),
        "oldest_due_date": oldest_due_date,
        "is_npa": npa_flag,
        "dpd_classification": get_dpd_classification(dpd, npa_flag),
    }


def create_delinquency_snapshot(
    loan_account: "LoanAccount",
    snapshot_date: date,
    db: Session
) -> DelinquencySnapshot:
    """
    Create or update a delinquency snapshot for a loan account.
    """
    existing = db.query(DelinquencySnapshot).filter(
        and_(
            DelinquencySnapshot.loan_account_id == loan_account.id,
            DelinquencySnapshot.snapshot_date == snapshot_date
        )
    ).first()

    metrics = calculate_delinquency_metrics(loan_account, snapshot_date, db)

    if existing:
        existing.dpd = metrics["dpd"]
        existing.bucket = metrics["bucket"]
        existing.overdue_principal = metrics["overdue_principal"]
        existing.overdue_interest = metrics["overdue_interest"]
        existing.overdue_fees = metrics["overdue_fees"]
        existing.total_overdue = metrics["total_overdue"]
        existing.principal_outstanding = float(loan_account.principal_outstanding)
        existing.missed_installments = metrics["missed_installments"]
        existing.oldest_due_date = metrics["oldest_due_date"]
        db.commit()
        db.refresh(existing)
        return existing

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
    Run daily delinquency snapshot and state updates.
    """
    from app.models.loan_account import LoanAccount

    active_accounts = db.query(LoanAccount).filter(
        LoanAccount.status.in_(["active", "delinquent", "npa"])
    ).all()

    processed = 0
    delinquent = 0
    npa = 0
    new_npa = 0
    errors = []

    for account in active_accounts:
        try:
            snapshot = create_delinquency_snapshot(account, snapshot_date, db)
            state = apply_delinquency_state(
                loan_account=account,
                dpd=snapshot.dpd,
                as_of_date=snapshot_date
            )
            db.commit()

            processed += 1
            if snapshot.dpd > 0:
                delinquent += 1
            if account.is_npa:
                npa += 1
            if state["entered_npa"]:
                new_npa += 1

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
        "new_npa_count": new_npa,
        "errors": errors
    }


def get_bucket_distribution(
    snapshot_date: date,
    db: Session,
    product_id: int | None = None
) -> dict:
    """
    Get delinquency bucket distribution for the portfolio.
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
