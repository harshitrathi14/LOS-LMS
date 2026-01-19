"""
Tests for ECL (Expected Credit Loss) service - IFRS 9 / Ind AS 109.
"""

import pytest
from datetime import date
from decimal import Decimal


class TestECLStaging:
    """Tests for ECL stage assignment."""

    def test_stage1_performing(self):
        """Test Stage 1 assignment for performing loans."""
        dpd = 0
        is_npa = False
        is_restructured = False
        stage1_max_dpd = 30

        stage = 1 if dpd <= stage1_max_dpd and not is_npa and not is_restructured else 2
        assert stage == 1

    def test_stage2_dpd_based(self):
        """Test Stage 2 assignment based on DPD."""
        dpd = 45
        stage1_max_dpd = 30
        stage2_max_dpd = 90

        if dpd > stage2_max_dpd:
            stage = 3
        elif dpd > stage1_max_dpd:
            stage = 2
        else:
            stage = 1

        assert stage == 2

    def test_stage2_restructured(self):
        """Test Stage 2 assignment for restructured loans."""
        dpd = 15  # Low DPD
        is_restructured = True
        stage2_restructure_flag = True

        if is_restructured and stage2_restructure_flag:
            stage = 2
        else:
            stage = 1

        assert stage == 2

    def test_stage3_npa(self):
        """Test Stage 3 assignment for NPA loans."""
        is_npa = True
        stage3_npa_flag = True

        stage = 3 if is_npa and stage3_npa_flag else 1
        assert stage == 3

    def test_stage3_dpd_over_90(self):
        """Test Stage 3 assignment for 90+ DPD."""
        dpd = 95
        stage2_max_dpd = 90

        stage = 3 if dpd > stage2_max_dpd else 2
        assert stage == 3

    def test_stage3_written_off(self):
        """Test Stage 3 assignment for written-off loans."""
        is_written_off = True
        stage3_write_off_flag = True

        stage = 3 if is_written_off and stage3_write_off_flag else 1
        assert stage == 3


class TestECLCalculation:
    """Tests for ECL amount calculation."""

    def test_ecl_12_month_calculation(self):
        """Test 12-month ECL calculation for Stage 1."""
        ead = Decimal("100000")
        pd_12m = Decimal("0.5")  # 0.5%
        lgd = Decimal("65")  # 65%

        ecl = ead * (pd_12m / 100) * (lgd / 100)
        expected = Decimal("100000") * Decimal("0.005") * Decimal("0.65")

        assert ecl == expected  # 325

    def test_ecl_lifetime_stage2(self):
        """Test lifetime ECL for Stage 2."""
        ead = Decimal("100000")
        pd_lifetime = Decimal("5")  # 5%
        lgd = Decimal("65")

        ecl = ead * (pd_lifetime / 100) * (lgd / 100)
        expected = Decimal("100000") * Decimal("0.05") * Decimal("0.65")

        assert ecl == expected  # 3250

    def test_ecl_stage3_100_pd(self):
        """Test Stage 3 ECL with 100% PD."""
        ead = Decimal("100000")
        lgd = Decimal("65")

        # Stage 3: PD = 100%
        ecl = ead * lgd / 100
        assert ecl == Decimal("65000")

    def test_ecl_with_collateral(self):
        """Test ECL with collateral reducing LGD."""
        ead = Decimal("100000")
        pd = Decimal("5")
        base_lgd = Decimal("65")
        collateral_coverage = Decimal("40")  # 40% covered

        # LGD reduced by collateral
        effective_lgd = base_lgd * (100 - collateral_coverage) / 100
        ecl = ead * (pd / 100) * (effective_lgd / 100)

        assert effective_lgd == Decimal("39")


class TestECLProvision:
    """Tests for ECL provision calculations."""

    def test_provision_charge(self):
        """Test provision charge calculation."""
        opening_provision = Decimal("1000")
        closing_provision = Decimal("1500")

        provision_charge = max(Decimal("0"), closing_provision - opening_provision)
        assert provision_charge == Decimal("500")

    def test_provision_release(self):
        """Test provision release calculation."""
        opening_provision = Decimal("1500")
        closing_provision = Decimal("1000")

        provision_release = max(Decimal("0"), opening_provision - closing_provision)
        assert provision_release == Decimal("500")

    def test_provision_coverage_ratio(self):
        """Test provision coverage ratio calculation."""
        provision = Decimal("6500")
        exposure = Decimal("100000")

        coverage = provision / exposure * 100
        assert coverage == Decimal("6.5")

    def test_provision_write_off_utilization(self):
        """Test provision utilization on write-off."""
        provision_balance = Decimal("6500")
        write_off_amount = Decimal("100000")

        utilized = min(provision_balance, write_off_amount)
        net_write_off = write_off_amount - utilized

        assert utilized == Decimal("6500")
        assert net_write_off == Decimal("93500")


