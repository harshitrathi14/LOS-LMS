"""
Floating rate service for benchmark rate management and rate calculations.

Handles:
- Benchmark rate lookups
- Effective rate calculations (benchmark + spread with floor/cap)
- Rate reset processing
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.loan_account import LoanAccount

from app.models.benchmark_rate import BenchmarkRate, BenchmarkRateHistory

# Precision constant
RATE_PRECISION = Decimal("0.000001")


def _to_decimal(value: float | Decimal | int | None) -> Decimal:
    """Convert numeric value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def get_benchmark_rate(
    benchmark_id: int,
    as_of_date: date,
    db: Session
) -> BenchmarkRateHistory | None:
    """
    Get the benchmark rate effective on a given date.

    Returns the most recent rate entry on or before the specified date.

    Args:
        benchmark_id: Benchmark rate ID
        as_of_date: Date for which to get the rate
        db: Database session

    Returns:
        BenchmarkRateHistory record or None if not found
    """
    return db.query(BenchmarkRateHistory).filter(
        and_(
            BenchmarkRateHistory.benchmark_id == benchmark_id,
            BenchmarkRateHistory.effective_date <= as_of_date
        )
    ).order_by(desc(BenchmarkRateHistory.effective_date)).first()


def get_current_benchmark_rate(
    benchmark_id: int,
    as_of_date: date,
    db: Session
) -> Decimal:
    """
    Get the current benchmark rate value as a Decimal.

    Args:
        benchmark_id: Benchmark rate ID
        as_of_date: Date for which to get the rate
        db: Database session

    Returns:
        Rate value as Decimal, or 0 if not found

    Raises:
        ValueError: If benchmark rate not found
    """
    rate_entry = get_benchmark_rate(benchmark_id, as_of_date, db)
    if rate_entry is None:
        raise ValueError(
            f"No benchmark rate found for ID {benchmark_id} on or before {as_of_date}"
        )
    return _to_decimal(rate_entry.rate_value)


def calculate_effective_rate(
    loan_account: "LoanAccount",
    as_of_date: date,
    db: Session
) -> Decimal:
    """
    Calculate the effective interest rate for a loan account.

    For floating rate loans:
        effective_rate = benchmark_rate + spread
        With floor and cap adjustments if configured

    For fixed rate loans:
        Returns the fixed interest rate

    Args:
        loan_account: Loan account record
        as_of_date: Date for rate calculation
        db: Database session

    Returns:
        Effective annual interest rate as Decimal (percentage)
    """
    # Fixed rate: return as-is
    if loan_account.interest_rate_type == "fixed":
        return _to_decimal(loan_account.interest_rate)

    # Floating rate: benchmark + spread
    if not loan_account.benchmark_rate_id:
        # No benchmark configured, use base rate
        return _to_decimal(loan_account.interest_rate)

    # Get current benchmark rate
    benchmark_value = get_current_benchmark_rate(
        loan_account.benchmark_rate_id,
        as_of_date,
        db
    )

    # Add spread
    spread = _to_decimal(loan_account.spread) if loan_account.spread else Decimal("0")
    effective_rate = benchmark_value + spread

    # Apply floor if configured
    if loan_account.floor_rate is not None:
        floor = _to_decimal(loan_account.floor_rate)
        effective_rate = max(effective_rate, floor)

    # Apply cap if configured
    if loan_account.cap_rate is not None:
        cap = _to_decimal(loan_account.cap_rate)
        effective_rate = min(effective_rate, cap)

    return effective_rate.quantize(RATE_PRECISION)


def check_rate_reset_due(
    loan_account: "LoanAccount",
    as_of_date: date
) -> bool:
    """
    Check if a rate reset is due for the loan account.

    Args:
        loan_account: Loan account record
        as_of_date: Date to check against

    Returns:
        True if rate reset is due
    """
    if loan_account.interest_rate_type != "floating":
        return False

    if loan_account.next_rate_reset_date is None:
        return False

    return as_of_date >= loan_account.next_rate_reset_date


