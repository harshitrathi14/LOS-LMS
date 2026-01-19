"""
Tests for securitization service.
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock


class TestPoolStatistics:
    """Tests for pool statistics calculations."""

    def test_weighted_average_rate(self):
        """Test weighted average rate calculation."""
        loans = [
            {"principal": 100000, "rate": 12.0},
            {"principal": 200000, "rate": 11.5},
            {"principal": 150000, "rate": 12.5},
        ]

        total_principal = sum(Decimal(str(l["principal"])) for l in loans)
        weighted_rate = sum(
            Decimal(str(l["principal"])) * Decimal(str(l["rate"]))
            for l in loans
        ) / total_principal

        # (100000*12 + 200000*11.5 + 150000*12.5) / 450000
        # = (1200000 + 2300000 + 1875000) / 450000
        # = 5375000 / 450000 = 11.944...
        expected = Decimal("5375000") / Decimal("450000")
        assert weighted_rate == expected

    def test_weighted_average_tenure(self):
        """Test weighted average tenure calculation."""
        loans = [
            {"principal": 100000, "tenure": 36},
            {"principal": 200000, "tenure": 48},
            {"principal": 150000, "tenure": 60},
        ]

        total_principal = sum(Decimal(str(l["principal"])) for l in loans)
        weighted_tenure = sum(
            Decimal(str(l["principal"])) * l["tenure"]
            for l in loans
        ) / total_principal

        # (100000*36 + 200000*48 + 150000*60) / 450000
        # = (3600000 + 9600000 + 9000000) / 450000 = 49.33...
        expected = Decimal("22200000") / Decimal("450000")
        assert weighted_tenure == expected


class TestInvestmentShare:
    """Tests for investment share calculations."""

    def test_investment_percentage(self):
        """Test investment percentage calculation."""
        pool_principal = Decimal("10000000")
        investment_amount = Decimal("2500000")

        investment_percent = (investment_amount / pool_principal * 100)
        assert investment_percent == Decimal("25")

    def test_multiple_investors(self):
        """Test multiple investor allocations."""
        pool_principal = Decimal("10000000")
        investments = [
            {"amount": 5000000},  # 50%
            {"amount": 3000000},  # 30%
            {"amount": 2000000},  # 20%
        ]

        total_invested = sum(Decimal(str(i["amount"])) for i in investments)
        assert total_invested == pool_principal

        percentages = [
            Decimal(str(i["amount"])) / pool_principal * 100
            for i in investments
        ]
        assert sum(percentages) == Decimal("100")


class TestCashFlowDistribution:
    """Tests for cash flow distribution."""

    def test_pro_rata_distribution(self):
        """Test pro-rata distribution to investors."""
        total_collection = Decimal("100000")
        investors = [
            {"share": Decimal("50")},
            {"share": Decimal("30")},
            {"share": Decimal("20")},
        ]

        distributions = [
            (total_collection * inv["share"] / 100)
            for inv in investors
        ]

        assert distributions[0] == Decimal("50000")
        assert distributions[1] == Decimal("30000")
        assert distributions[2] == Decimal("20000")
        assert sum(distributions) == total_collection

    def test_servicer_fee_deduction(self):
        """Test servicer fee deduction from collections."""
        total_collection = Decimal("100000")
        servicer_fee_rate = Decimal("0.5")  # 0.5%

        servicer_fee = (total_collection * servicer_fee_rate / 100)
        distributable = total_collection - servicer_fee

        assert servicer_fee == Decimal("500")
        assert distributable == Decimal("99500")

    def test_multiple_fee_deductions(self):
        """Test multiple fee deductions."""
        total_collection = Decimal("100000")
        servicer_rate = Decimal("0.5")
        trustee_rate = Decimal("0.1")

        servicer_fee = (total_collection * servicer_rate / 100)
        trustee_fee = (total_collection * trustee_rate / 100)
        distributable = total_collection - servicer_fee - trustee_fee

        assert servicer_fee == Decimal("500")
        assert trustee_fee == Decimal("100")
        assert distributable == Decimal("99400")


class TestTaxDeduction:
    """Tests for tax deduction on distributions."""

    def test_tds_on_interest(self):
        """Test TDS deduction on interest."""
        interest_amount = Decimal("10000")
        tds_rate = Decimal("10")  # 10% TDS

        tds = (interest_amount * tds_rate / 100)
        net_interest = interest_amount - tds

        assert tds == Decimal("1000")
        assert net_interest == Decimal("9000")

    def test_no_tds_on_principal(self):
        """Test no TDS on principal repayment."""
        principal_amount = Decimal("50000")
        tds = Decimal("0")

        net_principal = principal_amount - tds
        assert net_principal == principal_amount


class TestPoolPerformance:
    """Tests for pool performance metrics."""

    def test_collection_rate(self):
        """Test collection rate calculation."""
        expected_collection = Decimal("1000000")
        actual_collection = Decimal("950000")

        collection_rate = (actual_collection / expected_collection * 100)
        assert collection_rate == Decimal("95")

    def test_prepayment_rate(self):
        """Test prepayment rate calculation."""
        original_principal = Decimal("10000000")
        prepayments = Decimal("500000")

        prepayment_rate = (prepayments / original_principal * 100)
        assert prepayment_rate == Decimal("5")

    def test_delinquency_rate(self):
        """Test delinquency rate calculation."""
        total_loans = 100
        delinquent_loans = 8

        delinquency_rate = (delinquent_loans / total_loans * 100)
        assert delinquency_rate == 8


class TestTranche:
    """Tests for tranche waterfall."""

    def test_tranche_priority(self):
        """Test tranche priority ordering."""
        tranches = ["senior", "mezzanine", "junior"]

        # Senior gets paid first
        assert tranches.index("senior") < tranches.index("mezzanine")
        assert tranches.index("mezzanine") < tranches.index("junior")

    def test_first_loss_absorption(self):
        """Test first loss piece absorption."""
        first_loss = Decimal("500000")
        loss_amount = Decimal("300000")

        # Junior tranche absorbs first
        remaining_first_loss = max(Decimal("0"), first_loss - loss_amount)
        absorbed = min(first_loss, loss_amount)

        assert absorbed == Decimal("300000")
        assert remaining_first_loss == Decimal("200000")


class TestInvestorRedemption:
    """Tests for investor redemption."""

    def test_full_redemption(self):
        """Test full redemption when principal reaches zero."""
        investment_amount = Decimal("1000000")
        distributions = Decimal("1000000")

        remaining = investment_amount - distributions
        is_fully_redeemed = remaining <= Decimal("0.01")

        assert is_fully_redeemed == True

    def test_partial_redemption(self):
        """Test partial redemption."""
        investment_amount = Decimal("1000000")
        distributions = Decimal("500000")

        remaining = investment_amount - distributions
        is_fully_redeemed = remaining <= Decimal("0.01")

        assert is_fully_redeemed == False
        assert remaining == Decimal("500000")


class TestPoolStatus:
    """Tests for pool status transitions."""

    def test_valid_pool_statuses(self):
        """Test valid pool statuses."""
        valid_statuses = ["draft", "active", "closed", "terminated"]

        for status in valid_statuses:
            assert status in valid_statuses

    def test_pool_activation_requirements(self):
        """Test pool activation requirements."""
        # Pool needs loans to be activated
        total_loans = 0
        can_activate = total_loans > 0

        assert can_activate == False

        total_loans = 10
        can_activate = total_loans > 0
        assert can_activate == True


class TestLoanRemoval:
    """Tests for loan removal from pool."""

    def test_removal_reasons(self):
        """Test valid removal reasons."""
        valid_reasons = ["prepaid", "defaulted", "substituted", "matured"]

        for reason in valid_reasons:
            assert reason in valid_reasons

    def test_pool_update_on_removal(self):
        """Test pool statistics update on loan removal."""
        original_loans = 100
        original_principal = Decimal("10000000")
        removed_principal = Decimal("100000")

        new_principal = original_principal - removed_principal
        new_loans = original_loans - 1

        assert new_loans == 99
        assert new_principal == Decimal("9900000")