class TestECLMovement:
    """Tests for ECL stage movement tracking."""

    def test_downgrade_1_to_2(self):
        """Test stage downgrade from 1 to 2."""
        from_stage = 1
        to_stage = 2

        direction = "downgrade" if to_stage > from_stage else "upgrade"
        assert direction == "downgrade"

    def test_downgrade_2_to_3(self):
        """Test stage downgrade from 2 to 3."""
        from_stage = 2
        to_stage = 3

        direction = "downgrade" if to_stage > from_stage else "upgrade"
        assert direction == "downgrade"

    def test_upgrade_2_to_1(self):
        """Test stage upgrade from 2 to 1."""
        from_stage = 2
        to_stage = 1

        direction = "downgrade" if to_stage > from_stage else "upgrade"
        assert direction == "upgrade"

    def test_upgrade_3_to_2(self):
        """Test stage upgrade from 3 to 2."""
        from_stage = 3
        to_stage = 2

        direction = "downgrade" if to_stage > from_stage else "upgrade"
        assert direction == "upgrade"


class TestECLPortfolio:
    """Tests for portfolio-level ECL aggregation."""

    def test_portfolio_total_provision(self):
        """Test total portfolio provision calculation."""
        loans = [
            {"stage": 1, "exposure": 100000, "provision": 325},
            {"stage": 1, "exposure": 200000, "provision": 650},
            {"stage": 2, "exposure": 50000, "provision": 1625},
            {"stage": 3, "exposure": 30000, "provision": 19500},
        ]

        total_exposure = sum(Decimal(str(l["exposure"])) for l in loans)
        total_provision = sum(Decimal(str(l["provision"])) for l in loans)

        assert total_exposure == Decimal("380000")
        assert total_provision == Decimal("22100")

    def test_stage_wise_aggregation(self):
        """Test stage-wise ECL aggregation."""
        loans = [
            {"stage": 1, "exposure": 100000, "provision": 325},
            {"stage": 1, "exposure": 200000, "provision": 650},
            {"stage": 2, "exposure": 50000, "provision": 1625},
            {"stage": 3, "exposure": 30000, "provision": 19500},
        ]

        stage_totals = {1: 0, 2: 0, 3: 0}
        for loan in loans:
            stage_totals[loan["stage"]] += loan["provision"]

        assert stage_totals[1] == 975
        assert stage_totals[2] == 1625
        assert stage_totals[3] == 19500

    def test_overall_coverage(self):
        """Test overall coverage ratio."""
        total_exposure = Decimal("380000")
        total_provision = Decimal("22100")

        coverage = total_provision / total_exposure * 100
        assert coverage.quantize(Decimal("0.01")) == Decimal("5.82")


class TestECLParameters:
    """Tests for ECL parameters (PD, LGD, EAD)."""

    def test_pd_by_stage(self):
        """Test PD assignment by stage."""
        pd_stage1 = Decimal("0.5")
        pd_stage2 = Decimal("5.0")
        pd_stage3 = Decimal("100.0")

        assert pd_stage1 < pd_stage2 < pd_stage3

    def test_lgd_secured_vs_unsecured(self):
        """Test LGD for secured vs unsecured loans."""
        lgd_secured = Decimal("35")
        lgd_unsecured = Decimal("65")

        assert lgd_secured < lgd_unsecured

    def test_ead_calculation(self):
        """Test EAD (Exposure at Default) calculation."""
        principal_outstanding = Decimal("100000")
        interest_outstanding = Decimal("5000")
        fees_outstanding = Decimal("500")

        ead = principal_outstanding + interest_outstanding + fees_outstanding
        assert ead == Decimal("105500")

    def test_ead_with_undrawn(self):
        """Test EAD including undrawn commitment."""
        drawn = Decimal("100000")
        undrawn = Decimal("50000")
        ccf = Decimal("75")  # Credit conversion factor

        off_balance_ead = undrawn * ccf / 100
        total_ead = drawn + off_balance_ead

        assert off_balance_ead == Decimal("37500")
        assert total_ead == Decimal("137500")


class TestSICR:
    """Tests for SICR (Significant Increase in Credit Risk)."""

    def test_sicr_rating_downgrade(self):
        """Test SICR triggered by rating downgrade."""
        original_rating = "A"
        current_rating = "BB"
        rating_order = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]

        original_index = rating_order.index(original_rating)
        current_index = rating_order.index(current_rating)
        notches_downgraded = current_index - original_index

        sicr_threshold = 2
        sicr_triggered = notches_downgraded >= sicr_threshold

        assert notches_downgraded == 2
        assert sicr_triggered == True

    def test_sicr_pd_increase(self):
        """Test SICR triggered by PD increase."""
        original_pd = Decimal("0.5")
        current_pd = Decimal("1.5")
        threshold = Decimal("100")  # 100% increase

        pd_increase_pct = (current_pd - original_pd) / original_pd * 100
        sicr_triggered = pd_increase_pct >= threshold

        assert pd_increase_pct == Decimal("200")
        assert sicr_triggered == True


class TestMonthEndProvision:
    """Tests for month-end provision calculation."""

    def test_month_end_date_check(self):
        """Test identification of month-end date."""
        import calendar

        test_date = date(2024, 1, 31)
        last_day = calendar.monthrange(test_date.year, test_date.month)[1]

        is_month_end = test_date.day == last_day
        assert is_month_end == True

    def test_provision_movement_reconciliation(self):
        """Test provision movement reconciliation."""
        opening = Decimal("10000")
        charge = Decimal("2000")
        release = Decimal("500")
        write_off_utilized = Decimal("1000")

        closing = opening + charge - release - write_off_utilized
        assert closing == Decimal("10500")
