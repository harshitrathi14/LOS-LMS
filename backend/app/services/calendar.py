"""
Business day adjustment and holiday calendar service.

Provides functionality for:
- Business day determination
- Holiday calendar management
- Date adjustments for payment due dates
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal
from sqlalchemy.orm import Session

# Business day adjustment types
AdjustmentType = Literal[
    "no_adjustment",     # Use actual date regardless of weekends/holidays
    "following",         # Move to next business day
    "preceding",         # Move to previous business day
    "modified_following", # Following, unless crosses month boundary, then preceding
    "modified_preceding", # Preceding, unless crosses month boundary, then following
]


def is_weekend(d: date) -> bool:
    """Check if date falls on a weekend (Saturday=5, Sunday=6)."""
    return d.weekday() >= 5


def get_holidays_for_calendar(
    calendar_id: int,
    start_date: date,
    end_date: date,
    db: Session
) -> set[date]:
    """
    Fetch holidays for a calendar within a date range.

    Args:
        calendar_id: Holiday calendar ID
        start_date: Range start date
        end_date: Range end date
        db: Database session

    Returns:
        Set of holiday dates
    """
    # Import here to avoid circular imports
    from app.models.holiday_calendar import Holiday

    holidays = db.query(Holiday).filter(
        Holiday.calendar_id == calendar_id,
        Holiday.holiday_date >= start_date,
        Holiday.holiday_date <= end_date
    ).all()

    holiday_dates = set()
    for h in holidays:
        if h.is_recurring:
            # For recurring holidays, check if the date falls within range
            # by checking the same month/day in each year
            for year in range(start_date.year, end_date.year + 1):
                try:
                    recurring_date = date(year, h.holiday_date.month, h.holiday_date.day)
                    if start_date <= recurring_date <= end_date:
                        holiday_dates.add(recurring_date)
                except ValueError:
                    # Handle Feb 29 in non-leap years
                    pass
        else:
            holiday_dates.add(h.holiday_date)

    return holiday_dates


def is_business_day(
    d: date,
    calendar_id: int | None = None,
    db: Session | None = None,
    holidays: set[date] | None = None
) -> bool:
    """
    Check if a date is a business day.

    A business day is one that is not a weekend and not a holiday.

    Args:
        d: Date to check
        calendar_id: Optional holiday calendar ID
        db: Database session (required if calendar_id provided)
        holidays: Pre-fetched set of holiday dates (optimization)

    Returns:
        True if business day, False otherwise
    """
    if is_weekend(d):
        return False

    if holidays is not None:
        return d not in holidays

    if calendar_id is not None and db is not None:
        # Fetch holidays for just this date
        calendar_holidays = get_holidays_for_calendar(
            calendar_id, d, d, db
        )
        return d not in calendar_holidays

    return True


def next_business_day(
    d: date,
    calendar_id: int | None = None,
    db: Session | None = None,
    holidays: set[date] | None = None,
    max_days: int = 30
) -> date:
    """
    Find the next business day on or after the given date.

    Args:
        d: Starting date
        calendar_id: Optional holiday calendar ID
        db: Database session
        holidays: Pre-fetched holidays (optimization)
        max_days: Maximum days to search (safety limit)

    Returns:
        Next business day

    Raises:
        ValueError: If no business day found within max_days
    """
    current = d
    for _ in range(max_days):
        if is_business_day(current, calendar_id, db, holidays):
            return current
        current += timedelta(days=1)

    raise ValueError(f"No business day found within {max_days} days of {d}")


def previous_business_day(
    d: date,
    calendar_id: int | None = None,
    db: Session | None = None,
    holidays: set[date] | None = None,
    max_days: int = 30
) -> date:
    """
    Find the previous business day on or before the given date.

    Args:
        d: Starting date
        calendar_id: Optional holiday calendar ID
        db: Database session
        holidays: Pre-fetched holidays (optimization)
        max_days: Maximum days to search (safety limit)

    Returns:
        Previous business day

    Raises:
        ValueError: If no business day found within max_days
    """
    current = d
    for _ in range(max_days):
        if is_business_day(current, calendar_id, db, holidays):
            return current
        current -= timedelta(days=1)

    raise ValueError(f"No business day found within {max_days} days before {d}")


def adjust_for_business_day(
    d: date,
    adjustment: AdjustmentType = "following",
    calendar_id: int | None = None,
    db: Session | None = None,
    holidays: set[date] | None = None
) -> date:
    """
    Adjust a date according to business day convention.

    Args:
        d: Date to adjust
        adjustment: Type of adjustment
        calendar_id: Optional holiday calendar ID
        db: Database session
        holidays: Pre-fetched holidays (optimization)

    Returns:
        Adjusted date
    """
    if adjustment == "no_adjustment":
        return d

    if is_business_day(d, calendar_id, db, holidays):
        return d

    if adjustment == "following":
        return next_business_day(d, calendar_id, db, holidays)

    elif adjustment == "preceding":
        return previous_business_day(d, calendar_id, db, holidays)

    elif adjustment == "modified_following":
        next_bd = next_business_day(d, calendar_id, db, holidays)
        # If next business day is in different month, use preceding
        if next_bd.month != d.month:
            return previous_business_day(d, calendar_id, db, holidays)
        return next_bd

    elif adjustment == "modified_preceding":
        prev_bd = previous_business_day(d, calendar_id, db, holidays)
        # If previous business day is in different month, use following
        if prev_bd.month != d.month:
            return next_business_day(d, calendar_id, db, holidays)
        return prev_bd

    else:
        raise ValueError(f"Unsupported adjustment type: {adjustment}")


def adjust_due_dates(
    due_dates: list[date],
    adjustment: AdjustmentType = "following",
    calendar_id: int | None = None,
    db: Session | None = None
) -> list[date]:
    """
    Adjust a list of due dates for business days.

    Optimizes by pre-fetching all relevant holidays.

    Args:
        due_dates: List of original due dates
        adjustment: Business day adjustment type
        calendar_id: Optional holiday calendar ID
        db: Database session

    Returns:
        List of adjusted due dates
    """
    if not due_dates or adjustment == "no_adjustment":
        return due_dates

    # Pre-fetch holidays for the entire date range (with buffer for adjustments)
    holidays: set[date] | None = None
    if calendar_id is not None and db is not None:
        min_date = min(due_dates) - timedelta(days=10)
        max_date = max(due_dates) + timedelta(days=10)
        holidays = get_holidays_for_calendar(calendar_id, min_date, max_date, db)

    return [
        adjust_for_business_day(d, adjustment, calendar_id, db, holidays)
        for d in due_dates
    ]


def business_days_between(
    start_date: date,
    end_date: date,
    calendar_id: int | None = None,
    db: Session | None = None
) -> int:
    """
    Count business days between two dates (exclusive of start, inclusive of end).

    Args:
        start_date: Start date
        end_date: End date
        calendar_id: Optional holiday calendar ID
        db: Database session

    Returns:
        Number of business days
    """
    if start_date >= end_date:
        return 0

    # Pre-fetch holidays
    holidays: set[date] | None = None
    if calendar_id is not None and db is not None:
        holidays = get_holidays_for_calendar(calendar_id, start_date, end_date, db)

    count = 0
    current = start_date + timedelta(days=1)
    while current <= end_date:
        if is_business_day(current, calendar_id, db, holidays):
            count += 1
        current += timedelta(days=1)

    return count


def add_business_days(
    start_date: date,
    num_days: int,
    calendar_id: int | None = None,
    db: Session | None = None
) -> date:
    """
    Add a number of business days to a date.

    Args:
        start_date: Starting date
        num_days: Number of business days to add
        calendar_id: Optional holiday calendar ID
        db: Database session

    Returns:
        Resulting date
    """
    if num_days == 0:
        return start_date

    direction = 1 if num_days > 0 else -1
    remaining = abs(num_days)
    current = start_date

    # Pre-fetch holidays for a reasonable range
    holidays: set[date] | None = None
    if calendar_id is not None and db is not None:
        buffer = num_days * 2 if num_days > 0 else num_days * 2 * -1
        end_range = start_date + timedelta(days=buffer)
        holidays = get_holidays_for_calendar(
            calendar_id,
            min(start_date, end_range),
            max(start_date, end_range),
            db
        )

    while remaining > 0:
        current += timedelta(days=direction)
        if is_business_day(current, calendar_id, db, holidays):
            remaining -= 1

    return current


def get_default_adjustment_type(product_type: str | None = None) -> AdjustmentType:
    """
    Get default business day adjustment type based on product type.

    Args:
        product_type: Optional loan product type

    Returns:
        Default adjustment type
    """
    # Default to modified following for most financial products
    return "modified_following"
