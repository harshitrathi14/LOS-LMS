"""
Tests for enhanced amortization schedule generation.

Tests the integration of day-count conventions, payment frequencies,
and business day adjustments in schedule generation.
"""

import pytest
from datetime import date
from decimal import Decimal

from app.services.schedule import (
    generate_amortization_schedule,
    generate_schedule_simple,
    calculate_total_interest,
    calculate_total_payment,
    recalculate_schedule_from_installment,
)


class TestGenerateAmortizationSchedule:
    """Test enhanced amortization schedule generation."""

    def test_basic_monthly_emi(self):
        """Test standard monthly EMI schedule generation."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            schedule_type="emi",
            repayment_frequency="monthly",
        )

        assert len(schedule) == 12
        assert schedule[0]["installment_number"] == 1
        assert schedule[0]["due_date"] == date(2024, 2, 1)
        assert schedule[11]["installment_number"] == 12
        assert schedule[11]["due_date"] == date(2025, 1, 1)

        # Verify closing balance is 0 at end
        assert schedule[11]["closing_balance"] == 0.0

    def test_principal_sum_equals_original(self):
        """Total principal paid should equal original principal."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
        )

        total_principal = sum(item["principal_due"] for item in schedule)
        assert abs(total_principal - 100000) < 0.01

    def test_interest_only_schedule(self):
        """Test interest-only schedule."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            schedule_type="interest_only",
        )

        # First 11 installments should have zero principal
        for item in schedule[:-1]:
            assert item["principal_due"] == 0.0

        # Last installment should have full principal
        assert schedule[-1]["principal_due"] == 100000.0

    def test_bullet_schedule(self):
        """Test bullet (single payment at end) schedule."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            schedule_type="bullet",
        )

        # All intermediate principal should be 0
        for item in schedule[:-1]:
            assert item["principal_due"] == 0.0

        # Last installment should have full principal
        assert schedule[-1]["principal_due"] == 100000.0

    def test_quarterly_frequency(self):
        """Test quarterly payment frequency."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            repayment_frequency="quarterly",
        )

        # 12 months / quarterly = 4 periods
        assert len(schedule) == 4
        assert schedule[0]["due_date"] == date(2024, 4, 1)
        assert schedule[3]["due_date"] == date(2025, 1, 1)

    def test_weekly_frequency(self):
        """Test weekly payment frequency."""
        schedule = generate_amortization_schedule(
            principal=10000,
            annual_rate=12,
            tenure_months=1,  # ~4 weeks
            start_date=date(2024, 1, 1),
            repayment_frequency="weekly",
        )

        # 1 month ≈ 4 weeks
        assert len(schedule) == 4
        assert schedule[0]["due_date"] == date(2024, 1, 8)

    def test_30_360_day_count(self):
        """Test 30/360 day count convention."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            day_count_convention="30/360",
        )

        # First interest payment should be based on 30/360
        # 100000 * 0.12 * (30/360) = 1000.00
        first_interest = schedule[0]["interest_due"]
        assert abs(first_interest - 1000.00) < 1.00  # Allow for rounding

    def test_act_365_day_count(self):
        """Test ACT/365 day count convention."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            day_count_convention="act/365",
        )

        # First period: Jan 1 to Feb 1 = 31 days
        # 100000 * 0.12 * (31/365) ≈ 1019.18
        first_interest = schedule[0]["interest_due"]
        assert 1018 < first_interest < 1020

    def test_act_360_day_count(self):
        """Test ACT/360 day count convention."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            day_count_convention="act/360",
        )

        # First period: Jan 1 to Feb 1 = 31 days
        # 100000 * 0.12 * (31/360) ≈ 1033.33
        first_interest = schedule[0]["interest_due"]
        assert 1032 < first_interest < 1035

    def test_schedule_item_structure(self):
        """Verify schedule item has all required fields."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=3,
            start_date=date(2024, 1, 1),
        )

        item = schedule[0]
        required_fields = [
            "installment_number",
            "due_date",
            "period_start",
            "period_end",
            "principal_due",
            "interest_due",
            "fees_due",
            "total_due",
            "opening_balance",
            "closing_balance",
        ]
        for field in required_fields:
            assert field in item, f"Missing field: {field}"

    def test_zero_interest_rate(self):
        """Test schedule with zero interest rate."""
        schedule = generate_amortization_schedule(
            principal=12000,
            annual_rate=0,
            tenure_months=12,
            start_date=date(2024, 1, 1),
        )

        # All interest should be 0
        total_interest = sum(item["interest_due"] for item in schedule)
        assert total_interest == 0.0

        # Each principal payment should be equal (1000)
        for item in schedule:
            assert abs(item["principal_due"] - 1000.0) < 0.01


class TestBackwardsCompatibility:
    """Test backwards-compatible simple schedule function."""

    def test_simple_schedule_format(self):
        """Test generate_schedule_simple returns old format."""
        schedule = generate_schedule_simple(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
        )

        # Should have old format fields only
        item = schedule[0]
        assert "installment_number" in item
        assert "due_date" in item
        assert "principal_due" in item
        assert "interest_due" in item
        assert "fees_due" in item
        assert "total_due" in item

        # Should NOT have new fields
        assert "period_start" not in item
        assert "opening_balance" not in item


class TestScheduleTotals:
    """Test schedule total calculations."""

    def test_calculate_total_interest(self):
        """Test total interest calculation."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
        )

        total_interest = calculate_total_interest(schedule)
        assert total_interest > Decimal("0")
        # 12% on 100K for 1 year should be roughly 6500-7000
        assert Decimal("6000") < total_interest < Decimal("7500")

    def test_calculate_total_payment(self):
        """Test total payment calculation."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
        )

        total_payment = calculate_total_payment(schedule)
        total_interest = calculate_total_interest(schedule)

        # Total payment = principal + interest
        assert abs(total_payment - (Decimal("100000") + total_interest)) < Decimal("1")


class TestScheduleRecalculation:
    """Test schedule recalculation for rate resets."""

    def test_recalculate_from_middle(self):
        """Test recalculating schedule from middle installment."""
        original_schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
        )

        # Recalculate from installment 7 with new rate
        new_schedule = recalculate_schedule_from_installment(
            existing_schedule=original_schedule,
            from_installment=7,
            outstanding_principal=50000,  # Assume 50K remaining
            annual_rate=10,  # New lower rate
        )

        # Should have 6 installments (7-12)
        assert len(new_schedule) == 6
        assert new_schedule[0]["installment_number"] == 7
        assert new_schedule[5]["installment_number"] == 12


class TestValidationErrors:
    """Test input validation."""

    def test_invalid_tenure(self):
        with pytest.raises(ValueError, match="Tenure must be at least 1"):
            generate_amortization_schedule(
                principal=100000,
                annual_rate=12,
                tenure_months=0,
                start_date=date(2024, 1, 1),
            )

    def test_invalid_principal(self):
        with pytest.raises(ValueError, match="Principal must be positive"):
            generate_amortization_schedule(
                principal=0,
                annual_rate=12,
                tenure_months=12,
                start_date=date(2024, 1, 1),
            )

    def test_invalid_frequency(self):
        with pytest.raises(ValueError, match="Unsupported repayment frequency"):
            generate_amortization_schedule(
                principal=100000,
                annual_rate=12,
                tenure_months=12,
                start_date=date(2024, 1, 1),
                repayment_frequency="daily",
            )

    def test_invalid_schedule_type(self):
        with pytest.raises(ValueError, match="Unsupported schedule type"):
            generate_amortization_schedule(
                principal=100000,
                annual_rate=12,
                tenure_months=12,
                start_date=date(2024, 1, 1),
                schedule_type="unknown",
            )


class TestDayCountConventionComparison:
    """Compare interest amounts across day-count conventions."""

    def test_act_360_higher_than_act_365(self):
        """ACT/360 should produce higher interest than ACT/365."""
        schedule_360 = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            day_count_convention="act/360",
        )
        schedule_365 = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            day_count_convention="act/365",
        )

        total_360 = calculate_total_interest(schedule_360)
        total_365 = calculate_total_interest(schedule_365)

        # ACT/360 divides by 360 (smaller), so interest is higher
        assert total_360 > total_365

    def test_30_360_vs_act_365(self):
        """Compare 30/360 and ACT/365 conventions."""
        schedule_30_360 = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            day_count_convention="30/360",
        )
        schedule_act = generate_amortization_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            day_count_convention="act/365",
        )

        total_30_360 = calculate_total_interest(schedule_30_360)
        total_act = calculate_total_interest(schedule_act)

        # Both should be positive and reasonably close
        assert total_30_360 > 0
        assert total_act > 0
        # Difference should be small (within 5%)
        ratio = float(total_30_360 / total_act)
        assert 0.95 < ratio < 1.05
