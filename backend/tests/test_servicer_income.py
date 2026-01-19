"""
Tests for Servicer Income service.
"""

import pytest
from datetime import date
from decimal import Decimal


class TestServicerFeeCalculation:
    """Tests for servicer fee calculation."""

    def test_servicer_fee_monthly(self):
        """Test monthly servicer fee calculation."""
        portfolio_outstanding = Decimal("10000000")  # 1 Cr
        servicer_fee_rate = Decimal("0.5")  # 0.5% p.a.
        days = 30

        fee = portfolio_outstanding * servicer_fee_rate / 100 * days / 365
        expected = Decimal("10000000") * Decimal("0.005") * Decimal("30") / Decimal("365")

        assert fee.quantize(Decimal("0.01")) == expected.quantize(Decimal("0.01"))

    def test_servicer_fee_quarterly(self):
        """Test quarterly servicer fee calculation."""
        portfolio_outstanding = Decimal("10000000")
        servicer_fee_rate = Decimal("0.5")
        days = 90

        fee = portfolio_outstanding * servicer_fee_rate / 100 * days / 365
        monthly_fee = portfolio_outstanding * servicer_fee_rate / 100 * 30 / 365

        assert fee > monthly_fee * 2  # Quarterly > 2 months

    def test_minimum_servicer_fee(self):
        """Test minimum servicer fee enforcement."""
        calculated_fee = Decimal("3000")
        min_fee = Decimal("5000")

        actual_fee = max(calculated_fee, min_fee)
        assert actual_fee == Decimal("5000")

    def test_gst_on_servicer_fee(self):
        """Test GST calculation on servicer fee."""
        servicer_fee = Decimal("50000")
        gst_rate = Decimal("18")

        gst = servicer_fee * gst_rate / 100
        total_fee = servicer_fee + gst

        assert gst == Decimal("9000")
        assert total_fee == Decimal("59000")


class TestExcessSpread:
    """Tests for excess interest spread calculation."""

    def test_excess_spread_calculation(self):
        """Test excess spread calculation."""
        borrower_rate = Decimal("14")  # 14% p.a.
        lender_yield = Decimal("10")  # 10% p.a.

        excess_spread_rate = borrower_rate - lender_yield
        assert excess_spread_rate == Decimal("4")  # 4%

    def test_excess_spread_amount(self):
        """Test excess spread amount for a period."""
        principal = Decimal("100000")
        excess_rate = Decimal("4")  # 4% p.a.
        days = 30

        excess_amount = principal * excess_rate / 100 * days / 365
        expected = Decimal("100000") * Decimal("0.04") * Decimal("30") / Decimal("365")

        assert excess_amount.quantize(Decimal("0.01")) == expected.quantize(Decimal("0.01"))

    def test_excess_spread_sharing(self):
        """Test excess spread sharing between parties."""
        excess_amount = Decimal("10000")
        servicer_share_percent = Decimal("70")

        servicer_share = excess_amount * servicer_share_percent / 100
        lender_share = excess_amount - servicer_share

        assert servicer_share == Decimal("7000")
        assert lender_share == Decimal("3000")

    def test_no_excess_spread_same_rate(self):
        """Test no excess spread when rates are equal."""
        borrower_rate = Decimal("12")
        lender_yield = Decimal("12")

        excess_spread_rate = max(Decimal("0"), borrower_rate - lender_yield)
        assert excess_spread_rate == Decimal("0")

    def test_excess_spread_cap(self):
        """Test excess spread cap."""
        gross_excess_spread = Decimal("15000")
        cap_amount = Decimal("10000")

        capped_spread = min(gross_excess_spread, cap_amount)
        assert capped_spread == Decimal("10000")


class TestWithholding:
    """Tests for withholding from collections."""

    def test_withholding_calculation(self):
        """Test servicer fee withholding from collection."""
        collection_amount = Decimal("22000")  # EMI
        servicer_fee_rate = Decimal("0.5")
        days = 30

        # Simplified: fee based on collection
        servicer_fee_withheld = collection_amount * servicer_fee_rate / 100 * days / 365
        net_to_lender = collection_amount - servicer_fee_withheld

        assert net_to_lender < collection_amount

    def test_excess_spread_withholding(self):
        """Test excess spread withholding."""
        interest_collected = Decimal("5000")
        borrower_rate = Decimal("14")
        lender_yield = Decimal("10")

        # Excess spread portion of interest
        excess_spread_withheld = interest_collected * (borrower_rate - lender_yield) / borrower_rate
        lender_interest = interest_collected - excess_spread_withheld

        expected_withheld = Decimal("5000") * Decimal("4") / Decimal("14")
        assert excess_spread_withheld.quantize(Decimal("0.01")) == expected_withheld.quantize(Decimal("0.01"))

    def test_lender_share_calculation(self):
        """Test lender's share of collection."""
        collection = Decimal("22000")
        lender_share_percent = Decimal("80")

        lender_collection = collection * lender_share_percent / 100
        assert lender_collection == Decimal("17600")


