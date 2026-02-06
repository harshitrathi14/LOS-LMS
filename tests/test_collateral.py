"""
Tests for collateral service (LAP collateral management).
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest

from app.services.collateral import (
    calculate_ltv,
    create_collateral,
    update_collateral,
    add_valuation,
    add_insurance,
    add_legal_verification,
    link_collateral_to_account,
    get_collateral_summary,
    _to_decimal,
)


class TestToDecimal:
    def test_none_returns_zero(self):
        assert _to_decimal(None) == Decimal("0")

    def test_float_conversion(self):
        assert _to_decimal(100000.50) == Decimal("100000.5")

    def test_int_conversion(self):
        assert _to_decimal(500000) == Decimal("500000")


class TestCreateCollateral:
    def test_create_collateral(self):
        db = MagicMock()
        data = {
            "application_id": 1,
            "property_type": "residential",
            "address_line1": "123 Main St",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "owner_name": "John Doe",
        }

        result = create_collateral(data, db)

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()


class TestUpdateCollateral:
    def test_update_collateral_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Collateral 999 not found"):
            update_collateral(999, {"status": "verified"}, db)

    def test_update_collateral_sets_fields(self):
        db = MagicMock()
        collateral = SimpleNamespace(id=1, status="pending", city="Mumbai")
        db.query.return_value.filter.return_value.first.return_value = collateral

        result = update_collateral(1, {"status": "verified", "city": "Pune"}, db)

        assert collateral.status == "verified"
        assert collateral.city == "Pune"
        db.commit.assert_called_once()


class TestAddValuation:
    def test_add_valuation_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Collateral 999 not found"):
            add_valuation(999, {}, db)

    def test_add_valuation_updates_parent_snapshot(self):
        db = MagicMock()
        collateral = SimpleNamespace(
            id=1,
            loan_account_id=None,
            market_value=None,
            realizable_value=None,
            distress_value=None,
            valuation_date=None,
            valuer_name=None,
            ltv_ratio=None,
        )
        db.query.return_value.filter.return_value.first.return_value = collateral

        data = {
            "valuation_date": date(2024, 6, 1),
            "valuer_name": "ABC Valuers",
            "valuation_type": "initial",
            "market_value": 5000000.0,
            "realizable_value": 4000000.0,
            "distress_value": 3000000.0,
            "ltv_at_valuation": 0.60,
        }

        add_valuation(1, data, db)

        assert collateral.market_value == 5000000.0
        assert collateral.realizable_value == 4000000.0
        assert collateral.distress_value == 3000000.0
        assert collateral.valuation_date == date(2024, 6, 1)
        assert collateral.valuer_name == "ABC Valuers"
        db.commit.assert_called_once()

    def test_add_valuation_recalculates_ltv_with_account(self):
        db = MagicMock()
        collateral = SimpleNamespace(
            id=1,
            loan_account_id=10,
            market_value=None,
            realizable_value=None,
            distress_value=None,
            valuation_date=None,
            valuer_name=None,
            ltv_ratio=None,
        )
        account = SimpleNamespace(principal_outstanding=3000000.0)

        def side_effect_query(model):
            mock = MagicMock()
            from app.models.collateral import Collateral
            from app.models.loan_account import LoanAccount
            if model == Collateral:
                mock.filter.return_value.first.return_value = collateral
            elif model == LoanAccount:
                mock.filter.return_value.first.return_value = account
            return mock

        db.query.side_effect = side_effect_query

        data = {
            "valuation_date": date(2024, 6, 1),
            "valuer_name": "XYZ Valuers",
            "valuation_type": "initial",
            "market_value": 5000000.0,
            "realizable_value": None,
            "distress_value": None,
            "ltv_at_valuation": None,
        }

        add_valuation(1, data, db)

        # LTV = 3000000 / 5000000 = 0.6
        assert collateral.ltv_ratio == 0.6


class TestAddInsurance:
    def test_add_insurance_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Collateral 999 not found"):
            add_insurance(999, {}, db)

    def test_add_insurance_updates_parent_snapshot(self):
        db = MagicMock()
        collateral = SimpleNamespace(
            id=1,
            insurance_policy_number=None,
            insurance_expiry_date=None,
            insured_value=None,
        )
        db.query.return_value.filter.return_value.first.return_value = collateral

        data = {
            "policy_number": "POL-001",
            "provider": "HDFC ERGO",
            "insured_value": 5000000.0,
            "premium_amount": 25000.0,
            "start_date": date(2024, 1, 1),
            "expiry_date": date(2025, 1, 1),
        }

        add_insurance(1, data, db)

        assert collateral.insurance_policy_number == "POL-001"
        assert collateral.insurance_expiry_date == date(2025, 1, 1)
        assert collateral.insured_value == 5000000.0
        db.commit.assert_called_once()


class TestAddLegalVerification:
    def test_all_clear_sets_legal_status_clear(self):
        db = MagicMock()
        collateral = SimpleNamespace(id=1, legal_status="pending")

        # Mock: first query for collateral, second for all verifications
        from app.models.collateral import Collateral, CollateralLegalVerification

        v1 = SimpleNamespace(verification_status="clear")
        v2 = SimpleNamespace(verification_status="clear")

        def side_effect_query(model):
            mock = MagicMock()
            if model == Collateral:
                mock.filter.return_value.first.return_value = collateral
            elif model == CollateralLegalVerification:
                mock.filter.return_value.all.return_value = [v1, v2]
            return mock

        db.query.side_effect = side_effect_query

        data = {
            "verification_type": "title_search",
            "verification_date": date(2024, 6, 1),
            "verified_by": "Legal Team",
            "verification_status": "clear",
        }

        add_legal_verification(1, data, db)

        assert collateral.legal_status == "clear"

    def test_issue_found_sets_legal_status_issue(self):
        db = MagicMock()
        collateral = SimpleNamespace(id=1, legal_status="pending")

        from app.models.collateral import Collateral, CollateralLegalVerification

        v1 = SimpleNamespace(verification_status="clear")
        v2 = SimpleNamespace(verification_status="issue_found")

        def side_effect_query(model):
            mock = MagicMock()
            if model == Collateral:
                mock.filter.return_value.first.return_value = collateral
            elif model == CollateralLegalVerification:
                mock.filter.return_value.all.return_value = [v1, v2]
            return mock

        db.query.side_effect = side_effect_query

        data = {
            "verification_type": "encumbrance_check",
            "verification_date": date(2024, 6, 1),
            "verified_by": "Legal Team",
            "verification_status": "issue_found",
        }

        add_legal_verification(1, data, db)

        assert collateral.legal_status == "issue_found"

    def test_mixed_pending_stays_pending(self):
        db = MagicMock()
        collateral = SimpleNamespace(id=1, legal_status=None)

        from app.models.collateral import Collateral, CollateralLegalVerification

        v1 = SimpleNamespace(verification_status="clear")
        v2 = SimpleNamespace(verification_status="pending")

        def side_effect_query(model):
            mock = MagicMock()
            if model == Collateral:
                mock.filter.return_value.first.return_value = collateral
            elif model == CollateralLegalVerification:
                mock.filter.return_value.all.return_value = [v1, v2]
            return mock

        db.query.side_effect = side_effect_query

        data = {
            "verification_type": "cersai_search",
            "verification_date": date(2024, 6, 1),
            "verified_by": "Legal Team",
            "verification_status": "pending",
        }

        add_legal_verification(1, data, db)

        assert collateral.legal_status == "pending"


class TestCalculateLTV:
    def test_ltv_no_market_value(self):
        db = MagicMock()
        collateral = SimpleNamespace(
            id=1,
            market_value=None,
            loan_account_id=None,
            application_id=1,
        )
        db.query.return_value.filter.return_value.first.return_value = collateral

        result = calculate_ltv(1, db)

        assert result["ltv_ratio"] is None
        assert "No market value" in result["message"]

    def test_ltv_with_loan_account(self):
        db = MagicMock()
        collateral = SimpleNamespace(
            id=1,
            market_value=5000000.0,
            loan_account_id=10,
            application_id=1,
        )
        account = SimpleNamespace(principal_outstanding=3000000.0)

        from app.models.collateral import Collateral
        from app.models.loan_account import LoanAccount

        def side_effect_query(model):
            mock = MagicMock()
            if model == Collateral:
                mock.filter.return_value.first.return_value = collateral
            elif model == LoanAccount:
                mock.filter.return_value.first.return_value = account
            return mock

        db.query.side_effect = side_effect_query

        result = calculate_ltv(1, db)

        # LTV = (3000000 / 5000000) * 100 = 60.00%
        assert result["ltv_ratio"] == 60.0
        assert result["outstanding"] == 3000000.0
        assert result["market_value"] == 5000000.0

    def test_ltv_with_application_amount(self):
        db = MagicMock()
        collateral = SimpleNamespace(
            id=1,
            market_value=5000000.0,
            loan_account_id=None,
            application_id=1,
        )
        application = SimpleNamespace(
            approved_amount=None,
            requested_amount=4000000.0,
        )

        from app.models.collateral import Collateral
        from app.models.loan_application import LoanApplication

        def side_effect_query(model):
            mock = MagicMock()
            if model == Collateral:
                mock.filter.return_value.first.return_value = collateral
            elif model == LoanApplication:
                mock.filter.return_value.first.return_value = application
            return mock

        db.query.side_effect = side_effect_query

        result = calculate_ltv(1, db)

        # LTV = (4000000 / 5000000) * 100 = 80.00%
        assert result["ltv_ratio"] == 80.0

    def test_ltv_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Collateral 999 not found"):
            calculate_ltv(999, db)


class TestLinkCollateralToAccount:
    def test_link_success(self):
        db = MagicMock()
        collateral = SimpleNamespace(id=1, loan_account_id=None)
        account = SimpleNamespace(id=10)

        from app.models.collateral import Collateral
        from app.models.loan_account import LoanAccount

        def side_effect_query(model):
            mock = MagicMock()
            if model == Collateral:
                mock.filter.return_value.first.return_value = collateral
            elif model == LoanAccount:
                mock.filter.return_value.first.return_value = account
            return mock

        db.query.side_effect = side_effect_query

        link_collateral_to_account(1, 10, db)

        assert collateral.loan_account_id == 10
        db.commit.assert_called_once()

    def test_link_collateral_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Collateral 999 not found"):
            link_collateral_to_account(999, 10, db)
