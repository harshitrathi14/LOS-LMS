"""
Tests for business day adjustments and holiday calendar functionality.
"""

import pytest
from datetime import date, timedelta

from app.services.calendar import (
    is_weekend,
    is_business_day,
    next_business_day,
    previous_business_day,
    adjust_for_business_day,
    adjust_due_dates,
    business_days_between,
    add_business_days,
    get_default_adjustment_type,
)


class TestWeekendDetection:
    """Test weekend detection."""

    def test_weekday(self):
        # January 15, 2024 is Monday
        assert is_weekend(date(2024, 1, 15)) is False

    def test_saturday(self):
        # January 13, 2024 is Saturday
        assert is_weekend(date(2024, 1, 13)) is True

    def test_sunday(self):
        # January 14, 2024 is Sunday
        assert is_weekend(date(2024, 1, 14)) is True

    def test_friday(self):
        # January 12, 2024 is Friday
        assert is_weekend(date(2024, 1, 12)) is False


class TestIsBusinessDay:
    """Test business day determination without holiday calendar."""

    def test_weekday_is_business_day(self):
        assert is_business_day(date(2024, 1, 15)) is True  # Monday

    def test_weekend_not_business_day(self):
        assert is_business_day(date(2024, 1, 13)) is False  # Saturday
        assert is_business_day(date(2024, 1, 14)) is False  # Sunday

    def test_with_holiday_set(self):
        holidays = {date(2024, 1, 15)}  # Mark Monday as holiday
        assert is_business_day(date(2024, 1, 15), holidays=holidays) is False
        assert is_business_day(date(2024, 1, 16), holidays=holidays) is True


class TestNextBusinessDay:
    """Test finding next business day."""

    def test_already_business_day(self):
        # Monday returns same day
        assert next_business_day(date(2024, 1, 15)) == date(2024, 1, 15)

    def test_saturday_to_monday(self):
        # Saturday moves to Monday
        assert next_business_day(date(2024, 1, 13)) == date(2024, 1, 15)

    def test_sunday_to_monday(self):
        # Sunday moves to Monday
        assert next_business_day(date(2024, 1, 14)) == date(2024, 1, 15)

    def test_friday_stays_friday(self):
        assert next_business_day(date(2024, 1, 12)) == date(2024, 1, 12)

    def test_with_holiday(self):
        # Monday is holiday, should move to Tuesday
        holidays = {date(2024, 1, 15)}
        assert next_business_day(date(2024, 1, 13), holidays=holidays) == date(2024, 1, 16)


class TestPreviousBusinessDay:
    """Test finding previous business day."""

    def test_already_business_day(self):
        assert previous_business_day(date(2024, 1, 15)) == date(2024, 1, 15)

    def test_saturday_to_friday(self):
        assert previous_business_day(date(2024, 1, 13)) == date(2024, 1, 12)

    def test_sunday_to_friday(self):
        assert previous_business_day(date(2024, 1, 14)) == date(2024, 1, 12)

    def test_monday_stays_monday(self):
        assert previous_business_day(date(2024, 1, 15)) == date(2024, 1, 15)


