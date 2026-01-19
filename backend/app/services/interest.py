"""
Interest calculation service with day-count convention implementations.

Supported day-count conventions:
- 30/360 (Bond Basis, US): Assumes 30-day months and 360-day years
- ACT/365 (Actual/365 Fixed): Actual days in period, 365-day year
- ACT/ACT (Actual/Actual ISDA): Actual days, actual days in year
- ACT/360 (Actual/360, Money Market): Actual days, 360-day year
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import calendar

# Precision constants
RATE_PRECISION = Decimal("0.0000000001")  # 10 decimal places for rate calculations
CENT = Decimal("0.01")


def _to_decimal(value: float | Decimal | int) -> Decimal:
    """Convert numeric value to Decimal for precise calculations."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def is_leap_year(year: int) -> bool:
    """Check if a year is a leap year."""
    return calendar.isleap(year)


def days_in_year(year: int, convention: str = "act/365") -> int:
    """Return the number of days in a year based on convention."""
    convention = convention.lower()
    if convention in ("30/360", "act/360"):
        return 360
    elif convention == "act/365":
        return 365
    elif convention == "act/act":
        return 366 if is_leap_year(year) else 365
    else:
        raise ValueError(f"Unsupported day-count convention: {convention}")


def actual_days_between(start_date: date, end_date: date) -> int:
    """Calculate actual number of days between two dates."""
    return (end_date - start_date).days


def days_30_360(start_date: date, end_date: date) -> int:
    """
    Calculate days between two dates using 30/360 (US Bond Basis) convention.

    Rules:
    - If start day is 31, change to 30
    - If end day is 31 and start day is 30 or 31, change end day to 30
    """
    d1 = start_date.day
    m1 = start_date.month
    y1 = start_date.year

    d2 = end_date.day
    m2 = end_date.month
    y2 = end_date.year

    # Adjust start day
    if d1 == 31:
        d1 = 30

    # Adjust end day
    if d2 == 31 and d1 >= 30:
        d2 = 30

    return 360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)


def year_fraction(
    start_date: date,
    end_date: date,
    convention: str = "act/365"
) -> Decimal:
    """
    Calculate the year fraction between two dates based on day-count convention.

    Args:
        start_date: Period start date
        end_date: Period end date
        convention: Day-count convention (30/360, act/365, act/act, act/360)

    Returns:
        Year fraction as Decimal
    """
    if start_date >= end_date:
        return Decimal("0")

    convention = convention.lower()

    if convention == "30/360":
        days = days_30_360(start_date, end_date)
        return (Decimal(str(days)) / Decimal("360")).quantize(RATE_PRECISION)

    elif convention == "act/360":
        days = actual_days_between(start_date, end_date)
        return (Decimal(str(days)) / Decimal("360")).quantize(RATE_PRECISION)

    elif convention == "act/365":
        days = actual_days_between(start_date, end_date)
        return (Decimal(str(days)) / Decimal("365")).quantize(RATE_PRECISION)

    elif convention == "act/act":
        # ACT/ACT ISDA: prorate across year boundaries
        days = actual_days_between(start_date, end_date)

        if start_date.year == end_date.year:
            year_days = days_in_year(start_date.year, "act/act")
            return (Decimal(str(days)) / Decimal(str(year_days))).quantize(RATE_PRECISION)

        # Split across years
        fraction = Decimal("0")
        current = start_date

        for year in range(start_date.year, end_date.year + 1):
            year_start = date(year, 1, 1)
            year_end = date(year, 12, 31)
            year_days = days_in_year(year, "act/act")

            period_start = max(current, year_start)
            period_end = min(end_date, date(year + 1, 1, 1))

            if period_start < period_end:
                period_days = actual_days_between(period_start, period_end)
                fraction += Decimal(str(period_days)) / Decimal(str(year_days))

        return fraction.quantize(RATE_PRECISION)

    else:
        raise ValueError(f"Unsupported day-count convention: {convention}")


