"""
Advanced schedule generation service.

Supports:
- Step-up EMI (increasing payments over time)
- Step-down EMI (decreasing payments over time)
- Moratorium periods (full, principal-only, interest-only)
- Balloon payments
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TypedDict

from app.services.interest import calculate_emi, calculate_interest, CENT
from app.services.frequency import (
    add_period,
    generate_due_dates,
    periods_per_year,
    calculate_tenure_periods,
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
    is_moratorium: bool
    step_number: int


def _to_decimal(value: float | Decimal | int | None) -> Decimal:
    """Convert numeric value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def generate_step_up_schedule(
    principal: float | Decimal,
    annual_rate: float | Decimal,
    tenure_months: int,
    start_date: date,
    step_percent: float | Decimal,
    step_frequency_months: int,
    repayment_frequency: str = "monthly",
    day_count_convention: str = "act/365",
    step_count: int | None = None
) -> list[ScheduleItem]:
    """
    Generate a step-up EMI schedule where EMI increases periodically.

    Args:
        principal: Loan principal amount
        annual_rate: Annual interest rate (percentage)
        tenure_months: Total loan tenure in months
        start_date: Loan start date
        step_percent: Percentage increase at each step
        step_frequency_months: Months between step increases
        repayment_frequency: Payment frequency
        day_count_convention: Day count convention
        step_count: Maximum number of steps (None for continuous)

    Returns:
        List of schedule items
    """
    principal_dec = _to_decimal(principal)
    annual_rate_dec = _to_decimal(annual_rate)
    step_pct = _to_decimal(step_percent)

    num_periods = calculate_tenure_periods(tenure_months, repayment_frequency)
    step_freq_periods = calculate_tenure_periods(step_frequency_months, repayment_frequency)
    ppy = periods_per_year(repayment_frequency)

    # Generate due dates
    due_dates = generate_due_dates(start_date, num_periods, repayment_frequency)

    # Calculate base EMI for first step
    # For step-up, we need to solve for a base EMI that will pay off the loan
    # This is complex, so we use an approximation approach
    base_emi = calculate_emi(principal_dec, annual_rate_dec, num_periods, ppy)

    # Adjust base EMI down since it will increase
    # Rough approximation: reduce by average step effect
    effective_steps = step_count or ((num_periods - 1) // step_freq_periods + 1)
    avg_multiplier = Decimal("1") + (step_pct / Decimal("100")) * Decimal(str(effective_steps / 2))
    adjusted_base = (base_emi / avg_multiplier).quantize(CENT, rounding=ROUND_HALF_UP)

    schedule: list[ScheduleItem] = []
    balance = principal_dec
    period_start = start_date
    current_step = 0
    current_emi = adjusted_base

    for i, due_date in enumerate(due_dates, start=1):
        period_end = due_date

        # Check if we should step up
        if i > 1 and (i - 1) % step_freq_periods == 0:
            if step_count is None or current_step < step_count:
                current_step += 1
                current_emi = (current_emi * (Decimal("1") + step_pct / Decimal("100"))).quantize(
                    CENT, rounding=ROUND_HALF_UP
                )

        # Calculate interest
        interest_due = calculate_interest(
            balance, annual_rate_dec, period_start, period_end, day_count_convention
        )

        # Calculate principal (EMI - interest)
        principal_due = (current_emi - interest_due).quantize(CENT, rounding=ROUND_HALF_UP)

        # Final installment adjustment
        if i == num_periods:
            principal_due = balance

        if principal_due > balance:
            principal_due = balance

        balance -= principal_due
        if balance < 0:
            balance = Decimal("0")

        total_due = (principal_due + interest_due).quantize(CENT)

        schedule.append({
            "installment_number": i,
            "due_date": due_date,
            "period_start": period_start,
            "period_end": period_end,
            "principal_due": float(principal_due),
            "interest_due": float(interest_due),
            "fees_due": 0.0,
            "total_due": float(total_due),
            "opening_balance": float(balance + principal_due),
            "closing_balance": float(balance),
            "is_moratorium": False,
            "step_number": current_step,
        })

        period_start = due_date

    return schedule


def generate_step_down_schedule(
    principal: float | Decimal,
    annual_rate: float | Decimal,
    tenure_months: int,
    start_date: date,
    step_percent: float | Decimal,
    step_frequency_months: int,
    repayment_frequency: str = "monthly",
    day_count_convention: str = "act/365",
    step_count: int | None = None
) -> list[ScheduleItem]:
    """
    Generate a step-down EMI schedule where EMI decreases periodically.

    Args:
        principal: Loan principal amount
        annual_rate: Annual interest rate (percentage)
        tenure_months: Total loan tenure in months
        start_date: Loan start date
        step_percent: Percentage decrease at each step
        step_frequency_months: Months between step decreases
        repayment_frequency: Payment frequency
        day_count_convention: Day count convention
        step_count: Maximum number of steps (None for continuous)

    Returns:
        List of schedule items
    """
    principal_dec = _to_decimal(principal)
    annual_rate_dec = _to_decimal(annual_rate)
    step_pct = _to_decimal(step_percent)

    num_periods = calculate_tenure_periods(tenure_months, repayment_frequency)
    step_freq_periods = calculate_tenure_periods(step_frequency_months, repayment_frequency)
    ppy = periods_per_year(repayment_frequency)

    due_dates = generate_due_dates(start_date, num_periods, repayment_frequency)

    # Calculate starting EMI (higher than normal since it will decrease)
    base_emi = calculate_emi(principal_dec, annual_rate_dec, num_periods, ppy)
    effective_steps = step_count or ((num_periods - 1) // step_freq_periods + 1)
    avg_multiplier = Decimal("1") - (step_pct / Decimal("100")) * Decimal(str(effective_steps / 2))
    adjusted_base = (base_emi / avg_multiplier).quantize(CENT, rounding=ROUND_HALF_UP)

    schedule: list[ScheduleItem] = []
    balance = principal_dec
    period_start = start_date
    current_step = 0
    current_emi = adjusted_base

    for i, due_date in enumerate(due_dates, start=1):
        period_end = due_date

        # Check if we should step down
        if i > 1 and (i - 1) % step_freq_periods == 0:
            if step_count is None or current_step < step_count:
                current_step += 1
                current_emi = (current_emi * (Decimal("1") - step_pct / Decimal("100"))).quantize(
                    CENT, rounding=ROUND_HALF_UP
                )

        interest_due = calculate_interest(
            balance, annual_rate_dec, period_start, period_end, day_count_convention
        )

        principal_due = (current_emi - interest_due).quantize(CENT, rounding=ROUND_HALF_UP)

        if i == num_periods:
            principal_due = balance

        if principal_due > balance:
            principal_due = balance
        if principal_due < 0:
            principal_due = Decimal("0")

        balance -= principal_due
        if balance < 0:
            balance = Decimal("0")

        total_due = (principal_due + interest_due).quantize(CENT)

        schedule.append({
            "installment_number": i,
            "due_date": due_date,
            "period_start": period_start,
            "period_end": period_end,
            "principal_due": float(principal_due),
            "interest_due": float(interest_due),
            "fees_due": 0.0,
            "total_due": float(total_due),
            "opening_balance": float(balance + principal_due),
            "closing_balance": float(balance),
            "is_moratorium": False,
            "step_number": current_step,
        })

        period_start = due_date

    return schedule


def apply_moratorium(
    schedule: list[dict],
    moratorium_months: int,
    moratorium_type: str,
    interest_treatment: str = "capitalize",
    principal_start_date: date | None = None
) -> list[dict]:
    """
    Apply moratorium to an existing schedule.

    Args:
        schedule: Existing repayment schedule
        moratorium_months: Number of moratorium months
        moratorium_type: "full", "principal_only", or "interest_only"
        interest_treatment: How to handle interest during moratorium
            - "capitalize": Add to principal
            - "accrue": Track separately (not added to principal)
            - "waive": No interest during moratorium
        principal_start_date: Date when principal payments start (for adjusting)

    Returns:
        Modified schedule with moratorium applied
    """
    if moratorium_months <= 0:
        return schedule

    modified_schedule = []
    capitalized_interest = Decimal("0")

    for i, item in enumerate(schedule):
        new_item = item.copy()

        if i < moratorium_months:
            # Moratorium period
            new_item["is_moratorium"] = True

            if moratorium_type == "full":
                # No payment at all
                if interest_treatment == "capitalize":
                    capitalized_interest += _to_decimal(item["interest_due"])
                elif interest_treatment == "waive":
                    new_item["interest_due"] = 0.0

                new_item["principal_due"] = 0.0
                new_item["total_due"] = 0.0 if interest_treatment != "accrue" else item["interest_due"]

            elif moratorium_type == "principal_only":
                # Pay interest only
                new_item["principal_due"] = 0.0
                new_item["total_due"] = item["interest_due"]

            elif moratorium_type == "interest_only":
                # Pay principal only (unusual)
                new_item["interest_due"] = 0.0
                new_item["total_due"] = item["principal_due"]

        else:
            new_item["is_moratorium"] = False

            # Add capitalized interest to first post-moratorium payment
            if i == moratorium_months and capitalized_interest > 0:
                new_item["opening_balance"] = float(
                    _to_decimal(item["opening_balance"]) + capitalized_interest
                )

        modified_schedule.append(new_item)

    return modified_schedule


def generate_balloon_schedule(
    principal: float | Decimal,
    annual_rate: float | Decimal,
    tenure_months: int,
    start_date: date,
    balloon_percent: float | Decimal | None = None,
    balloon_amount: float | Decimal | None = None,
    repayment_frequency: str = "monthly",
    day_count_convention: str = "act/365"
) -> list[ScheduleItem]:
    """
    Generate a schedule with a balloon payment at the end.

    The regular payments are calculated based on the non-balloon portion,
    with the balloon amount due in the final installment.

    Args:
        principal: Loan principal amount
        annual_rate: Annual interest rate (percentage)
        tenure_months: Total loan tenure in months
        start_date: Loan start date
        balloon_percent: Percentage of principal as balloon (mutually exclusive with balloon_amount)
        balloon_amount: Fixed balloon amount (mutually exclusive with balloon_percent)
        repayment_frequency: Payment frequency
        day_count_convention: Day count convention

    Returns:
        List of schedule items
    """
    principal_dec = _to_decimal(principal)
    annual_rate_dec = _to_decimal(annual_rate)

    # Calculate balloon amount
    if balloon_amount is not None:
        balloon = _to_decimal(balloon_amount)
    elif balloon_percent is not None:
        balloon = (principal_dec * _to_decimal(balloon_percent) / Decimal("100")).quantize(CENT)
    else:
        raise ValueError("Either balloon_percent or balloon_amount must be provided")

    # Principal to be amortized regularly
    amortized_principal = principal_dec - balloon

    num_periods = calculate_tenure_periods(tenure_months, repayment_frequency)
    ppy = periods_per_year(repayment_frequency)
    due_dates = generate_due_dates(start_date, num_periods, repayment_frequency)

    # Calculate EMI for amortized portion
    emi = calculate_emi(amortized_principal, annual_rate_dec, num_periods, ppy)

    schedule: list[ScheduleItem] = []
    balance = principal_dec
    period_start = start_date

    for i, due_date in enumerate(due_dates, start=1):
        period_end = due_date

        interest_due = calculate_interest(
            balance, annual_rate_dec, period_start, period_end, day_count_convention
        )

        if i == num_periods:
            # Final payment includes balloon
            principal_due = balance
        else:
            principal_due = (emi - interest_due).quantize(CENT, rounding=ROUND_HALF_UP)
            if principal_due > balance - balloon:
                principal_due = balance - balloon
            if principal_due < 0:
                principal_due = Decimal("0")

        balance -= principal_due
        if balance < 0:
            balance = Decimal("0")

        total_due = (principal_due + interest_due).quantize(CENT)

        schedule.append({
            "installment_number": i,
            "due_date": due_date,
            "period_start": period_start,
            "period_end": period_end,
            "principal_due": float(principal_due),
            "interest_due": float(interest_due),
            "fees_due": 0.0,
            "total_due": float(total_due),
            "opening_balance": float(balance + principal_due),
            "closing_balance": float(balance),
            "is_moratorium": False,
            "step_number": 0,
        })

        period_start = due_date

    return schedule
