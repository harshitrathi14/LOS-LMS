"""
Tests for payment frequency calculations.
"""

import pytest
from datetime import date

from app.services.frequency import (
    add_period,
    add_months,
    generate_due_dates,
    periods_per_year,
    calculate_tenure_periods,
    calculate_tenure_months,
    get_period_start_end,
    days_in_period,
    is_period_based_on_months,
    is_valid_frequency,
    get_supported_frequencies,
    annualize_rate,
)


class TestPeriodsPerYear:
    """Test periods per year for different frequencies."""

    def test_weekly(self):
        assert periods_per_year("weekly") == 52

    def test_biweekly(self):
        assert periods_per_year("biweekly") == 26

    def test_monthly(self):
        assert periods_per_year("monthly") == 12

    def test_quarterly(self):
        assert periods_per_year("quarterly") == 4

    def test_semiannual(self):
        assert periods_per_year("semiannual") == 2

    def test_annual(self):
        assert periods_per_year("annual") == 1

    def test_case_insensitive(self):
        assert periods_per_year("MONTHLY") == 12
        assert periods_per_year("Weekly") == 52

    def test_invalid_frequency_raises(self):
        with pytest.raises(ValueError, match="Unsupported frequency"):
            periods_per_year("daily")


class TestAddPeriod:
    """Test adding payment periods to dates."""

    def test_add_one_month(self):
        result = add_period(date(2024, 1, 15), "monthly", 1)
        assert result == date(2024, 2, 15)

    def test_add_multiple_months(self):
        result = add_period(date(2024, 1, 15), "monthly", 3)
        assert result == date(2024, 4, 15)

    def test_add_one_week(self):
        result = add_period(date(2024, 1, 15), "weekly", 1)
        assert result == date(2024, 1, 22)

    def test_add_biweekly(self):
        result = add_period(date(2024, 1, 15), "biweekly", 1)
        assert result == date(2024, 1, 29)

    def test_add_quarterly(self):
        result = add_period(date(2024, 1, 15), "quarterly", 1)
        assert result == date(2024, 4, 15)

    def test_add_semiannual(self):
        result = add_period(date(2024, 1, 15), "semiannual", 1)
        assert result == date(2024, 7, 15)

    def test_add_annual(self):
        result = add_period(date(2024, 1, 15), "annual", 1)
        assert result == date(2025, 1, 15)

    def test_month_end_handling(self):
        # Jan 31 + 1 month = Feb 28/29 (month end clamping)
        result = add_period(date(2024, 1, 31), "monthly", 1)
        assert result == date(2024, 2, 29)  # 2024 is leap year

        result = add_period(date(2023, 1, 31), "monthly", 1)
        assert result == date(2023, 2, 28)  # 2023 is not leap year

    def test_add_negative_periods(self):
        result = add_period(date(2024, 3, 15), "monthly", -1)
        assert result == date(2024, 2, 15)


class TestAddMonths:
    """Test add_months helper function."""

    def test_simple_add(self):
        assert add_months(date(2024, 1, 15), 1) == date(2024, 2, 15)

    def test_year_rollover(self):
        assert add_months(date(2024, 11, 15), 3) == date(2025, 2, 15)

    def test_month_end_clamping(self):
        assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
        assert add_months(date(2024, 3, 31), 1) == date(2024, 4, 30)

    def test_negative_months(self):
        assert add_months(date(2024, 3, 15), -2) == date(2024, 1, 15)


class TestGenerateDueDates:
    """Test due date generation."""

    def test_monthly_12_periods(self):
        due_dates = generate_due_dates(date(2024, 1, 1), 12, "monthly")
        assert len(due_dates) == 12
        assert due_dates[0] == date(2024, 2, 1)
        assert due_dates[11] == date(2025, 1, 1)

    def test_quarterly_4_periods(self):
        due_dates = generate_due_dates(date(2024, 1, 1), 4, "quarterly")
        assert len(due_dates) == 4
        assert due_dates[0] == date(2024, 4, 1)
        assert due_dates[3] == date(2025, 1, 1)

    def test_weekly_periods(self):
        due_dates = generate_due_dates(date(2024, 1, 1), 4, "weekly")
        assert len(due_dates) == 4
        assert due_dates[0] == date(2024, 1, 8)
        assert due_dates[3] == date(2024, 1, 29)


class TestCalculateTenurePeriods:
    """Test tenure conversion from months to periods."""

    def test_monthly(self):
        assert calculate_tenure_periods(12, "monthly") == 12
        assert calculate_tenure_periods(24, "monthly") == 24

    def test_quarterly(self):
        assert calculate_tenure_periods(12, "quarterly") == 4
        assert calculate_tenure_periods(24, "quarterly") == 8

    def test_weekly(self):
        assert calculate_tenure_periods(12, "weekly") == 52

    def test_biweekly(self):
        assert calculate_tenure_periods(12, "biweekly") == 26

    def test_annual(self):
        assert calculate_tenure_periods(24, "annual") == 2


class TestCalculateTenureMonths:
    """Test conversion from periods to months."""

    def test_monthly(self):
        assert calculate_tenure_months(12, "monthly") == 12

    def test_quarterly(self):
        assert calculate_tenure_months(4, "quarterly") == 12

    def test_weekly(self):
        assert calculate_tenure_months(52, "weekly") == 12


class TestGetPeriodStartEnd:
    """Test period boundary calculation."""

    def test_monthly_period(self):
        start, end = get_period_start_end(date(2024, 2, 15), "monthly", 1)
        assert end == date(2024, 2, 15)
        assert start == date(2024, 1, 15)

    def test_quarterly_period(self):
        start, end = get_period_start_end(date(2024, 4, 1), "quarterly", 1)
        assert end == date(2024, 4, 1)
        assert start == date(2024, 1, 1)


class TestDaysInPeriod:
    """Test days in period calculation."""

    def test_weekly(self):
        assert days_in_period("weekly") == 7

    def test_biweekly(self):
        assert days_in_period("biweekly") == 14

    def test_monthly_average(self):
        # Without reference date, uses average
        days = days_in_period("monthly")
        assert 30 <= days <= 31

    def test_monthly_with_reference(self):
        # January has 31 days
        days = days_in_period("monthly", date(2024, 1, 15))
        assert days == 31


class TestFrequencyValidation:
    """Test frequency validation helpers."""

    def test_valid_frequencies(self):
        assert is_valid_frequency("weekly") is True
        assert is_valid_frequency("monthly") is True
        assert is_valid_frequency("QUARTERLY") is True

    def test_invalid_frequencies(self):
        assert is_valid_frequency("daily") is False
        assert is_valid_frequency("unknown") is False

    def test_get_supported_frequencies(self):
        freqs = get_supported_frequencies()
        assert "weekly" in freqs
        assert "monthly" in freqs
        assert "quarterly" in freqs
        assert len(freqs) == 6

    def test_is_month_based(self):
        assert is_period_based_on_months("monthly") is True
        assert is_period_based_on_months("quarterly") is True
        assert is_period_based_on_months("weekly") is False
        assert is_period_based_on_months("biweekly") is False


class TestAnnualizeRate:
    """Test rate annualization."""

    def test_monthly_to_annual(self):
        assert annualize_rate(1, "monthly") == 12

    def test_quarterly_to_annual(self):
        assert annualize_rate(3, "quarterly") == 12
