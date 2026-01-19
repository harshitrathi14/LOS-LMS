"""
Tests for day-count conventions and interest calculations.

These tests verify financial accuracy against industry standards.
"""

import pytest
from datetime import date
from decimal import Decimal

from app.services.interest import (
    actual_days_between,
    days_30_360,
    year_fraction,
    calculate_interest,
    calculate_daily_rate,
    calculate_periodic_rate,
    calculate_effective_annual_rate,
    calculate_emi,
    is_leap_year,
    days_in_year,
)


class TestActualDaysBetween:
    """Test actual days calculation."""

    def test_same_date(self):
        d = date(2024, 1, 15)
        assert actual_days_between(d, d) == 0

    def test_one_day(self):
        assert actual_days_between(date(2024, 1, 1), date(2024, 1, 2)) == 1

    def test_one_month(self):
        assert actual_days_between(date(2024, 1, 1), date(2024, 2, 1)) == 31

    def test_leap_year_february(self):
        # 2024 is a leap year
        assert actual_days_between(date(2024, 2, 1), date(2024, 3, 1)) == 29

    def test_non_leap_year_february(self):
        # 2023 is not a leap year
        assert actual_days_between(date(2023, 2, 1), date(2023, 3, 1)) == 28

    def test_full_year(self):
        assert actual_days_between(date(2024, 1, 1), date(2025, 1, 1)) == 366  # Leap year


class TestDays30_360:
    """Test 30/360 (Bond Basis) day count convention."""

    def test_same_date(self):
        d = date(2024, 1, 15)
        assert days_30_360(d, d) == 0

    def test_one_month(self):
        # 30/360: one month = 30 days
        assert days_30_360(date(2024, 1, 1), date(2024, 2, 1)) == 30

    def test_full_year(self):
        # 30/360: one year = 360 days
        assert days_30_360(date(2024, 1, 1), date(2025, 1, 1)) == 360

    def test_day_31_adjustment(self):
        # If start day is 31, change to 30
        # Jan 31 to Feb 28 should be (30 - 30 + 30*(2-1)) = 30 days
        assert days_30_360(date(2024, 1, 31), date(2024, 2, 28)) == 28

    def test_end_day_31_adjustment(self):
        # If end day is 31 and start day >= 30, change end to 30
        assert days_30_360(date(2024, 1, 30), date(2024, 3, 31)) == 60

    def test_mid_month_dates(self):
        # Jan 15 to Feb 15 = 30 days in 30/360
        assert days_30_360(date(2024, 1, 15), date(2024, 2, 15)) == 30


class TestYearFraction:
    """Test year fraction calculations for different conventions."""

    def test_act_365_one_month(self):
        # January has 31 days
        frac = year_fraction(date(2024, 1, 1), date(2024, 2, 1), "act/365")
        expected = Decimal("31") / Decimal("365")
        assert abs(frac - expected) < Decimal("0.0000001")

    def test_act_365_full_year(self):
        frac = year_fraction(date(2024, 1, 1), date(2025, 1, 1), "act/365")
        # 2024 is leap year = 366 days, but act/365 always divides by 365
        expected = Decimal("366") / Decimal("365")
        assert abs(frac - expected) < Decimal("0.0000001")

    def test_act_360_one_month(self):
        frac = year_fraction(date(2024, 1, 1), date(2024, 2, 1), "act/360")
        expected = Decimal("31") / Decimal("360")
        assert abs(frac - expected) < Decimal("0.0000001")

    def test_30_360_one_month(self):
        frac = year_fraction(date(2024, 1, 1), date(2024, 2, 1), "30/360")
        expected = Decimal("30") / Decimal("360")
        assert abs(frac - expected) < Decimal("0.0000001")

    def test_30_360_full_year(self):
        frac = year_fraction(date(2024, 1, 1), date(2025, 1, 1), "30/360")
        assert frac == Decimal("1")  # Exactly 1 year

    def test_act_act_leap_year(self):
        # 2024 is a leap year (366 days)
        frac = year_fraction(date(2024, 1, 1), date(2025, 1, 1), "act/act")
        assert frac == Decimal("1")  # Exactly 1 year

    def test_act_act_non_leap_year(self):
        # 2023 is not a leap year (365 days)
        frac = year_fraction(date(2023, 1, 1), date(2024, 1, 1), "act/act")
        assert frac == Decimal("1")  # Exactly 1 year

    def test_act_act_cross_year_boundary(self):
        # Dec 2023 to Feb 2024 crosses year boundary
        frac = year_fraction(date(2023, 12, 1), date(2024, 2, 1), "act/act")
        # 31 days in 2023 (365-day year) + 31 days in 2024 (366-day year)
        expected = Decimal("31") / Decimal("365") + Decimal("31") / Decimal("366")
        assert abs(frac - expected) < Decimal("0.0000001")

    def test_start_after_end_returns_zero(self):
        frac = year_fraction(date(2024, 2, 1), date(2024, 1, 1), "act/365")
        assert frac == Decimal("0")

    def test_invalid_convention_raises(self):
        with pytest.raises(ValueError, match="Unsupported day-count convention"):
            year_fraction(date(2024, 1, 1), date(2024, 2, 1), "invalid")