def calculate_interest(
    principal: float | Decimal,
    annual_rate: float | Decimal,
    start_date: date,
    end_date: date,
    convention: str = "act/365"
) -> Decimal:
    """
    Calculate interest for a period using specified day-count convention.

    Args:
        principal: Outstanding principal amount
        annual_rate: Annual interest rate as percentage (e.g., 12.5 for 12.5%)
        start_date: Period start date
        end_date: Period end date
        convention: Day-count convention

    Returns:
        Interest amount for the period, rounded to 2 decimal places
    """
    principal_dec = _to_decimal(principal)
    rate_dec = _to_decimal(annual_rate) / Decimal("100")  # Convert percentage to decimal

    frac = year_fraction(start_date, end_date, convention)
    interest = principal_dec * rate_dec * frac

    return interest.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_daily_rate(
    annual_rate: float | Decimal,
    convention: str = "act/365",
    year: int | None = None
) -> Decimal:
    """
    Calculate daily interest rate based on convention.

    Args:
        annual_rate: Annual interest rate as percentage
        convention: Day-count convention
        year: Year (required for ACT/ACT convention)

    Returns:
        Daily rate as decimal (not percentage)
    """
    rate_dec = _to_decimal(annual_rate) / Decimal("100")
    convention = convention.lower()

    if convention == "act/act":
        if year is None:
            raise ValueError("Year required for ACT/ACT convention")
        year_days = days_in_year(year, convention)
    else:
        year_days = days_in_year(date.today().year, convention)

    return (rate_dec / Decimal(str(year_days))).quantize(RATE_PRECISION)


def calculate_periodic_rate(
    annual_rate: float | Decimal,
    periods_per_year: int
) -> Decimal:
    """
    Calculate periodic interest rate (e.g., monthly, quarterly).

    Args:
        annual_rate: Annual interest rate as percentage
        periods_per_year: Number of periods (12 for monthly, 4 for quarterly, etc.)

    Returns:
        Periodic rate as decimal (not percentage)
    """
    rate_dec = _to_decimal(annual_rate) / Decimal("100")
    return (rate_dec / Decimal(str(periods_per_year))).quantize(RATE_PRECISION)


def calculate_effective_annual_rate(
    nominal_rate: float | Decimal,
    compounding_periods: int
) -> Decimal:
    """
    Calculate effective annual rate from nominal rate.

    EAR = (1 + r/n)^n - 1

    Args:
        nominal_rate: Nominal annual rate as percentage
        compounding_periods: Number of compounding periods per year

    Returns:
        Effective annual rate as percentage
    """
    r = _to_decimal(nominal_rate) / Decimal("100")
    n = Decimal(str(compounding_periods))

    ear = (Decimal("1") + r / n) ** n - Decimal("1")
    return (ear * Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def calculate_emi(
    principal: float | Decimal,
    annual_rate: float | Decimal,
    tenure_periods: int,
    periods_per_year: int = 12
) -> Decimal:
    """
    Calculate EMI (Equated Monthly/Periodic Installment).

    EMI = P * r * (1+r)^n / ((1+r)^n - 1)

    Args:
        principal: Loan principal amount
        annual_rate: Annual interest rate as percentage
        tenure_periods: Number of installments
        periods_per_year: Periods per year (12 for monthly, 4 for quarterly)

    Returns:
        EMI amount rounded to 2 decimal places
    """
    principal_dec = _to_decimal(principal)

    if annual_rate == 0:
        return (principal_dec / Decimal(str(tenure_periods))).quantize(
            CENT, rounding=ROUND_HALF_UP
        )

    periodic_rate = calculate_periodic_rate(annual_rate, periods_per_year)
    n = Decimal(str(tenure_periods))

    factor = (Decimal("1") + periodic_rate) ** n
    emi = principal_dec * periodic_rate * factor / (factor - Decimal("1"))

    return emi.quantize(CENT, rounding=ROUND_HALF_UP)
