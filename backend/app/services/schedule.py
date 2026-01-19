"""
Amortization schedule generation service.

Generates repayment schedules for various loan types:
- EMI (Equated Monthly/Periodic Installment)
- Interest-only (pay interest each period, principal at end)
- Bullet (pay everything at maturity)

Supports:
- Multiple day-count conventions (30/360, ACT/365, ACT/ACT, ACT/360)
- Multiple payment frequencies (weekly, biweekly, monthly, quarterly, semiannual, annual)
- Business day adjustments via holiday calendars
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TypedDict

from sqlalchemy.orm import Session

from app.services.interest import (
    CENT,
    calculate_interest,
    calculate_emi,
    calculate_periodic_rate,
    year_fraction,
)
from app.services.frequency import (
    add_period,
    generate_due_dates,
    periods_per_year,
    calculate_tenure_periods,
    get_period_start_end,
    is_valid_frequency,
)
from app.services.calendar import (
    adjust_due_dates,
    AdjustmentType,
)


class ScheduleItem(TypedDict):
    """Type definition for a schedule item."""
    installment_number: int
    due_date: date
    period_start: date
    period_end: date
    principal_due: float
    interest_due: float
    fees_due: float
    total_due: float
    opening_balance: float
    closing_balance: float


def _to_decimal(value: float | Decimal | int) -> Decimal:
    """Convert numeric value to Decimal for precise calculations."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def generate_amortization_schedule(
    principal: float | Decimal,
    annual_rate: float | Decimal,
    tenure_months: int,
    start_date: date,
    schedule_type: str = "emi",
    repayment_frequency: str = "monthly",
    day_count_convention: str = "act/365",
    holiday_calendar_id: int | None = None,
    business_day_adjustment: AdjustmentType = "modified_following",
    db: Session | None = None,
) -> list[ScheduleItem]:
    """
    Generate an amortization schedule for a loan.

    Args:
        principal: Loan principal amount
        annual_rate: Annual interest rate as percentage (e.g., 12.5 for 12.5%)
        tenure_months: Loan tenure in months
        start_date: Loan disbursement/start date
        schedule_type: "emi", "interest_only", or "bullet"
        repayment_frequency: Payment frequency (weekly, biweekly, monthly, quarterly, etc.)
        day_count_convention: Day-count convention for interest calculation
        holiday_calendar_id: Optional holiday calendar for business day adjustment
        business_day_adjustment: How to adjust due dates for non-business days
        db: Database session (required if using holiday calendar)

    Returns:
        List of schedule items with payment details

    Raises:
        ValueError: If invalid parameters provided
    """
    # Validate inputs
    if tenure_months <= 0:
        raise ValueError("Tenure must be at least 1 month.")
    if principal <= 0:
        raise ValueError("Principal must be positive.")
    if not is_valid_frequency(repayment_frequency):
        raise ValueError(f"Unsupported repayment frequency: {repayment_frequency}")

    schedule_type = schedule_type.lower()
    if schedule_type not in {"emi", "interest_only", "bullet"}:
        raise ValueError(f"Unsupported schedule type: {schedule_type}")

    # Convert to Decimal for precision
    principal_dec = _to_decimal(principal)
    annual_rate_dec = _to_decimal(annual_rate)

    # Calculate number of installments based on frequency
    num_periods = calculate_tenure_periods(tenure_months, repayment_frequency)
    if num_periods <= 0:
        raise ValueError("Calculated periods must be positive.")

    # Generate raw due dates
    raw_due_dates = generate_due_dates(start_date, num_periods, repayment_frequency)

    # Adjust for business days if calendar provided
    if holiday_calendar_id and db:
        due_dates = adjust_due_dates(
            raw_due_dates,
            business_day_adjustment,
            holiday_calendar_id,
            db
        )
    else:
        due_dates = raw_due_dates

    # Calculate EMI if applicable
    ppy = periods_per_year(repayment_frequency)
    emi = Decimal("0")
    if schedule_type == "emi" and annual_rate_dec > 0:
        emi = calculate_emi(principal_dec, annual_rate_dec, num_periods, ppy)
    elif schedule_type == "emi" and annual_rate_dec == 0:
        # Zero interest - equal principal payments
        emi = (principal_dec / Decimal(str(num_periods))).quantize(CENT, rounding=ROUND_HALF_UP)

    # Build schedule
    schedule: list[ScheduleItem] = []
    balance = principal_dec
    period_start = start_date

    for i, due_date in enumerate(due_dates, start=1):
        installment_number = i
        period_end = due_date
        opening_balance = balance

        # Calculate interest for this period using day-count convention
        interest_due = calculate_interest(
            balance,
            annual_rate_dec,
            period_start,
            period_end,
            day_count_convention
        )

        # Determine principal component based on schedule type
        if schedule_type == "bullet":
            # Bullet: No principal until final installment
            if i == num_periods:
                principal_due = balance
            else:
                principal_due = Decimal("0.00")

        elif schedule_type == "interest_only":
            # Interest-only: Principal paid only at end
            if i == num_periods:
                principal_due = balance
            else:
                principal_due = Decimal("0.00")

        else:  # EMI
            if annual_rate_dec > 0:
                principal_due = (emi - interest_due).quantize(CENT, rounding=ROUND_HALF_UP)
            else:
                principal_due = emi

            # Adjust for rounding in final installment
            if i == num_periods:
                principal_due = balance
            elif principal_due > balance:
                principal_due = balance

        # Update balance
        balance -= principal_due
        if balance < 0:
            balance = Decimal("0")

        # Calculate total due
        total_due = (principal_due + interest_due).quantize(CENT, rounding=ROUND_HALF_UP)

        schedule.append({
            "installment_number": installment_number,
            "due_date": due_date,
            "period_start": period_start,
            "period_end": period_end,
            "principal_due": float(principal_due),
            "interest_due": float(interest_due),
            "fees_due": 0.0,
            "total_due": float(total_due),
            "opening_balance": float(opening_balance),
            "closing_balance": float(balance),
        })

        # Next period starts after this due date
        period_start = due_date

    return schedule


