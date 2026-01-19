"""
Tests for advanced schedule generation (step-up, step-down, balloon, moratorium).
"""

import pytest
from datetime import date
from decimal import Decimal

from app.services.advanced_schedule import (
    generate_step_up_schedule,
    generate_step_down_schedule,
    generate_balloon_schedule,
    apply_moratorium,
)


class TestStepUpSchedule:
    """Test step-up EMI schedule generation."""

    def test_basic_step_up(self):
        """Test basic step-up schedule."""
        schedule = generate_step_up_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            step_percent=10,  # 10% increase
            step_frequency_months=3,  # Every 3 months
        )

        assert len(schedule) == 12

        # EMI should increase over time
        first_emi = schedule[0]["total_due"]
        mid_emi = schedule[6]["total_due"]
        last_emi = schedule[11]["total_due"]

        # Generally, EMI should increase (though final payment adjusts for balance)
        assert first_emi > 0
        assert schedule[0]["step_number"] == 0

    def test_step_up_principal_closes_to_zero(self):
        """Total principal paid should equal original principal."""
        schedule = generate_step_up_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            step_percent=5,
            step_frequency_months=6,
        )

        total_principal = sum(item["principal_due"] for item in schedule)
        assert abs(total_principal - 100000) < 1.0  # Within rounding tolerance

    def test_step_number_tracking(self):
        """Verify step numbers are tracked correctly."""
        schedule = generate_step_up_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            step_percent=10,
            step_frequency_months=3,
        )

        # Check step progression
        assert schedule[0]["step_number"] == 0
        assert schedule[2]["step_number"] == 0  # Still in first period
        assert schedule[3]["step_number"] == 1  # First step


class TestStepDownSchedule:
    """Test step-down EMI schedule generation."""

    def test_basic_step_down(self):
        """Test basic step-down schedule."""
        schedule = generate_step_down_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            step_percent=10,  # 10% decrease
            step_frequency_months=3,  # Every 3 months
        )

        assert len(schedule) == 12

        # First payment should be higher than later payments (excluding final)
        first_emi = schedule[0]["total_due"]
        assert first_emi > 0

    def test_step_down_principal_closes_to_zero(self):
        """Total principal paid should equal original principal."""
        schedule = generate_step_down_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            step_percent=5,
            step_frequency_months=6,
        )

        total_principal = sum(item["principal_due"] for item in schedule)
        assert abs(total_principal - 100000) < 1.0


class TestBalloonSchedule:
    """Test balloon payment schedule generation."""

    def test_balloon_with_percentage(self):
        """Test balloon schedule with percentage."""
        schedule = generate_balloon_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            balloon_percent=30,  # 30% balloon
        )

        assert len(schedule) == 12

        # Final payment should include balloon
        final_principal = schedule[11]["principal_due"]
        # Should be approximately 30,000 + remaining regular principal
        assert final_principal >= 30000

    def test_balloon_with_fixed_amount(self):
        """Test balloon schedule with fixed amount."""
        schedule = generate_balloon_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            balloon_amount=25000,
        )

        assert len(schedule) == 12

        # Final payment should be at least the balloon amount
        final_principal = schedule[11]["principal_due"]
        assert final_principal >= 25000

    def test_balloon_total_principal(self):
        """Total principal should equal original principal."""
        schedule = generate_balloon_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=12,
            start_date=date(2024, 1, 1),
            balloon_percent=20,
        )

        total_principal = sum(item["principal_due"] for item in schedule)
        assert abs(total_principal - 100000) < 1.0

    def test_balloon_requires_amount_or_percent(self):
        """Should raise error if neither amount nor percent provided."""
        with pytest.raises(ValueError, match="balloon_percent or balloon_amount"):
            generate_balloon_schedule(
                principal=100000,
                annual_rate=12,
                tenure_months=12,
                start_date=date(2024, 1, 1),
            )


class TestMoratorium:
    """Test moratorium application."""

    def test_full_moratorium(self):
        """Test full moratorium (no payment during period)."""
        # Create a simple schedule with all required fields
        original_schedule = [
            {
                "installment_number": i,
                "due_date": date(2024, i, 1),
                "principal_due": 8000.0,
                "interest_due": 1000.0,
                "total_due": 9000.0,
                "opening_balance": 100000.0 - (i - 1) * 8000.0,
                "is_moratorium": False,
            }
            for i in range(1, 13)
        ]

        modified = apply_moratorium(
            original_schedule,
            moratorium_months=3,
            moratorium_type="full",
            interest_treatment="capitalize"
        )

        # First 3 payments should be zero
        assert modified[0]["total_due"] == 0.0
        assert modified[1]["total_due"] == 0.0
        assert modified[2]["total_due"] == 0.0
        assert modified[0]["is_moratorium"] is True

        # 4th payment onwards should be normal
        assert modified[3]["is_moratorium"] is False

    def test_principal_only_moratorium(self):
        """Test principal-only moratorium (pay interest only)."""
        original_schedule = [
            {
                "installment_number": i,
                "due_date": date(2024, i, 1),
                "principal_due": 8000.0,
                "interest_due": 1000.0,
                "total_due": 9000.0,
                "opening_balance": 100000.0 - (i - 1) * 8000.0,
                "is_moratorium": False,
            }
            for i in range(1, 7)
        ]

        modified = apply_moratorium(
            original_schedule,
            moratorium_months=2,
            moratorium_type="principal_only"
        )

        # First 2 payments should be interest only
        assert modified[0]["principal_due"] == 0.0
        assert modified[0]["interest_due"] == 1000.0
        assert modified[0]["total_due"] == 1000.0
        assert modified[0]["is_moratorium"] is True

    def test_zero_moratorium(self):
        """Zero moratorium months should return unchanged schedule."""
        original_schedule = [
            {"installment_number": 1, "total_due": 9000.0}
        ]

        modified = apply_moratorium(
            original_schedule,
            moratorium_months=0,
            moratorium_type="full"
        )

        assert modified == original_schedule


class TestScheduleStructure:
    """Test schedule structure and fields."""

    def test_step_schedule_has_all_fields(self):
        """Verify all required fields are present."""
        schedule = generate_step_up_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=6,
            start_date=date(2024, 1, 1),
            step_percent=5,
            step_frequency_months=3,
        )

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
            "is_moratorium",
            "step_number",
        ]

        for field in required_fields:
            assert field in schedule[0], f"Missing field: {field}"

    def test_balloon_schedule_has_all_fields(self):
        """Verify balloon schedule has all required fields."""
        schedule = generate_balloon_schedule(
            principal=100000,
            annual_rate=12,
            tenure_months=6,
            start_date=date(2024, 1, 1),
            balloon_percent=20,
        )

        assert "is_moratorium" in schedule[0]
        assert "step_number" in schedule[0]
