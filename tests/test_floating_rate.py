"""
Tests for floating rate calculations and benchmark rate management.
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.floating_rate import (
    _to_decimal,
    get_benchmark_rate,
    get_current_benchmark_rate,
    calculate_effective_rate,
    check_rate_reset_due,
    calculate_next_reset_date,
    get_rate_reset_schedule,
)


class TestToDecimal:
    """Test decimal conversion helper."""

    def test_float_conversion(self):
        assert _to_decimal(12.5) == Decimal("12.5")

    def test_int_conversion(self):
        assert _to_decimal(12) == Decimal("12")

    def test_decimal_passthrough(self):
        d = Decimal("12.5")
        assert _to_decimal(d) is d

    def test_none_returns_zero(self):
        assert _to_decimal(None) == Decimal("0")


class TestCalculateNextResetDate:
    """Test rate reset date calculation."""

    def test_monthly_reset(self):
        next_date = calculate_next_reset_date(date(2024, 1, 15), "monthly")
        assert next_date == date(2024, 2, 15)

    def test_quarterly_reset(self):
        next_date = calculate_next_reset_date(date(2024, 1, 15), "quarterly")
        assert next_date == date(2024, 4, 15)

    def test_semiannual_reset(self):
        next_date = calculate_next_reset_date(date(2024, 1, 15), "semiannual")
        assert next_date == date(2024, 7, 15)

    def test_annual_reset(self):
        next_date = calculate_next_reset_date(date(2024, 1, 15), "annual")
        assert next_date == date(2025, 1, 15)


class TestCheckRateResetDue:
    """Test rate reset due checking."""

    def test_fixed_rate_never_due(self):
        account = MagicMock()
        account.interest_rate_type = "fixed"
        account.next_rate_reset_date = date(2024, 1, 1)

        assert check_rate_reset_due(account, date(2024, 2, 1)) is False

    def test_floating_rate_due(self):
        account = MagicMock()
        account.interest_rate_type = "floating"
        account.next_rate_reset_date = date(2024, 1, 15)

        assert check_rate_reset_due(account, date(2024, 1, 15)) is True
        assert check_rate_reset_due(account, date(2024, 1, 20)) is True

    def test_floating_rate_not_due(self):
        account = MagicMock()
        account.interest_rate_type = "floating"
        account.next_rate_reset_date = date(2024, 1, 15)

        assert check_rate_reset_due(account, date(2024, 1, 10)) is False

    def test_no_reset_date_not_due(self):
        account = MagicMock()
        account.interest_rate_type = "floating"
        account.next_rate_reset_date = None

        assert check_rate_reset_due(account, date(2024, 1, 15)) is False


class TestGetRateResetSchedule:
    """Test rate reset schedule generation."""

    def test_fixed_rate_empty_schedule(self):
        account = MagicMock()
        account.interest_rate_type = "fixed"

        schedule = get_rate_reset_schedule(account, date(2025, 12, 31))
        assert schedule == []

    def test_monthly_reset_schedule(self):
        account = MagicMock()
        account.interest_rate_type = "floating"
        account.next_rate_reset_date = date(2024, 1, 15)
        account.start_date = date(2024, 1, 1)
        account.rate_reset_frequency = "monthly"

        schedule = get_rate_reset_schedule(account, date(2024, 4, 1))

        assert len(schedule) == 3
        assert schedule[0] == date(2024, 1, 15)
        assert schedule[1] == date(2024, 2, 15)
        assert schedule[2] == date(2024, 3, 15)

    def test_quarterly_reset_schedule(self):
        account = MagicMock()
        account.interest_rate_type = "floating"
        account.next_rate_reset_date = date(2024, 1, 1)
        account.start_date = date(2024, 1, 1)
        account.rate_reset_frequency = "quarterly"

        schedule = get_rate_reset_schedule(account, date(2024, 12, 31))

        assert len(schedule) == 4
        assert schedule[0] == date(2024, 1, 1)
        assert schedule[1] == date(2024, 4, 1)
        assert schedule[2] == date(2024, 7, 1)
        assert schedule[3] == date(2024, 10, 1)


class TestCalculateEffectiveRate:
    """Test effective rate calculation."""

    def test_fixed_rate_returns_base_rate(self):
        account = MagicMock()
        account.interest_rate_type = "fixed"
        account.interest_rate = 12.5

        db = MagicMock()
        rate = calculate_effective_rate(account, date(2024, 1, 15), db)

        assert rate == Decimal("12.5")

    def test_floating_rate_no_benchmark(self):
        account = MagicMock()
        account.interest_rate_type = "floating"
        account.benchmark_rate_id = None
        account.interest_rate = 10.0

        db = MagicMock()
        rate = calculate_effective_rate(account, date(2024, 1, 15), db)

        assert rate == Decimal("10.0")

    @patch("app.services.floating_rate.get_current_benchmark_rate")
    def test_floating_rate_with_spread(self, mock_get_benchmark):
        mock_get_benchmark.return_value = Decimal("5.5")

        account = MagicMock()
        account.interest_rate_type = "floating"
        account.benchmark_rate_id = 1
        account.spread = 2.5
        account.floor_rate = None
        account.cap_rate = None

        db = MagicMock()
        rate = calculate_effective_rate(account, date(2024, 1, 15), db)

        # 5.5 + 2.5 = 8.0
        assert rate == Decimal("8.0")

    @patch("app.services.floating_rate.get_current_benchmark_rate")
    def test_floating_rate_with_floor(self, mock_get_benchmark):
        mock_get_benchmark.return_value = Decimal("3.0")

        account = MagicMock()
        account.interest_rate_type = "floating"
        account.benchmark_rate_id = 1
        account.spread = 1.0
        account.floor_rate = 6.0  # Floor is higher
        account.cap_rate = None

        db = MagicMock()
        rate = calculate_effective_rate(account, date(2024, 1, 15), db)

        # 3.0 + 1.0 = 4.0, but floor is 6.0
        assert rate == Decimal("6.0")

    @patch("app.services.floating_rate.get_current_benchmark_rate")
    def test_floating_rate_with_cap(self, mock_get_benchmark):
        mock_get_benchmark.return_value = Decimal("8.0")

        account = MagicMock()
        account.interest_rate_type = "floating"
        account.benchmark_rate_id = 1
        account.spread = 3.0
        account.floor_rate = None
        account.cap_rate = 10.0  # Cap is lower

        db = MagicMock()
        rate = calculate_effective_rate(account, date(2024, 1, 15), db)

        # 8.0 + 3.0 = 11.0, but cap is 10.0
        assert rate == Decimal("10.0")

    @patch("app.services.floating_rate.get_current_benchmark_rate")
    def test_floating_rate_within_bounds(self, mock_get_benchmark):
        mock_get_benchmark.return_value = Decimal("6.0")

        account = MagicMock()
        account.interest_rate_type = "floating"
        account.benchmark_rate_id = 1
        account.spread = 2.0
        account.floor_rate = 5.0
        account.cap_rate = 12.0

        db = MagicMock()
        rate = calculate_effective_rate(account, date(2024, 1, 15), db)

        # 6.0 + 2.0 = 8.0 (within 5.0-12.0 bounds)
        assert rate == Decimal("8.0")