class TestAdjustForBusinessDay:
    """Test business day adjustment types."""

    def test_no_adjustment(self):
        # Saturday stays Saturday
        assert adjust_for_business_day(
            date(2024, 1, 13), "no_adjustment"
        ) == date(2024, 1, 13)

    def test_following(self):
        # Saturday moves to Monday
        assert adjust_for_business_day(
            date(2024, 1, 13), "following"
        ) == date(2024, 1, 15)

    def test_preceding(self):
        # Saturday moves to Friday
        assert adjust_for_business_day(
            date(2024, 1, 13), "preceding"
        ) == date(2024, 1, 12)

    def test_modified_following_same_month(self):
        # Saturday moves to Monday (same month)
        assert adjust_for_business_day(
            date(2024, 1, 13), "modified_following"
        ) == date(2024, 1, 15)

    def test_modified_following_cross_month(self):
        # Aug 31, 2024 is Saturday, Sep 2 is Monday (different month)
        # Should use preceding (Aug 30, Friday)
        assert adjust_for_business_day(
            date(2024, 8, 31), "modified_following"
        ) == date(2024, 8, 30)

    def test_modified_preceding_same_month(self):
        # Saturday mid-month moves to Friday
        assert adjust_for_business_day(
            date(2024, 1, 13), "modified_preceding"
        ) == date(2024, 1, 12)

    def test_modified_preceding_cross_month(self):
        # Sep 1, 2024 is Sunday, Aug 30 is Friday (different month)
        # Should use following (Sep 2, Monday)
        assert adjust_for_business_day(
            date(2024, 9, 1), "modified_preceding"
        ) == date(2024, 9, 2)

    def test_weekday_no_change(self):
        # Business day stays the same for all adjustment types
        monday = date(2024, 1, 15)
        assert adjust_for_business_day(monday, "following") == monday
        assert adjust_for_business_day(monday, "preceding") == monday
        assert adjust_for_business_day(monday, "modified_following") == monday


class TestAdjustDueDates:
    """Test adjusting a list of due dates."""

    def test_adjust_list(self):
        due_dates = [
            date(2024, 1, 13),  # Saturday -> Monday
            date(2024, 1, 14),  # Sunday -> Monday
            date(2024, 1, 15),  # Monday -> Monday
        ]
        adjusted = adjust_due_dates(due_dates, "following")
        assert adjusted[0] == date(2024, 1, 15)
        assert adjusted[1] == date(2024, 1, 15)
        assert adjusted[2] == date(2024, 1, 15)

    def test_no_adjustment_returns_same(self):
        due_dates = [date(2024, 1, 13), date(2024, 1, 14)]
        adjusted = adjust_due_dates(due_dates, "no_adjustment")
        assert adjusted == due_dates

    def test_empty_list(self):
        assert adjust_due_dates([], "following") == []


class TestBusinessDaysBetween:
    """Test counting business days between dates."""

    def test_same_date(self):
        assert business_days_between(date(2024, 1, 15), date(2024, 1, 15)) == 0

    def test_one_business_day(self):
        # Monday to Tuesday = 1 business day
        assert business_days_between(date(2024, 1, 15), date(2024, 1, 16)) == 1

    def test_over_weekend(self):
        # Friday to Monday = 1 business day (Monday only)
        assert business_days_between(date(2024, 1, 12), date(2024, 1, 15)) == 1

    def test_full_week(self):
        # Monday to next Monday = 5 business days
        assert business_days_between(date(2024, 1, 15), date(2024, 1, 22)) == 5


class TestAddBusinessDays:
    """Test adding business days to a date."""

    def test_add_one_day(self):
        # Monday + 1 business day = Tuesday
        assert add_business_days(date(2024, 1, 15), 1) == date(2024, 1, 16)

    def test_add_over_weekend(self):
        # Friday + 1 business day = Monday
        assert add_business_days(date(2024, 1, 12), 1) == date(2024, 1, 15)

    def test_add_five_days(self):
        # Monday + 5 business days = next Monday
        assert add_business_days(date(2024, 1, 15), 5) == date(2024, 1, 22)

    def test_add_zero_days(self):
        assert add_business_days(date(2024, 1, 15), 0) == date(2024, 1, 15)

    def test_subtract_days(self):
        # Tuesday - 1 business day = Monday
        assert add_business_days(date(2024, 1, 16), -1) == date(2024, 1, 15)


class TestDefaultAdjustmentType:
    """Test default adjustment type selection."""

    def test_default_is_modified_following(self):
        assert get_default_adjustment_type() == "modified_following"

    def test_with_product_type(self):
        # Currently returns same for all products
        assert get_default_adjustment_type("retail") == "modified_following"
