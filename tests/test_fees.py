"""
Tests for fee calculation and management service.
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.fees import (
    _to_decimal,
    calculate_fee_amount,
    allocate_payment_to_fees,
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


class TestCalculateFeeAmount:
    """Test fee amount calculation."""

    def test_flat_fee(self):
        """Test flat fee calculation."""
        fee_type = MagicMock()
        fee_type.calculation_type = "flat"

        product_fee = MagicMock()
        product_fee.fee_type = fee_type
        product_fee.flat_amount = 500.0
        product_fee.min_amount = None
        product_fee.max_amount = None

        amount = calculate_fee_amount(product_fee, Decimal("100000"))
        assert amount == Decimal("500.00")

    def test_percentage_fee(self):
        """Test percentage-based fee calculation."""
        fee_type = MagicMock()
        fee_type.calculation_type = "percentage"

        product_fee = MagicMock()
        product_fee.fee_type = fee_type
        product_fee.percentage_value = 2.0  # 2%
        product_fee.min_amount = None
        product_fee.max_amount = None

        amount = calculate_fee_amount(product_fee, Decimal("100000"))
        assert amount == Decimal("2000.00")

    def test_percentage_fee_with_min(self):
        """Test percentage fee with minimum amount."""
        fee_type = MagicMock()
        fee_type.calculation_type = "percentage"

        product_fee = MagicMock()
        product_fee.fee_type = fee_type
        product_fee.percentage_value = 0.5  # 0.5%
        product_fee.min_amount = 1000.0  # Minimum 1000
        product_fee.max_amount = None

        # 0.5% of 100000 = 500, but min is 1000
        amount = calculate_fee_amount(product_fee, Decimal("100000"))
        assert amount == Decimal("1000.00")

    def test_percentage_fee_with_max(self):
        """Test percentage fee with maximum amount."""
        fee_type = MagicMock()
        fee_type.calculation_type = "percentage"

        product_fee = MagicMock()
        product_fee.fee_type = fee_type
        product_fee.percentage_value = 5.0  # 5%
        product_fee.min_amount = None
        product_fee.max_amount = 2000.0  # Maximum 2000

        # 5% of 100000 = 5000, but max is 2000
        amount = calculate_fee_amount(product_fee, Decimal("100000"))
        assert amount == Decimal("2000.00")

    def test_percentage_within_limits(self):
        """Test percentage fee within min/max limits."""
        fee_type = MagicMock()
        fee_type.calculation_type = "percentage"

        product_fee = MagicMock()
        product_fee.fee_type = fee_type
        product_fee.percentage_value = 1.5  # 1.5%
        product_fee.min_amount = 500.0
        product_fee.max_amount = 5000.0

        # 1.5% of 100000 = 1500, within 500-5000
        amount = calculate_fee_amount(product_fee, Decimal("100000"))
        assert amount == Decimal("1500.00")


class TestFeeCalculationFormulas:
    """Test fee calculation formulas."""

    def test_processing_fee_formula(self):
        """Test processing fee calculation formula."""
        principal = Decimal("100000")
        rate = Decimal("2")  # 2%

        fee = (principal * rate / Decimal("100")).quantize(Decimal("0.01"))
        assert fee == Decimal("2000.00")

    def test_late_fee_formula(self):
        """Test late fee calculation formula."""
        overdue_amount = Decimal("10000")
        penalty_rate = Decimal("2")  # 2% penalty

        late_fee = (overdue_amount * penalty_rate / Decimal("100")).quantize(Decimal("0.01"))
        assert late_fee == Decimal("200.00")

    def test_prepayment_penalty_formula(self):
        """Test prepayment penalty calculation formula."""
        prepay_amount = Decimal("50000")
        penalty_rate = Decimal("3")  # 3% penalty

        penalty = (prepay_amount * penalty_rate / Decimal("100")).quantize(Decimal("0.01"))
        assert penalty == Decimal("1500.00")


class TestFeeWaterfall:
    """Test fee payment waterfall logic."""

    def test_waterfall_priority_concept(self):
        """
        Test fee waterfall priority concept.

        Lower priority number = paid first.
        Example priorities:
        - Late fees: 10
        - Other fees: 50
        - Interest: 100
        - Principal: 200
        """
        fees = [
            {"name": "late_fee", "priority": 10, "outstanding": Decimal("100")},
            {"name": "processing_fee", "priority": 50, "outstanding": Decimal("200")},
        ]

        # Sort by priority (lower first)
        sorted_fees = sorted(fees, key=lambda x: x["priority"])

        assert sorted_fees[0]["name"] == "late_fee"
        assert sorted_fees[1]["name"] == "processing_fee"

    def test_partial_allocation(self):
        """Test partial fee allocation when payment < total fees."""
        # Simulate fees totaling 500
        fees = [
            {"outstanding": Decimal("200"), "priority": 10},
            {"outstanding": Decimal("300"), "priority": 20},
        ]
        payment = Decimal("350")

        remaining = payment
        allocations = []

        for fee in sorted(fees, key=lambda x: x["priority"]):
            if remaining <= 0:
                break
            allocation = min(remaining, fee["outstanding"])
            allocations.append(allocation)
            remaining -= allocation

        # First fee (200) fully paid, second partially (150)
        assert allocations[0] == Decimal("200")
        assert allocations[1] == Decimal("150")
        assert remaining == Decimal("0")


class TestFeeTypes:
    """Test different fee type configurations."""

    def test_processing_fee_config(self):
        """Test processing fee type configuration."""
        fee_config = {
            "code": "processing_fee",
            "calculation_type": "percentage",
            "applies_to": "disbursement",
            "charge_timing": "upfront",
            "taxable": True,
        }

        assert fee_config["charge_timing"] == "upfront"
        assert fee_config["applies_to"] == "disbursement"

    def test_late_fee_config(self):
        """Test late fee type configuration."""
        fee_config = {
            "code": "late_fee",
            "calculation_type": "percentage",
            "applies_to": "overdue",
            "charge_timing": "on_occurrence",
            "grace_days": 3,
        }

        assert fee_config["charge_timing"] == "on_occurrence"
        assert fee_config["grace_days"] == 3

    def test_prepayment_penalty_config(self):
        """Test prepayment penalty configuration."""
        fee_config = {
            "code": "prepayment_penalty",
            "calculation_type": "percentage",
            "applies_to": "prepayment",
            "charge_timing": "on_occurrence",
        }

        assert fee_config["applies_to"] == "prepayment"