def calculate_next_reset_date(
    current_reset_date: date,
    reset_frequency: str
) -> date:
    """
    Calculate the next rate reset date based on frequency.

    Args:
        current_reset_date: Current/previous reset date
        reset_frequency: Reset frequency (monthly, quarterly, semiannual, annual)

    Returns:
        Next reset date
    """
    from app.services.frequency import add_period
    return add_period(current_reset_date, reset_frequency, 1)


def apply_rate_reset(
    loan_account: "LoanAccount",
    reset_date: date,
    db: Session
) -> dict:
    """
    Apply a rate reset to a floating rate loan.

    Updates the loan account with the new effective rate and
    calculates the next reset date.

    Args:
        loan_account: Loan account to reset
        reset_date: Date of the reset
        db: Database session

    Returns:
        Dictionary with old_rate, new_rate, next_reset_date
    """
    if loan_account.interest_rate_type != "floating":
        raise ValueError("Rate reset only applies to floating rate loans")

    old_rate = _to_decimal(loan_account.interest_rate)

    # Calculate new effective rate
    new_rate = calculate_effective_rate(loan_account, reset_date, db)

    # Update loan account
    loan_account.interest_rate = float(new_rate)

    # Calculate next reset date
    reset_frequency = loan_account.rate_reset_frequency or "monthly"
    next_reset = calculate_next_reset_date(reset_date, reset_frequency)
    loan_account.next_rate_reset_date = next_reset

    db.commit()
    db.refresh(loan_account)

    return {
        "old_rate": float(old_rate),
        "new_rate": float(new_rate),
        "reset_date": reset_date,
        "next_reset_date": next_reset,
    }


def get_rate_reset_schedule(
    loan_account: "LoanAccount",
    end_date: date
) -> list[date]:
    """
    Generate list of rate reset dates for a loan up to end_date.

    Args:
        loan_account: Loan account
        end_date: End date for the schedule

    Returns:
        List of reset dates
    """
    if loan_account.interest_rate_type != "floating":
        return []

    reset_dates = []
    current_date = loan_account.next_rate_reset_date or loan_account.start_date
    reset_frequency = loan_account.rate_reset_frequency or "monthly"

    while current_date <= end_date:
        reset_dates.append(current_date)
        current_date = calculate_next_reset_date(current_date, reset_frequency)

    return reset_dates


def get_benchmark_by_code(
    rate_code: str,
    db: Session
) -> BenchmarkRate | None:
    """Get a benchmark rate by its code."""
    return db.query(BenchmarkRate).filter(
        BenchmarkRate.rate_code == rate_code
    ).first()


def get_all_active_benchmarks(db: Session) -> list[BenchmarkRate]:
    """Get all active benchmark rates."""
    return db.query(BenchmarkRate).filter(
        BenchmarkRate.is_active == True
    ).all()


def add_benchmark_rate_value(
    benchmark_id: int,
    effective_date: date,
    rate_value: float,
    db: Session
) -> BenchmarkRateHistory:
    """
    Add a new rate value for a benchmark.

    Args:
        benchmark_id: Benchmark rate ID
        effective_date: Effective date of the rate
        rate_value: Rate value (as percentage)
        db: Database session

    Returns:
        Created BenchmarkRateHistory record
    """
    # Check if entry already exists for this date
    existing = db.query(BenchmarkRateHistory).filter(
        and_(
            BenchmarkRateHistory.benchmark_id == benchmark_id,
            BenchmarkRateHistory.effective_date == effective_date
        )
    ).first()

    if existing:
        # Update existing entry
        existing.rate_value = rate_value
        db.commit()
        db.refresh(existing)
        return existing

    # Create new entry
    history = BenchmarkRateHistory(
        benchmark_id=benchmark_id,
        effective_date=effective_date,
        rate_value=rate_value
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history
