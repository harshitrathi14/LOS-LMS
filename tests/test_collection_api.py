"""
Tests for collection service (collection case management, PTP, escalation).
"""

import json
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.collection import (
    open_collection_case,
    update_case_status,
    log_collection_action,
    record_promise_to_pay,
    update_promise_status,
    get_case_details,
    get_overdue_accounts,
    get_collection_dashboard,
    evaluate_escalation_rules,
    _generate_case_number,
)


class TestGenerateCaseNumber:
    def test_generates_sequential_number(self):
        db = MagicMock()
        db.query.return_value.scalar.return_value = 5

        result = _generate_case_number(db)

        assert result == "COL-000006"

    def test_first_case_number(self):
        db = MagicMock()
        db.query.return_value.scalar.return_value = 0

        result = _generate_case_number(db)

        assert result == "COL-000001"


class TestOpenCollectionCase:
    def test_open_case_success(self):
        db = MagicMock()
        account = SimpleNamespace(
            id=1,
            dpd=45,
            interest_outstanding=5000.0,
            fees_outstanding=500.0,
        )
        db.query.return_value.filter.return_value.first.return_value = account

        # Mock _generate_case_number via the count query
        db.query.return_value.scalar.return_value = 0

        result = open_collection_case(
            loan_account_id=1,
            assigned_to="collector1",
            assigned_queue="queue_a",
            priority="high",
            db=db,
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_open_case_account_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Loan account 999 not found"):
            open_collection_case(loan_account_id=999, db=db)


class TestUpdateCaseStatus:
    def test_valid_transition(self):
        db = MagicMock()
        case = SimpleNamespace(
            id=1,
            status="open",
            resolution_date=None,
            resolution_type=None,
        )
        db.query.return_value.filter.return_value.first.return_value = case

        update_case_status(1, "in_progress", db=db)

        assert case.status == "in_progress"
        db.commit.assert_called_once()

    def test_invalid_transition(self):
        db = MagicMock()
        case = SimpleNamespace(id=1, status="resolved")
        db.query.return_value.filter.return_value.first.return_value = case

        with pytest.raises(ValueError, match="Cannot transition"):
            update_case_status(1, "in_progress", db=db)

    def test_resolution_sets_date(self):
        db = MagicMock()
        case = SimpleNamespace(
            id=1,
            status="in_progress",
            resolution_date=None,
            resolution_type=None,
        )
        db.query.return_value.filter.return_value.first.return_value = case

        update_case_status(1, "resolved", resolution_type="paid", db=db)

        assert case.status == "resolved"
        assert case.resolution_date == date.today()
        assert case.resolution_type == "paid"

    def test_case_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Collection case 999 not found"):
            update_case_status(999, "closed", db=db)


class TestLogCollectionAction:
    def test_log_action_updates_case_dates(self):
        db = MagicMock()
        case = SimpleNamespace(
            id=1,
            status="open",
            last_action_date=None,
            next_action_date=None,
        )
        db.query.return_value.filter.return_value.first.return_value = case

        log_collection_action(
            case_id=1,
            action_type="call",
            performed_by="collector1",
            outcome="contacted",
            next_action_date=date(2024, 7, 15),
            db=db,
        )

        assert case.last_action_date == date.today()
        assert case.next_action_date == date(2024, 7, 15)
        # Auto-transitions open to in_progress
        assert case.status == "in_progress"
        db.commit.assert_called_once()

    def test_log_action_case_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Collection case 999 not found"):
            log_collection_action(
                case_id=999,
                action_type="call",
                performed_by="collector1",
                db=db,
            )


class TestPromiseToPay:
    def test_record_ptp(self):
        db = MagicMock()
        case = SimpleNamespace(id=1)
        db.query.return_value.filter.return_value.first.return_value = case

        result = record_promise_to_pay(
            case_id=1,
            promise_date=date(2024, 7, 1),
            payment_due_date=date(2024, 7, 15),
            promised_amount=10000.0,
            db=db,
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_record_ptp_case_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Collection case 999 not found"):
            record_promise_to_pay(
                case_id=999,
                promise_date=date(2024, 7, 1),
                payment_due_date=date(2024, 7, 15),
                promised_amount=10000.0,
                db=db,
            )

    def test_update_ptp_kept(self):
        db = MagicMock()
        ptp = SimpleNamespace(
            id=1,
            status="pending",
            actual_payment_date=None,
            actual_amount=None,
            notes=None,
        )
        db.query.return_value.filter.return_value.first.return_value = ptp

        update_promise_status(
            promise_id=1,
            actual_date=date(2024, 7, 14),
            actual_amount=10000.0,
            status="kept",
            db=db,
        )

        assert ptp.status == "kept"
        assert ptp.actual_payment_date == date(2024, 7, 14)
        assert ptp.actual_amount == 10000.0

    def test_update_ptp_broken(self):
        db = MagicMock()
        ptp = SimpleNamespace(
            id=1,
            status="pending",
            actual_payment_date=None,
            actual_amount=None,
            notes=None,
        )
        db.query.return_value.filter.return_value.first.return_value = ptp

        update_promise_status(
            promise_id=1,
            status="broken",
            notes="Customer did not pay",
            db=db,
        )

        assert ptp.status == "broken"
        assert ptp.notes == "Customer did not pay"

    def test_update_ptp_partial(self):
        db = MagicMock()
        ptp = SimpleNamespace(
            id=1,
            status="pending",
            actual_payment_date=None,
            actual_amount=None,
            notes=None,
        )
        db.query.return_value.filter.return_value.first.return_value = ptp

        update_promise_status(
            promise_id=1,
            actual_date=date(2024, 7, 15),
            actual_amount=5000.0,
            status="partial",
            db=db,
        )

        assert ptp.status == "partial"
        assert ptp.actual_amount == 5000.0

    def test_update_ptp_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Promise to pay 999 not found"):
            update_promise_status(promise_id=999, status="kept", db=db)


class TestEvaluateEscalationRules:
    def test_dpd_trigger_matches(self):
        db = MagicMock()
        account = SimpleNamespace(
            id=1,
            dpd=95,
            interest_outstanding=50000.0,
            fees_outstanding=5000.0,
            application=SimpleNamespace(product_id=1),
        )
        rule = SimpleNamespace(
            id=1,
            name="NPA Escalation",
            trigger_dpd=90,
            trigger_bucket=None,
            trigger_amount=None,
            action_type="assign_queue",
            action_config='{"queue": "legal"}',
            applies_to_product_id=None,
            is_active=True,
            priority=100,
        )

        from app.models.loan_account import LoanAccount
        from app.models.collection import EscalationRule

        def side_effect_query(model):
            mock = MagicMock()
            if model == LoanAccount:
                mock.filter.return_value.first.return_value = account
            elif model == EscalationRule:
                mock.filter.return_value.order_by.return_value.all.return_value = [rule]
            return mock

        db.query.side_effect = side_effect_query

        triggered = evaluate_escalation_rules(1, db)

        assert len(triggered) == 1
        assert triggered[0]["rule_name"] == "NPA Escalation"
        assert triggered[0]["action_config"] == {"queue": "legal"}

    def test_dpd_trigger_does_not_match(self):
        db = MagicMock()
        account = SimpleNamespace(
            id=1,
            dpd=30,
            interest_outstanding=5000.0,
            fees_outstanding=500.0,
            application=SimpleNamespace(product_id=1),
        )
        rule = SimpleNamespace(
            id=1,
            name="NPA Escalation",
            trigger_dpd=90,
            trigger_bucket=None,
            trigger_amount=None,
            action_type="assign_queue",
            action_config=None,
            applies_to_product_id=None,
            is_active=True,
            priority=100,
        )

        from app.models.loan_account import LoanAccount
        from app.models.collection import EscalationRule

        def side_effect_query(model):
            mock = MagicMock()
            if model == LoanAccount:
                mock.filter.return_value.first.return_value = account
            elif model == EscalationRule:
                mock.filter.return_value.order_by.return_value.all.return_value = [rule]
            return mock

        db.query.side_effect = side_effect_query

        triggered = evaluate_escalation_rules(1, db)

        assert len(triggered) == 0

    def test_bucket_trigger_matches(self):
        db = MagicMock()
        account = SimpleNamespace(
            id=1,
            dpd=45,  # SMA-1 bucket (31-60)
            interest_outstanding=10000.0,
            fees_outstanding=0.0,
            application=SimpleNamespace(product_id=1),
        )
        rule = SimpleNamespace(
            id=2,
            name="SMA-1 Alert",
            trigger_dpd=None,
            trigger_bucket="SMA-1",
            trigger_amount=None,
            action_type="send_sms",
            action_config=None,
            applies_to_product_id=None,
            is_active=True,
            priority=100,
        )

        from app.models.loan_account import LoanAccount
        from app.models.collection import EscalationRule

        def side_effect_query(model):
            mock = MagicMock()
            if model == LoanAccount:
                mock.filter.return_value.first.return_value = account
            elif model == EscalationRule:
                mock.filter.return_value.order_by.return_value.all.return_value = [rule]
            return mock

        db.query.side_effect = side_effect_query

        triggered = evaluate_escalation_rules(1, db)

        assert len(triggered) == 1
        assert triggered[0]["rule_name"] == "SMA-1 Alert"

    def test_amount_trigger(self):
        db = MagicMock()
        account = SimpleNamespace(
            id=1,
            dpd=100,
            interest_outstanding=100000.0,
            fees_outstanding=10000.0,
            application=SimpleNamespace(product_id=1),
        )
        rule = SimpleNamespace(
            id=3,
            name="High Amount Escalation",
            trigger_dpd=None,
            trigger_bucket=None,
            trigger_amount=50000.0,
            action_type="legal_notice",
            action_config=None,
            applies_to_product_id=None,
            is_active=True,
            priority=100,
        )

        from app.models.loan_account import LoanAccount
        from app.models.collection import EscalationRule

        def side_effect_query(model):
            mock = MagicMock()
            if model == LoanAccount:
                mock.filter.return_value.first.return_value = account
            elif model == EscalationRule:
                mock.filter.return_value.order_by.return_value.all.return_value = [rule]
            return mock

        db.query.side_effect = side_effect_query

        triggered = evaluate_escalation_rules(1, db)

        assert len(triggered) == 1
        assert triggered[0]["action_type"] == "legal_notice"

    def test_account_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Loan account 999 not found"):
            evaluate_escalation_rules(999, db)


class TestCollectionDashboard:
    def test_dashboard_empty(self):
        db = MagicMock()
        db.query.return_value.scalar.return_value = 0
        db.query.return_value.group_by.return_value.all.return_value = []

        result = get_collection_dashboard(db)

        assert result["total_cases"] == 0
        assert result["resolution_rate"] == 0
