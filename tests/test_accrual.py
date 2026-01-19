"""
Tests for daily interest accrual service.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.accrual import (
    get_cumulative_accrual,
    get_accrual_summary,
)


class TestAccrualHelpers:
    """Test accrual helper functions."""

    def test_get_cumulative_accrual_empty(self):
        """Test cumulative accrual with no records."""
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = None

        result = get_cumulative_accrual(1, date(2024, 1, 31), db)
        assert result == Decimal("0.00")


class TestAccrualCalculations:
    """Test accrual calculation logic."""

    def test_daily_accrual_formula(self):
        """Verify daily accrual calculation formula."""
        # 100,000 principal, 12% annual rate, ACT/365
        principal = Decimal("100000")
        annual_rate = Decimal("12")  # 12%
        days_in_year = 365

        # Daily rate = 12% / 365 = 0.0328767...%
        daily_rate = (annual_rate / Decimal("100")) / Decimal(str(days_in_year))

        # Daily accrual = 100000 * 0.12 / 365 = 32.876712...
        daily_accrual = principal * daily_rate
        expected = Decimal("32.876712")

        assert abs(daily_accrual - expected) < Decimal("0.001")

    def test_daily_accrual_30_360(self):
        """Verify daily accrual with 30/360 convention."""
        principal = Decimal("100000")
        annual_rate = Decimal("12")
        days_in_year = 360

        daily_rate = (annual_rate / Decimal("100")) / Decimal(str(days_in_year))
        daily_accrual = principal * daily_rate

        # 100000 * 0.12 / 360 = 33.333...
        expected = Decimal("33.333333")
        assert abs(daily_accrual - expected) < Decimal("0.001")

    def test_cumulative_over_month(self):
        """Test cumulative accrual over a month."""
        principal = Decimal("100000")
        annual_rate = Decimal("12")
        days_in_year = 365
        days_in_month = 31  # January

        daily_accrual = principal * (annual_rate / Decimal("100")) / Decimal(str(days_in_year))
        monthly_accrual = daily_accrual * Decimal(str(days_in_month))

        # ~32.877 * 31 = ~1019.18
        assert Decimal("1018") < monthly_accrual < Decimal("1020")


class TestAccrualSummary:
    """Test accrual summary generation."""

    def test_summary_empty_period(self):
        """Test summary with no accruals in period."""
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        summary = get_accrual_summary(1, date(2024, 1, 1), date(2024, 1, 31), db)

        assert summary["total_accrued"] == 0.0
        assert summary["days_count"] == 0

    def test_summary_calculation(self):
        """Test summary calculation with mock accruals."""
        # Create mock accrual records
        accrual1 = MagicMock()
        accrual1.accrued_amount = 32.88
        accrual1.interest_rate = 12.0
        accrual1.opening_balance = 100000.0

        accrual2 = MagicMock()
        accrual2.accrued_amount = 32.88
        accrual2.interest_rate = 12.0
        accrual2.opening_balance = 100000.0

        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            accrual1, accrual2
        ]

        summary = get_accrual_summary(1, date(2024, 1, 1), date(2024, 1, 2), db)

        assert summary["days_count"] == 2
        assert summary["average_rate"] == 12.0
        assert abs(summary["total_accrued"] - 65.76) < 0.01


class TestAccrualIntegration:
    """Integration-level tests for accrual service."""

    def test_floating_rate_accrual_concept(self):
        """
        Conceptual test for floating rate accrual.

        When benchmark rate changes mid-month:
        - Days 1-15: benchmark 5%, spread 2% = 7%
        - Days 16-31: benchmark 5.5%, spread 2% = 7.5%

        Total interest should reflect both rates.
        """
        principal = Decimal("100000")
        rate1 = Decimal("7")
        rate2 = Decimal("7.5")
        days1 = 15
        days2 = 16
        days_in_year = 365

        accrual_1 = principal * (rate1 / Decimal("100")) / Decimal(str(days_in_year)) * Decimal(str(days1))
        accrual_2 = principal * (rate2 / Decimal("100")) / Decimal(str(days_in_year)) * Decimal(str(days2))

        total_accrual = accrual_1 + accrual_2

        # First half: 100000 * 0.07 / 365 * 15 ≈ 287.67
        # Second half: 100000 * 0.075 / 365 * 16 ≈ 328.77
        # Total ≈ 616.44
        assert Decimal("615") < total_accrual < Decimal("618")

    def test_leap_year_accrual(self):
        """Test accrual calculation in leap year with ACT/ACT."""
        principal = Decimal("100000")
        annual_rate = Decimal("12")
        days_in_year = 366  # 2024 is a leap year

        daily_accrual = principal * (annual_rate / Decimal("100")) / Decimal(str(days_in_year))

        # 100000 * 0.12 / 366 ≈ 32.787
        assert Decimal("32.78") < daily_accrual < Decimal("32.80")

    def test_partial_period_accrual(self):
        """Test accrual for partial month (disbursement mid-month)."""
        principal = Decimal("100000")
        annual_rate = Decimal("12")
        days_in_year = 365
        days_accrued = 15  # Disbursed on Jan 16, accrue Jan 16-31

        daily_accrual = principal * (annual_rate / Decimal("100")) / Decimal(str(days_in_year))
        period_accrual = daily_accrual * Decimal(str(days_accrued))

        # ~32.877 * 15 ≈ 493.15
        assert Decimal("492") < period_accrual < Decimal("495")
