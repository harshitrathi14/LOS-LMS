"""
Payment frequency service for handling various repayment schedules.

Supported frequencies:
- weekly: Every 7 days (52 periods/year)
- biweekly: Every 14 days (26 periods/year)
- monthly: Every month (12 periods/year)
- quarterly: Every 3 months (4 periods/year)
- semiannual: Every 6 months (2 periods/year)
- annual: Every 12 months (1 period/year)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal
import calendar

# Type definitions
FrequencyType = Literal[
    "weekly", "biweekly", "monthly", "quarterly", "semiannual", "annual"
]

# Frequency configuration
FREQUENCY_CONFIG: dict[str, dict] = {
    "weekly": {
        "periods_per_year": 52,
        "days": 7,
        "months": None,
    },
    "biweekly": {
        "periods_per_year": 26,
        "days": 14,
        "months": None,
    },
    "monthly": {
        "periods_per_year": 12,
        "days": None,
        "months": 1,
    },
    "quarterly": {
        "periods_per_year": 4,
        "days": None,
        "months": 3,
    },
    "semiannual": {
        "periods_per_year": 2,
        "days": None,
        "months": 6,
    },
    "annual": {
        "periods_per_year": 1,
        "days": None,
        "months": 12,
    },
}


def get_supported_frequencies() -> list[str]:
    """Return list of supported payment frequencies."""
    return list(FREQUENCY_CONFIG.keys())


def is_valid_frequency(frequency: str) -> bool:
    """Check if a frequency string is valid."""
    return frequency.lower() in FREQUENCY_CONFIG


def periods_per_year(frequency: str) -> int:
    """
    Get number of payment periods per year for a frequency.

    Args:
        frequency: Payment frequency string

    Returns:
        Number of periods in a year

    Raises:
        ValueError: If frequency is not supported
    """
    frequency = frequency.lower()
    if frequency not in FREQUENCY_CONFIG:
        raise ValueError(
            f"Unsupported frequency: {frequency}. "
            f"Supported: {', '.join(get_supported_frequencies())}"
        )
    return FREQUENCY_CONFIG[frequency]["periods_per_year"]


def add_months(anchor: date, months: int) -> date:
    """
    Add months to a date, handling month-end edge cases.

    Args:
        anchor: Starting date
        months: Number of months to add (can be negative)

    Returns:
        Resulting date
    """
    month_index = (anchor.month - 1) + months
    year = anchor.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def add_period(
    anchor: date,
    frequency: str,
    periods: int = 1
) -> date:
    """
    Add payment periods to a date.

    Args:
        anchor: Starting date
        frequency: Payment frequency
        periods: Number of periods to add (default 1)

    Returns:
        Resulting date

    Raises:
        ValueError: If frequency is not supported
    """
    frequency = frequency.lower()
    if frequency not in FREQUENCY_CONFIG:
        raise ValueError(f"Unsupported frequency: {frequency}")

    config = FREQUENCY_CONFIG[frequency]

    if config["days"] is not None:
        # Day-based frequency (weekly, biweekly)
        return anchor + timedelta(days=config["days"] * periods)
    else:
        # Month-based frequency
        return add_months(anchor, config["months"] * periods)


def generate_due_dates(
    start_date: date,
    num_periods: int,
    frequency: str
) -> list[date]:
    """
    Generate a list of due dates for a loan.

    Args:
        start_date: Loan start/disbursement date
        num_periods: Number of payment periods
        frequency: Payment frequency

    Returns:
        List of due dates (first due date is one period after start)
    """
    frequency = frequency.lower()
    if frequency not in FREQUENCY_CONFIG:
        raise ValueError(f"Unsupported frequency: {frequency}")

    due_dates = []
    for period in range(1, num_periods + 1):
        due_dates.append(add_period(start_date, frequency, period))

    return due_dates


def calculate_tenure_periods(
    tenure_months: int,
    frequency: str
) -> int:
    """
    Convert tenure in months to number of payment periods.

    Args:
        tenure_months: Loan tenure in months
        frequency: Payment frequency

    Returns:
        Number of payment periods

    Example:
        12 months, monthly -> 12 periods
        12 months, quarterly -> 4 periods
        12 months, weekly -> 52 periods
    """
    frequency = frequency.lower()
    periods = periods_per_year(frequency)

    # Convert months to years, then to periods
    years = tenure_months / 12
    return round(years * periods)


def calculate_tenure_months(
    num_periods: int,
    frequency: str
) -> int:
    """
    Convert number of payment periods to tenure in months.

    Args:
        num_periods: Number of payment periods
        frequency: Payment frequency

    Returns:
        Tenure in months (rounded)
    """
    frequency = frequency.lower()
    periods = periods_per_year(frequency)

    # Convert periods to years, then to months
    years = num_periods / periods
    return round(years * 12)


def get_period_start_end(
    due_date: date,
    frequency: str,
    period_number: int = 1
) -> tuple[date, date]:
    """
    Calculate the start and end date of a payment period.

    For interest calculation purposes, this returns the period
    that ends on the due date.

    Args:
        due_date: Payment due date
        frequency: Payment frequency
        period_number: Period number (1 = first period)

    Returns:
        Tuple of (period_start, period_end)
    """
    # Period ends on due date
    period_end = due_date

    # Period starts one frequency back from due date
    period_start = add_period(due_date, frequency, -1)

    return (period_start, period_end)


def days_in_period(frequency: str, reference_date: date | None = None) -> int:
    """
    Get approximate number of days in a payment period.

    For month-based frequencies, uses average or actual days.

    Args:
        frequency: Payment frequency
        reference_date: Reference date for calculating actual days

    Returns:
        Number of days in the period
    """
    frequency = frequency.lower()
    config = FREQUENCY_CONFIG[frequency]

    if config["days"] is not None:
        return config["days"]

    # For month-based frequencies, calculate based on reference
    if reference_date is None:
        # Use average days
        return round(365 / config["periods_per_year"])

    # Calculate actual days
    next_date = add_period(reference_date, frequency, 1)
    return (next_date - reference_date).days


def is_period_based_on_months(frequency: str) -> bool:
    """Check if frequency uses month-based periods."""
    frequency = frequency.lower()
    if frequency not in FREQUENCY_CONFIG:
        raise ValueError(f"Unsupported frequency: {frequency}")
    return FREQUENCY_CONFIG[frequency]["months"] is not None


def annualize_rate(periodic_rate: float, frequency: str) -> float:
    """
    Convert a periodic rate to an annual rate (simple, not compounded).

    Args:
        periodic_rate: Interest rate for one period
        frequency: Payment frequency

    Returns:
        Annual rate
    """
    return periodic_rate * periods_per_year(frequency)
