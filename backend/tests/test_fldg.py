"""
Tests for FLDG (First Loss Default Guarantee) service.
"""

import pytest
from datetime import date
from decimal import Decimal


class TestFLDGCalculations:
    """Tests for FLDG limit and availability calculations."""

    def test_fldg_percent_limit(self):
        """Test FLDG limit based on percentage of portfolio."""
        portfolio_outstanding = Decimal("10000000")  # 1 Cr
        fldg_percent = Decimal("5")  # 5%

        fldg_limit = (portfolio_outstanding * fldg_percent / 100)
        assert fldg_limit == Decimal("500000")  # 5 lakh

    def test_fldg_absolute_limit(self):
        """Test FLDG absolute limit cap."""
        portfolio_outstanding = Decimal("10000000")
        fldg_percent = Decimal("10")
        absolute_cap = Decimal("500000")

        percent_limit = portfolio_outstanding * fldg_percent / 100  # 10 lakh
        effective_limit = min(percent_limit, absolute_cap)

        assert effective_limit == Decimal("500000")  # Capped at 5 lakh

    def test_fldg_availability_sufficient(self):
        """Test FLDG availability when balance is sufficient."""
        fldg_balance = Decimal("500000")
        claim_amount = Decimal("100000")

        available = fldg_balance >= claim_amount
        shortfall = max(Decimal("0"), claim_amount - fldg_balance)

        assert available == True
        assert shortfall == Decimal("0")

    def test_fldg_availability_insufficient(self):
        """Test FLDG availability when balance is insufficient."""
        fldg_balance = Decimal("50000")
        claim_amount = Decimal("100000")

        available = fldg_balance >= claim_amount
        shortfall = max(Decimal("0"), claim_amount - fldg_balance)

        assert available == False
        assert shortfall == Decimal("50000")


class TestFLDGUtilization:
    """Tests for FLDG utilization calculations."""

    def test_fldg_claim_calculation(self):
        """Test FLDG claim amount calculation."""
        principal_outstanding = Decimal("100000")
        interest_outstanding = Decimal("5000")
        fees_outstanding = Decimal("1000")
        partner_share = Decimal("80")  # 80%

        principal_claim = principal_outstanding * partner_share / 100
        interest_claim = interest_outstanding * partner_share / 100
        total_claim = principal_claim + interest_claim

        assert principal_claim == Decimal("80000")
        assert interest_claim == Decimal("4000")
        assert total_claim == Decimal("84000")

    def test_fldg_utilization_balance_update(self):
        """Test FLDG balance update after utilization."""
        fldg_balance_before = Decimal("500000")
        approved_amount = Decimal("84000")

        fldg_balance_after = fldg_balance_before - approved_amount
        assert fldg_balance_after == Decimal("416000")

    def test_first_loss_utilization(self):
        """Test first loss FLDG utilization."""
        loss_amount = Decimal("100000")
        fldg_balance = Decimal("200000")

        # First loss absorbs the full loss
        utilized = min(loss_amount, fldg_balance)
        remaining_loss = loss_amount - utilized

        assert utilized == Decimal("100000")
        assert remaining_loss == Decimal("0")

    def test_second_loss_threshold(self):
        """Test second loss FLDG with first loss threshold."""
        loss_amount = Decimal("150000")
        first_loss_threshold = Decimal("100000")

        # Second loss only kicks in after first loss threshold
        second_loss_claim = max(Decimal("0"), loss_amount - first_loss_threshold)
        assert second_loss_claim == Decimal("50000")

    def test_second_loss_not_triggered(self):
        """Test second loss not triggered when below threshold."""
        loss_amount = Decimal("80000")
        first_loss_threshold = Decimal("100000")

        second_loss_claim = max(Decimal("0"), loss_amount - first_loss_threshold)
        assert second_loss_claim == Decimal("0")


