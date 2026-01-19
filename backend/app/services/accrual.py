"""
Daily interest accrual service.

Handles:
- Daily interest accrual calculations
- Batch processing for all active loans
- Cumulative accrual tracking
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.loan_account import LoanAccount

from app.models.interest_accrual import InterestAccrual
from app.services.interest import days_in_year, calculate_daily_rate
from app.services.floating_rate import calculate_effective_rate, _to_decimal


ACCRUAL_PRECISION = Decimal("0.000001")
CENT = Decimal("0.01")


def get_latest_accrual(
    loan_account_id: int,
    db: Session
) -> InterestAccrual | None:
    """
    Get the most recent accrual record for a loan account.

    Args:
        loan_account_id: Loan account ID
        db: Database session

    Returns:
        Most recent InterestAccrual or None
    """
    return db.query(InterestAccrual).filter(
        InterestAccrual.loan_account_id == loan_account_id
    ).order_by(InterestAccrual.accrual_date.desc()).first()


def get_accrual_for_date(
    loan_account_id: int,
    accrual_date: date,
    db: Session
) -> InterestAccrual | None:
    """
    Get the accrual record for a specific date.

    Args:
        loan_account_id: Loan account ID
        accrual_date: Date to check
        db: Database session

    Returns:
        InterestAccrual for the date or None
    """
    return db.query(InterestAccrual).filter(
        and_(
            InterestAccrual.loan_account_id == loan_account_id,
            InterestAccrual.accrual_date == accrual_date
        )
    ).first()


def get_cumulative_accrual(
    loan_account_id: int,
    as_of_date: date,
    db: Session
) -> Decimal:
    """
    Get cumulative accrued interest for a loan account as of a date.

    Args:
        loan_account_id: Loan account ID
        as_of_date: Date up to which to sum accruals
        db: Database session

    Returns:
        Total accrued interest as Decimal
    """
    result = db.query(func.sum(InterestAccrual.accrued_amount)).filter(
        and_(
            InterestAccrual.loan_account_id == loan_account_id,
            InterestAccrual.accrual_date <= as_of_date,
            InterestAccrual.status == "accrued"
        )
    ).scalar()

    return _to_decimal(result or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def accrue_interest_daily(
    loan_account: "LoanAccount",
    accrual_date: date,
    db: Session
) -> InterestAccrual:
    """
    Accrue one day of interest for a loan account.

    Args:
        loan_account: Loan account to accrue for
        accrual_date: Date of accrual
        db: Database session

    Returns:
        Created InterestAccrual record
    """
    # Check if already accrued for this date
    existing = get_accrual_for_date(loan_account.id, accrual_date, db)
    if existing:
        return existing

    # Get outstanding principal
    principal = _to_decimal(loan_account.principal_outstanding)
    if principal <= 0:
        # No principal = no interest
        return _create_zero_accrual(loan_account, accrual_date, db)

    # Get effective rate (handles floating vs fixed)
    effective_rate = calculate_effective_rate(loan_account, accrual_date, db)

    # Get day count info
    convention = loan_account.day_count_convention or "act/365"
    year_days = days_in_year(accrual_date.year, convention)

    # Calculate daily rate
    daily_rate = _to_decimal(effective_rate) / Decimal("100") / Decimal(str(year_days))

    # Calculate daily accrual
    daily_accrual = principal * daily_rate

    # Get previous cumulative
    latest_accrual = get_latest_accrual(loan_account.id, db)
    prev_cumulative = _to_decimal(latest_accrual.cumulative_accrued) if latest_accrual else Decimal("0")
    new_cumulative = (prev_cumulative + daily_accrual).quantize(CENT, rounding=ROUND_HALF_UP)

    # Get benchmark and spread for floating rate loans
    benchmark_rate = None
    spread = None
    if loan_account.interest_rate_type == "floating" and loan_account.benchmark_rate_id:
        from app.services.floating_rate import get_current_benchmark_rate
        try:
            benchmark_rate = float(get_current_benchmark_rate(
                loan_account.benchmark_rate_id, accrual_date, db
            ))
        except ValueError:
            benchmark_rate = None
        spread = loan_account.spread

    # Create accrual record
    accrual = InterestAccrual(
        loan_account_id=loan_account.id,
        accrual_date=accrual_date,
        opening_balance=float(principal),
        interest_rate=float(effective_rate),
        benchmark_rate=benchmark_rate,
        spread=spread,
        accrued_amount=float(daily_accrual.quantize(ACCRUAL_PRECISION)),
        cumulative_accrued=float(new_cumulative),
        day_count_convention=convention,
        days_in_year=year_days,
        status="accrued"
    )

    db.add(accrual)
    db.commit()
    db.refresh(accrual)

    return accrual


def _create_zero_accrual(
    loan_account: "LoanAccount",
    accrual_date: date,
    db: Session
) -> InterestAccrual:
    """Create a zero-value accrual record."""
    latest = get_latest_accrual(loan_account.id, db)
    cumulative = _to_decimal(latest.cumulative_accrued) if latest else Decimal("0")

    accrual = InterestAccrual(
        loan_account_id=loan_account.id,
        accrual_date=accrual_date,
        opening_balance=float(loan_account.principal_outstanding),
        interest_rate=float(loan_account.interest_rate),
        benchmark_rate=None,
        spread=None,
        accrued_amount=0.0,
        cumulative_accrued=float(cumulative),
        day_count_convention=loan_account.day_count_convention or "act/365",
        days_in_year=365,
        status="accrued"
    )

    db.add(accrual)
    db.commit()
    db.refresh(accrual)

    return accrual


def run_daily_accrual_batch(
    as_of_date: date,
    db: Session
) -> dict:
    """
    Run daily interest accrual for all active loan accounts.

    Args:
        as_of_date: Date for which to run accruals
        db: Database session

    Returns:
        Dictionary with processing statistics
    """
    from app.models.loan_account import LoanAccount

    # Get all active loan accounts
    active_accounts = db.query(LoanAccount).filter(
        LoanAccount.status == "active"
    ).all()

    processed = 0
    skipped = 0
    errors = []

    for account in active_accounts:
        try:
            # Skip if disbursement is after accrual date
            if account.disbursed_at and account.disbursed_at.date() > as_of_date:
                skipped += 1
                continue

            # Skip if start date is after accrual date
            if account.start_date > as_of_date:
                skipped += 1
                continue

            accrue_interest_daily(account, as_of_date, db)
            processed += 1

        except Exception as e:
            errors.append({
                "account_id": account.id,
                "account_number": account.account_number,
                "error": str(e)
            })

    return {
        "as_of_date": as_of_date,
        "total_accounts": len(active_accounts),
        "processed": processed,
        "skipped": skipped,
        "errors": errors
    }


def run_accrual_for_date_range(
    loan_account_id: int,
    start_date: date,
    end_date: date,
    db: Session
) -> list[InterestAccrual]:
    """
    Run accruals for a date range (catch-up accruals).

    Args:
        loan_account_id: Loan account ID
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        db: Database session

    Returns:
        List of created InterestAccrual records
    """
    from app.models.loan_account import LoanAccount

    account = db.query(LoanAccount).filter(
        LoanAccount.id == loan_account_id
    ).first()

    if not account:
        raise ValueError(f"Loan account {loan_account_id} not found")

    accruals = []
    current_date = start_date

    while current_date <= end_date:
        accrual = accrue_interest_daily(account, current_date, db)
        accruals.append(accrual)
        current_date += timedelta(days=1)

    return accruals


def reset_cumulative_on_payment(
    loan_account_id: int,
    payment_date: date,
    interest_paid: Decimal,
    db: Session
) -> None:
    """
    Reset cumulative accrual tracking after interest payment.

    Called after a payment is applied to reset the cumulative counter.

    Args:
        loan_account_id: Loan account ID
        payment_date: Date of payment
        interest_paid: Amount of interest paid
        db: Database session
    """
    # Mark existing accruals as posted
    db.query(InterestAccrual).filter(
        and_(
            InterestAccrual.loan_account_id == loan_account_id,
            InterestAccrual.accrual_date <= payment_date,
            InterestAccrual.status == "accrued"
        )
    ).update({"status": "posted"})

    db.commit()


def get_accrual_summary(
    loan_account_id: int,
    period_start: date,
    period_end: date,
    db: Session
) -> dict:
    """
    Get accrual summary for a period.

    Args:
        loan_account_id: Loan account ID
        period_start: Period start date
        period_end: Period end date
        db: Database session

    Returns:
        Summary dictionary
    """
    accruals = db.query(InterestAccrual).filter(
        and_(
            InterestAccrual.loan_account_id == loan_account_id,
            InterestAccrual.accrual_date >= period_start,
            InterestAccrual.accrual_date <= period_end
        )
    ).order_by(InterestAccrual.accrual_date).all()

    if not accruals:
        return {
            "period_start": period_start,
            "period_end": period_end,
            "total_accrued": 0.0,
            "average_rate": 0.0,
            "days_count": 0,
        }

    total_accrued = sum(_to_decimal(a.accrued_amount) for a in accruals)
    avg_rate = sum(_to_decimal(a.interest_rate) for a in accruals) / len(accruals)

    return {
        "period_start": period_start,
        "period_end": period_end,
        "total_accrued": float(total_accrued.quantize(CENT)),
        "average_rate": float(avg_rate.quantize(Decimal("0.0001"))),
        "days_count": len(accruals),
        "opening_balance": accruals[0].opening_balance,
        "closing_balance": accruals[-1].opening_balance,
    }