class TestCalculateInterest:
    """Test interest calculation with various conventions."""

    def test_simple_interest_act_365(self):
        # 100,000 principal, 12% annual rate, 31 days
        interest = calculate_interest(
            principal=100000,
            annual_rate=12,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 1),
            convention="act/365"
        )
        # Expected: 100000 * 0.12 * (31/365) = 1019.18
        expected = Decimal("100000") * Decimal("0.12") * (Decimal("31") / Decimal("365"))
        assert abs(interest - expected.quantize(Decimal("0.01"))) < Decimal("0.01")

    def test_simple_interest_30_360(self):
        # 100,000 principal, 12% annual rate, 30 days (30/360)
        interest = calculate_interest(
            principal=100000,
            annual_rate=12,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 1),
            convention="30/360"
        )
        # Expected: 100000 * 0.12 * (30/360) = 1000.00
        assert interest == Decimal("1000.00")

    def test_zero_rate(self):
        interest = calculate_interest(
            principal=100000,
            annual_rate=0,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 1),
            convention="act/365"
        )
        assert interest == Decimal("0.00")

    def test_decimal_inputs(self):
        interest = calculate_interest(
            principal=Decimal("100000"),
            annual_rate=Decimal("12.5"),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 1),
            convention="act/365"
        )
        assert interest > Decimal("0")


class TestCalculateEMI:
    """Test EMI calculation accuracy."""

    def test_standard_emi(self):
        # 100,000 principal, 12% annual rate, 12 months
        emi = calculate_emi(
            principal=100000,
            annual_rate=12,
            tenure_periods=12,
            periods_per_year=12
        )
        # Expected EMI approximately 8884.88
        assert Decimal("8884") <= emi <= Decimal("8885")

    def test_zero_rate_emi(self):
        emi = calculate_emi(
            principal=100000,
            annual_rate=0,
            tenure_periods=10,
            periods_per_year=12
        )
        # Zero rate = equal principal payments
        assert emi == Decimal("10000.00")

    def test_quarterly_emi(self):
        # 100,000 principal, 12% annual rate, 4 quarterly payments
        emi = calculate_emi(
            principal=100000,
            annual_rate=12,
            tenure_periods=4,
            periods_per_year=4
        )
        # Quarterly EMI should be higher than monthly EMI
        monthly_emi = calculate_emi(100000, 12, 12, 12)
        assert emi > monthly_emi * 3  # Quarterly > 3 months worth


class TestPeriodicRates:
    """Test periodic rate calculations."""

    def test_monthly_rate(self):
        rate = calculate_periodic_rate(12, 12)
        # 12% annual / 12 = 1% monthly = 0.01
        assert abs(rate - Decimal("0.01")) < Decimal("0.0000001")

    def test_quarterly_rate(self):
        rate = calculate_periodic_rate(12, 4)
        # 12% annual / 4 = 3% quarterly = 0.03
        assert abs(rate - Decimal("0.03")) < Decimal("0.0000001")

    def test_daily_rate_act_365(self):
        rate = calculate_daily_rate(12, "act/365")
        # 12% / 365
        expected = Decimal("0.12") / Decimal("365")
        assert abs(rate - expected) < Decimal("0.0000001")

    def test_daily_rate_act_act_requires_year(self):
        with pytest.raises(ValueError, match="Year required"):
            calculate_daily_rate(12, "act/act")

    def test_daily_rate_act_act_leap_year(self):
        rate = calculate_daily_rate(12, "act/act", year=2024)
        expected = Decimal("0.12") / Decimal("366")
        assert abs(rate - expected) < Decimal("0.0000001")


class TestEffectiveAnnualRate:
    """Test effective annual rate calculation."""

    def test_monthly_compounding(self):
        ear = calculate_effective_annual_rate(12, 12)
        # EAR for 12% nominal with monthly compounding ≈ 12.68%
        assert Decimal("12.6") < ear < Decimal("12.8")

    def test_quarterly_compounding(self):
        ear = calculate_effective_annual_rate(12, 4)
        # EAR for 12% nominal with quarterly compounding ≈ 12.55%
        assert Decimal("12.5") < ear < Decimal("12.6")

    def test_annual_compounding(self):
        ear = calculate_effective_annual_rate(12, 1)
        # EAR equals nominal rate with annual compounding
        assert ear == Decimal("12.0000")


class TestLeapYearHelpers:
    """Test leap year helper functions."""

    def test_leap_year_detection(self):
        assert is_leap_year(2024) is True
        assert is_leap_year(2023) is False
        assert is_leap_year(2000) is True  # Divisible by 400
        assert is_leap_year(1900) is False  # Divisible by 100 but not 400

    def test_days_in_year_act_365(self):
        assert days_in_year(2024, "act/365") == 365
        assert days_in_year(2023, "act/365") == 365

    def test_days_in_year_act_act(self):
        assert days_in_year(2024, "act/act") == 366
        assert days_in_year(2023, "act/act") == 365

    def test_days_in_year_30_360(self):
        assert days_in_year(2024, "30/360") == 360
        assert days_in_year(2023, "30/360") == 360