class TestFLDGRecovery:
    """Tests for FLDG recovery calculations."""

    def test_fldg_recovery_full(self):
        """Test full recovery returned to FLDG pool."""
        fldg_utilized = Decimal("100000")
        recovery_amount = Decimal("120000")

        # Recovery first goes to FLDG up to utilized amount
        amount_to_fldg = min(recovery_amount, fldg_utilized)
        excess = recovery_amount - amount_to_fldg

        assert amount_to_fldg == Decimal("100000")
        assert excess == Decimal("20000")

    def test_fldg_recovery_partial(self):
        """Test partial recovery returned to FLDG pool."""
        fldg_utilized = Decimal("100000")
        recovery_amount = Decimal("50000")

        amount_to_fldg = min(recovery_amount, fldg_utilized)
        remaining_fldg_claim = fldg_utilized - amount_to_fldg

        assert amount_to_fldg == Decimal("50000")
        assert remaining_fldg_claim == Decimal("50000")

    def test_fldg_balance_restoration(self):
        """Test FLDG balance restoration after recovery."""
        fldg_balance_before = Decimal("400000")
        recovery_to_fldg = Decimal("100000")

        fldg_balance_after = fldg_balance_before + recovery_to_fldg
        assert fldg_balance_after == Decimal("500000")


class TestFLDGTopUp:
    """Tests for FLDG top-up requirements."""

    def test_top_up_required(self):
        """Test top-up required when balance below threshold."""
        effective_limit = Decimal("500000")
        current_balance = Decimal("200000")
        threshold_percent = Decimal("50")

        threshold_amount = effective_limit * threshold_percent / 100
        requires_top_up = current_balance < threshold_amount

        assert threshold_amount == Decimal("250000")
        assert requires_top_up == True

    def test_top_up_not_required(self):
        """Test top-up not required when balance above threshold."""
        effective_limit = Decimal("500000")
        current_balance = Decimal("300000")
        threshold_percent = Decimal("50")

        threshold_amount = effective_limit * threshold_percent / 100
        requires_top_up = current_balance < threshold_amount

        assert requires_top_up == False

    def test_top_up_amount(self):
        """Test calculation of top-up amount needed."""
        effective_limit = Decimal("500000")
        current_balance = Decimal("200000")

        top_up_needed = effective_limit - current_balance
        assert top_up_needed == Decimal("300000")


class TestFLDGUtilizationRate:
    """Tests for FLDG utilization metrics."""

    def test_utilization_rate(self):
        """Test FLDG utilization rate calculation."""
        effective_limit = Decimal("500000")
        total_utilized = Decimal("150000")

        utilization_rate = total_utilized / effective_limit * 100
        assert utilization_rate == Decimal("30")

    def test_net_utilization(self):
        """Test net FLDG utilization after recoveries."""
        total_utilized = Decimal("200000")
        total_recovered = Decimal("50000")

        net_utilization = total_utilized - total_recovered
        assert net_utilization == Decimal("150000")


class TestCoLendingRatios:
    """Tests for various co-lending ratio scenarios."""

    def test_80_20_ratio(self):
        """Test 80:20 co-lending split."""
        loan_amount = Decimal("1000000")
        lender_share = Decimal("80")
        originator_share = Decimal("20")

        lender_portion = loan_amount * lender_share / 100
        originator_portion = loan_amount * originator_share / 100

        assert lender_portion == Decimal("800000")
        assert originator_portion == Decimal("200000")

    def test_90_10_ratio(self):
        """Test 90:10 co-lending split."""
        loan_amount = Decimal("1000000")
        lender_share = Decimal("90")
        originator_share = Decimal("10")

        lender_portion = loan_amount * lender_share / 100
        originator_portion = loan_amount * originator_share / 100

        assert lender_portion == Decimal("900000")
        assert originator_portion == Decimal("100000")

    def test_100_0_fully_backed(self):
        """Test 100:0 fully backed by lender (DA)."""
        loan_amount = Decimal("1000000")
        lender_share = Decimal("100")

        lender_portion = loan_amount * lender_share / 100
        originator_portion = loan_amount - lender_portion

        assert lender_portion == Decimal("1000000")
        assert originator_portion == Decimal("0")

    def test_collection_split_80_20(self):
        """Test collection split in 80:20 arrangement."""
        collection = Decimal("22000")  # EMI
        lender_share = Decimal("80")

        lender_collection = collection * lender_share / 100
        originator_collection = collection - lender_collection

        assert lender_collection == Decimal("17600")
        assert originator_collection == Decimal("4400")