def generate_schedule_simple(
    principal: float | Decimal,
    annual_rate: float | Decimal,
    tenure_months: int,
    start_date: date,
    schedule_type: str = "emi",
) -> list[dict]:
    """
    Generate a simple monthly EMI schedule (backwards compatible).

    This is a simplified version that always uses:
    - Monthly frequency
    - ACT/365 day-count convention
    - No business day adjustments

    Args:
        principal: Loan principal amount
        annual_rate: Annual interest rate as percentage
        tenure_months: Loan tenure in months
        start_date: Loan start date
        schedule_type: "emi", "interest_only", or "bullet"

    Returns:
        List of schedule items (simplified format for backwards compatibility)
    """
    full_schedule = generate_amortization_schedule(
        principal=principal,
        annual_rate=annual_rate,
        tenure_months=tenure_months,
        start_date=start_date,
        schedule_type=schedule_type,
        repayment_frequency="monthly",
        day_count_convention="act/365",
    )

    # Return simplified format for backwards compatibility
    return [
        {
            "installment_number": item["installment_number"],
            "due_date": item["due_date"],
            "principal_due": item["principal_due"],
            "interest_due": item["interest_due"],
            "fees_due": item["fees_due"],
            "total_due": item["total_due"],
        }
        for item in full_schedule
    ]


def recalculate_schedule_from_installment(
    existing_schedule: list[dict],
    from_installment: int,
    outstanding_principal: float | Decimal,
    annual_rate: float | Decimal,
    repayment_frequency: str = "monthly",
    day_count_convention: str = "act/365",
    schedule_type: str = "emi",
) -> list[dict]:
    """
    Recalculate remaining schedule from a specific installment.

    Useful for:
    - Rate resets on floating rate loans
    - Partial prepayments with EMI recalculation
    - Restructuring

    Args:
        existing_schedule: Current schedule
        from_installment: Installment number to recalculate from
        outstanding_principal: Principal balance at recalculation point
        annual_rate: New annual rate
        repayment_frequency: Payment frequency
        day_count_convention: Day-count convention
        schedule_type: Schedule type

    Returns:
        New schedule starting from the specified installment
    """
    if from_installment < 1 or from_installment > len(existing_schedule):
        raise ValueError(f"Invalid installment number: {from_installment}")

    principal_dec = _to_decimal(outstanding_principal)
    annual_rate_dec = _to_decimal(annual_rate)

    # Get the start date for recalculation (previous installment's due date)
    if from_installment == 1:
        # Need to derive start date from first installment
        first_item = existing_schedule[0]
        start_date = add_period(first_item["due_date"], repayment_frequency, -1)
    else:
        start_date = existing_schedule[from_installment - 2]["due_date"]

    # Calculate remaining periods
    remaining_periods = len(existing_schedule) - from_installment + 1

    # Generate new schedule for remaining periods
    new_schedule = generate_amortization_schedule(
        principal=principal_dec,
        annual_rate=annual_rate_dec,
        tenure_months=remaining_periods,  # Will be converted to periods
        start_date=start_date,
        schedule_type=schedule_type,
        repayment_frequency=repayment_frequency,
        day_count_convention=day_count_convention,
    )

    # Adjust installment numbers
    for i, item in enumerate(new_schedule):
        item["installment_number"] = from_installment + i

    return new_schedule


def calculate_total_interest(schedule: list[dict]) -> Decimal:
    """Calculate total interest payable over the loan term."""
    return sum(
        _to_decimal(item["interest_due"])
        for item in schedule
    ).quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_total_payment(schedule: list[dict]) -> Decimal:
    """Calculate total payment (principal + interest + fees) over the loan term."""
    return sum(
        _to_decimal(item["total_due"])
        for item in schedule
    ).quantize(CENT, rounding=ROUND_HALF_UP)


# Backward compatibility alias
add_months = add_period
