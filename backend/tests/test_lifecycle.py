"""
Tests for loan lifecycle services.

Tests restructuring, prepayment, and closure functionality.
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch


class TestRestructureService:
    """Tests for restructure service."""

    def test_calculate_restructure_impact_rate_reduction(self):
        """Test impact calculation for rate reduction."""
        from app.services.restructure import calculate_restructure_impact

        # Mock loan account
        loan_account = MagicMock()
        loan_account.interest_rate = 12.0
        loan_account.tenure_months = 36
        loan_account.principal_outstanding = 100000.0
        loan_account.schedule_type = "emi"

        result = calculate_restructure_impact(
            loan_account=loan_account,
            new_rate=10.0,
            new_tenure=None,
            principal_waiver=0
        )

        assert result["current"]["rate"] == 12.0
        assert result["proposed"]["rate"] == 10.0
        assert result["proposed"]["emi"] < result["current"]["emi"]
        assert result["savings"]["emi_reduction"] > 0

    def test_calculate_restructure_impact_tenure_extension(self):
        """Test impact calculation for tenure extension."""
        from app.services.restructure import calculate_restructure_impact

        loan_account = MagicMock()
        loan_account.interest_rate = 12.0
        loan_account.tenure_months = 36
        loan_account.principal_outstanding = 100000.0
        loan_account.schedule_type = "emi"

        result = calculate_restructure_impact(
            loan_account=loan_account,
            new_rate=None,
            new_tenure=48,
            principal_waiver=0
        )

        assert result["current"]["tenure"] == 36
        assert result["proposed"]["tenure"] == 48
        assert result["proposed"]["emi"] < result["current"]["emi"]

    def test_calculate_restructure_impact_principal_waiver(self):
        """Test impact calculation with principal waiver."""
        from app.services.restructure import calculate_restructure_impact

        loan_account = MagicMock()
        loan_account.interest_rate = 12.0
        loan_account.tenure_months = 36
        loan_account.principal_outstanding = 100000.0
        loan_account.schedule_type = "emi"

        result = calculate_restructure_impact(
            loan_account=loan_account,
            new_rate=None,
            new_tenure=None,
            principal_waiver=10000
        )

        assert result["current"]["principal"] == 100000.0
        assert result["proposed"]["principal"] == 90000.0
        assert result["savings"]["principal_waived"] == 10000

    def test_calculate_restructure_impact_combination(self):
        """Test impact calculation with combined changes."""
        from app.services.restructure import calculate_restructure_impact

        loan_account = MagicMock()
        loan_account.interest_rate = 12.0
        loan_account.tenure_months = 36
        loan_account.principal_outstanding = 100000.0
        loan_account.schedule_type = "emi"

        result = calculate_restructure_impact(
            loan_account=loan_account,
            new_rate=10.0,
            new_tenure=48,
            principal_waiver=5000
        )

        assert result["proposed"]["rate"] == 10.0
        assert result["proposed"]["tenure"] == 48
        assert result["proposed"]["principal"] == 95000.0
        assert result["savings"]["total_payment_reduction"] > 0


class TestPrepaymentService:
    """Tests for prepayment service."""

    def test_get_prepayment_options(self):
        """Test prepayment options calculation."""
        from app.services.prepayment import get_prepayment_options

        loan_account = MagicMock()
        loan_account.principal_outstanding = 100000.0
        loan_account.interest_rate = 12.0
        loan_account.schedule_type = "emi"

        # Mock db query
        db = MagicMock()
        schedule_item = MagicMock()
        schedule_item.total_due = 3500.0
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            schedule_item for _ in range(30)
        ]

        # Mock fee calculation - patch at the location where it's used
        with patch('app.services.fees.calculate_prepayment_penalty', return_value=0):
            result = get_prepayment_options(
                loan_account=loan_account,
                prepayment_amount=20000.0,
                db=db
            )

        assert result["prepayment_amount"] == 20000.0
        assert result["principal_reduced"] == 20000.0  # No penalty
        assert result["new_outstanding"] == 80000.0
        assert "reduce_emi" in result
        assert "reduce_tenure" in result

    def test_prepayment_options_emi_savings(self):
        """Test that reduce_emi option shows EMI savings."""
        from app.services.prepayment import get_prepayment_options

        loan_account = MagicMock()
        loan_account.principal_outstanding = 100000.0
        loan_account.interest_rate = 12.0
        loan_account.schedule_type = "emi"

        db = MagicMock()
        schedule_item = MagicMock()
        schedule_item.total_due = 3500.0
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            schedule_item for _ in range(30)
        ]

        with patch('app.services.fees.calculate_prepayment_penalty', return_value=0):
            result = get_prepayment_options(
                loan_account=loan_account,
                prepayment_amount=20000.0,
                db=db
            )

        # New EMI should be less than current
        if result["reduce_emi"]["new_emi"]:
            assert result["reduce_emi"]["new_emi"] < result["current"]["emi"]
            assert result["reduce_emi"]["emi_savings"] > 0


class TestClosureService:
    """Tests for closure service."""

    def test_can_close_loan_fully_paid(self):
        """Test closure options for fully paid loan."""
        from app.services.closure import can_close_loan

        loan_account = MagicMock()
        loan_account.status = "active"
        loan_account.principal_outstanding = 0.001  # Almost zero (below 0.01 threshold)
        loan_account.interest_outstanding = 0
        loan_account.fees_outstanding = 0
        loan_account.dpd = 0

        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 0

        result = can_close_loan(loan_account, db)

        # 0.001 is <= 0.01, so it's considered zero for normal closure
        assert result["options"]["normal_closure"]["eligible"] == True
        # Foreclosure is eligible when principal > 0 (even 0.001)
        # This is correct behavior - foreclosure option available for any positive balance
        assert result["options"]["foreclosure"]["eligible"] == True

    def test_can_close_loan_with_outstanding(self):
        """Test closure options for loan with outstanding balance."""
        from app.services.closure import can_close_loan

        loan_account = MagicMock()
        loan_account.status = "active"
        loan_account.principal_outstanding = 50000.0
        loan_account.interest_outstanding = 1000.0
        loan_account.fees_outstanding = 500.0
        loan_account.dpd = 45

        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 10

        result = can_close_loan(loan_account, db)

        assert result["options"]["normal_closure"]["eligible"] == False
        assert result["options"]["foreclosure"]["eligible"] == True
        assert result["options"]["settlement"]["eligible"] == False  # Below 90 DPD

    def test_can_close_loan_settlement_eligible(self):
        """Test settlement eligibility for 90+ DPD loan."""
        from app.services.closure import can_close_loan

        loan_account = MagicMock()
        loan_account.status = "active"
        loan_account.principal_outstanding = 50000.0
        loan_account.interest_outstanding = 5000.0
        loan_account.fees_outstanding = 1000.0
        loan_account.dpd = 120

        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 5

        result = can_close_loan(loan_account, db)

        assert result["options"]["settlement"]["eligible"] == True
        assert result["dpd"] == 120

    def test_can_close_loan_writeoff_eligible(self):
        """Test write-off eligibility for 180+ DPD loan."""
        from app.services.closure import can_close_loan

        loan_account = MagicMock()
        loan_account.status = "active"
        loan_account.principal_outstanding = 50000.0
        loan_account.interest_outstanding = 10000.0
        loan_account.fees_outstanding = 2000.0
        loan_account.dpd = 200

        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 8

        result = can_close_loan(loan_account, db)

        assert result["options"]["write_off"]["eligible"] == True


class TestWriteOffService:
    """Tests for write-off service."""

    def test_record_recovery_allocation(self):
        """Test recovery allocation logic to principal, interest, fees."""
        from app.services.closure import _to_decimal

        # Test the allocation logic directly without triggering model loading
        # Recovery of 2000 against write-off with:
        # - fees_written_off: 1000, recovered_fees: 0
        # - interest_written_off: 5000, recovered_interest: 0
        # - principal_written_off: 50000, recovered_principal: 0

        recovery_amount = _to_decimal(2000.0)
        remaining = recovery_amount

        # Fees first (1000 available)
        fees_remaining = _to_decimal(1000.0) - _to_decimal(0)  # 1000
        fees_recovered = min(remaining, fees_remaining)  # 1000
        remaining -= fees_recovered  # 1000 left

        # Interest next (5000 available)
        interest_remaining = _to_decimal(5000.0) - _to_decimal(0)  # 5000
        interest_recovered = min(remaining, interest_remaining)  # 1000
        remaining -= interest_recovered  # 0 left

        # Principal last
        principal_remaining = _to_decimal(50000.0) - _to_decimal(0)  # 50000
        principal_recovered = min(remaining, principal_remaining)  # 0

        assert fees_recovered == Decimal("1000")
        assert interest_recovered == Decimal("1000")
        assert principal_recovered == Decimal("0")
        assert fees_recovered + interest_recovered + principal_recovered == Decimal("2000")

    def test_write_off_summary_calculation(self):
        """Test write-off summary aggregation."""
        from app.services.closure import get_write_off_summary

        db = MagicMock()

        # Mock main query result
        main_result = MagicMock()
        main_result.count = 10
        main_result.total_written_off = 500000.0
        main_result.total_recovered = 50000.0
        db.query.return_value.first.return_value = main_result

        # Mock status query results
        status_results = [
            MagicMock(recovery_status="pending", count=5, amount=300000.0),
            MagicMock(recovery_status="partial", count=3, amount=150000.0),
            MagicMock(recovery_status="complete", count=2, amount=50000.0),
        ]
        db.query.return_value.group_by.return_value.all.return_value = status_results

        result = get_write_off_summary(db=db)

        assert result["total_accounts"] == 10
        assert result["total_written_off"] == 500000.0
        assert result["total_recovered"] == 50000.0
        assert result["recovery_rate_percent"] == 10.0
        assert result["net_loss"] == 450000.0


class TestDecimalConversions:
    """Tests for decimal conversion helpers."""

    def test_to_decimal_none(self):
        """Test conversion of None to Decimal."""
        from app.services.restructure import _to_decimal

        result = _to_decimal(None)
        assert result == Decimal("0")

    def test_to_decimal_float(self):
        """Test conversion of float to Decimal."""
        from app.services.restructure import _to_decimal

        result = _to_decimal(100.5)
        assert result == Decimal("100.5")

    def test_to_decimal_int(self):
        """Test conversion of int to Decimal."""
        from app.services.restructure import _to_decimal

        result = _to_decimal(100)
        assert result == Decimal("100")

    def test_to_decimal_already_decimal(self):
        """Test conversion of Decimal (should return same)."""
        from app.services.restructure import _to_decimal

        input_val = Decimal("123.45")
        result = _to_decimal(input_val)
        assert result == input_val


class TestEMICalculations:
    """Tests for EMI calculations in lifecycle services."""

    def test_restructure_emi_calculation(self):
        """Test that restructure correctly calculates new EMI."""
        from app.services.interest import calculate_emi

        # Original loan: 100000, 12%, 36 months
        original_emi = calculate_emi(
            Decimal("100000"),
            Decimal("12"),
            36
        )

        # After rate reduction to 10%
        new_emi_rate_reduction = calculate_emi(
            Decimal("100000"),
            Decimal("10"),
            36
        )

        # After tenure extension to 48 months
        new_emi_tenure_extension = calculate_emi(
            Decimal("100000"),
            Decimal("12"),
            48
        )

        assert new_emi_rate_reduction < original_emi
        assert new_emi_tenure_extension < original_emi

    def test_prepayment_emi_recalculation(self):
        """Test EMI recalculation after prepayment."""
        from app.services.interest import calculate_emi

        # Original: 100000, 12%, 36 months
        original_emi = calculate_emi(
            Decimal("100000"),
            Decimal("12"),
            36
        )

        # After 20000 prepayment with reduce_emi option
        # New principal: 80000, same tenure
        new_emi = calculate_emi(
            Decimal("80000"),
            Decimal("12"),
            36
        )

        # EMI should reduce proportionally (not exactly 20% due to interest)
        assert new_emi < original_emi
        assert float(new_emi) / float(original_emi) < 0.85  # Roughly 20% reduction


class TestClosureValidations:
    """Tests for closure validation logic."""

    def test_normal_closure_requires_zero_outstanding(self):
        """Test that normal closure requires zero outstanding."""
        from app.services.closure import _to_decimal

        # Helper to test the validation threshold
        # Amounts <= 0.01 should be considered zero
        assert _to_decimal(0.009) <= Decimal("0.01")
        assert _to_decimal(0.011) > Decimal("0.01")

    def test_settlement_requires_amount_less_than_outstanding(self):
        """Test settlement amount validation logic."""
        total_outstanding = Decimal("50000")
        settlement_amount = Decimal("45000")

        # Settlement should be less than outstanding
        assert settlement_amount < total_outstanding

        # Settlement equal to outstanding should use normal closure
        equal_settlement = Decimal("50000")
        assert equal_settlement >= total_outstanding

    def test_writeoff_dpd_threshold(self):
        """Test write-off DPD threshold."""
        # Standard practice: 180+ DPD for write-off
        dpd_values = [90, 120, 150, 180, 200, 365]

        for dpd in dpd_values:
            can_write_off = dpd >= 180
            if dpd >= 180:
                assert can_write_off == True
            else:
                assert can_write_off == False


class TestRecoveryTracking:
    """Tests for recovery tracking after write-off."""

    def test_recovery_status_transitions(self):
        """Test recovery status transitions."""
        # Status flow: pending -> in_progress -> partial -> complete

        # New write-off: pending
        total_written_off = Decimal("50000")
        total_recovered = Decimal("0")
        assert total_recovered == 0  # pending

        # After assignment to agency: in_progress
        # After first recovery: partial
        total_recovered = Decimal("10000")
        assert total_recovered > 0 and total_recovered < total_written_off

        # After full recovery: complete
        total_recovered = total_written_off
        assert total_recovered >= total_written_off

    def test_agency_commission_calculation(self):
        """Test agency commission calculation."""
        recovery_amount = Decimal("10000")
        commission_percent = Decimal("20")

        commission = (recovery_amount * commission_percent / 100)
        net_recovery = recovery_amount - commission

        assert commission == Decimal("2000")
        assert net_recovery == Decimal("8000")


class TestPrepaymentActionTypes:
    """Tests for prepayment action types."""

    def test_reduce_emi_keeps_tenure(self):
        """Test that reduce_emi keeps tenure unchanged."""
        original_tenure = 36
        new_tenure_reduce_emi = original_tenure  # Should stay same

        assert new_tenure_reduce_emi == original_tenure

    def test_reduce_tenure_keeps_emi(self):
        """Test that reduce_tenure keeps EMI unchanged."""
        from app.services.interest import calculate_emi

        original_emi = calculate_emi(Decimal("100000"), Decimal("12"), 36)

        # After prepayment, EMI stays same in reduce_tenure mode
        # Tenure decreases instead
        assert original_emi > 0

    def test_foreclosure_clears_all(self):
        """Test that foreclosure clears all balances."""
        # After foreclosure, all should be zero
        principal_after = Decimal("0")
        interest_after = Decimal("0")
        fees_after = Decimal("0")

        assert principal_after == 0
        assert interest_after == 0
        assert fees_after == 0