class TestIncomeAccrual:
    """Tests for income accrual calculations."""

    def test_servicer_total_income(self):
        """Test total servicer income calculation."""
        servicer_fee = Decimal("50000")
        excess_spread = Decimal("30000")
        performance_fee = Decimal("10000")

        total_income = servicer_fee + excess_spread + performance_fee
        assert total_income == Decimal("90000")

    def test_lender_interest_income(self):
        """Test lender interest income calculation."""
        portfolio_outstanding = Decimal("10000000")
        lender_yield = Decimal("10")  # 10% p.a.
        days = 30

        lender_interest = portfolio_outstanding * lender_yield / 100 * days / 365
        expected = Decimal("10000000") * Decimal("0.10") * Decimal("30") / Decimal("365")

        assert lender_interest.quantize(Decimal("0.01")) == expected.quantize(Decimal("0.01"))

    def test_tds_on_interest(self):
        """Test TDS deduction on lender interest."""
        lender_interest = Decimal("82192")  # ~1 month interest on 1 Cr at 10%
        tds_rate = Decimal("10")

        tds = lender_interest * tds_rate / 100
        net_interest = lender_interest - tds

        assert tds == Decimal("8219.2")
        assert net_interest == Decimal("73972.8")


class TestIncomeDistribution:
    """Tests for income distribution to parties."""

    def test_servicer_distribution(self):
        """Test servicer income distribution."""
        gross_income = Decimal("90000")
        gst_collected = Decimal("16200")

        # Servicer receives gross (GST is passed to government)
        net_to_servicer = gross_income
        assert net_to_servicer == Decimal("90000")

    def test_lender_distribution(self):
        """Test lender income distribution."""
        gross_interest = Decimal("82192")
        tds_deducted = Decimal("8219")

        net_to_lender = gross_interest - tds_deducted
        assert net_to_lender == Decimal("73973")


class TestPerformanceFee:
    """Tests for performance-linked servicer fee."""

    def test_performance_fee_earned(self):
        """Test performance fee when threshold met."""
        expected_collection = Decimal("1000000")
        actual_collection = Decimal("980000")
        threshold_rate = Decimal("95")  # 95% collection rate
        performance_fee_rate = Decimal("0.1")  # 0.1% of collections

        collection_rate = actual_collection / expected_collection * 100

        if collection_rate >= threshold_rate:
            performance_fee = actual_collection * performance_fee_rate / 100
        else:
            performance_fee = Decimal("0")

        assert collection_rate == Decimal("98")
        assert performance_fee == Decimal("980")

    def test_performance_fee_not_earned(self):
        """Test performance fee not earned below threshold."""
        expected_collection = Decimal("1000000")
        actual_collection = Decimal("900000")
        threshold_rate = Decimal("95")

        collection_rate = actual_collection / expected_collection * 100

        if collection_rate >= threshold_rate:
            performance_fee = Decimal("1000")
        else:
            performance_fee = Decimal("0")

        assert collection_rate == Decimal("90")
        assert performance_fee == Decimal("0")


class TestSLAPenalty:
    """Tests for SLA breach penalty."""

    def test_sla_penalty_calculation(self):
        """Test SLA penalty calculation."""
        portfolio_outstanding = Decimal("10000000")
        sla_penalty_rate = Decimal("0.05")  # 0.05% p.a.
        days_breached = 15

        penalty = portfolio_outstanding * sla_penalty_rate / 100 * days_breached / 365
        assert penalty > Decimal("0")

    def test_penalty_deduction(self):
        """Test penalty deduction from servicer fee."""
        servicer_fee = Decimal("50000")
        sla_penalty = Decimal("2000")

        net_servicer_fee = servicer_fee - sla_penalty
        assert net_servicer_fee == Decimal("48000")


class TestCumulativeTracking:
    """Tests for cumulative income tracking."""

    def test_cumulative_excess_spread(self):
        """Test cumulative excess spread tracking."""
        previous_cumulative = Decimal("100000")
        current_period_spread = Decimal("10000")

        new_cumulative = previous_cumulative + current_period_spread
        assert new_cumulative == Decimal("110000")

    def test_cumulative_servicer_fee(self):
        """Test cumulative servicer fee tracking."""
        monthly_fees = [Decimal("50000")] * 12  # 1 year
        cumulative = sum(monthly_fees)

        assert cumulative == Decimal("600000")


class TestCollectionEfficiency:
    """Tests for collection efficiency metrics."""

    def test_collection_rate(self):
        """Test collection rate calculation."""
        expected_collection = Decimal("1000000")
        actual_collection = Decimal("950000")

        collection_rate = actual_collection / expected_collection * 100
        assert collection_rate == Decimal("95")

    def test_principal_interest_split(self):
        """Test principal/interest split in collection."""
        total_collection = Decimal("22000")
        principal_portion = Decimal("17000")
        interest_portion = Decimal("5000")

        assert principal_portion + interest_portion == total_collection
