"""
Tests for LAP (Loan Against Property) 5-level approval workflow service.
"""

import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.services.lap_workflow import (
    LAP_STAGES,
    LAP_TRANSITIONS,
    LAP_FINAL_STAGES,
    LAP_WORKFLOW_CODE,
    STAGE_STATUS_MAP,
    seed_lap_workflow_definition,
    start_lap_workflow,
    transition_lap_workflow,
    assign_lap_workflow,
    get_lap_workflow_status,
)


class TestLapWorkflowConstants:
    def test_all_stages_have_transitions(self):
        """Every stage should appear as a key in LAP_TRANSITIONS."""
        for stage in LAP_STAGES:
            assert stage in LAP_TRANSITIONS, f"Stage '{stage}' missing from transitions"

    def test_all_transition_targets_are_valid_stages(self):
        """Every transition target should be a valid stage."""
        for source, targets in LAP_TRANSITIONS.items():
            for target in targets:
                assert target in LAP_STAGES, (
                    f"Transition target '{target}' from '{source}' is not a valid stage"
                )

    def test_final_stages_have_no_transitions(self):
        """Final stages should have empty transition lists."""
        for stage in LAP_FINAL_STAGES:
            assert LAP_TRANSITIONS[stage] == [], (
                f"Final stage '{stage}' should have no transitions"
            )

    def test_happy_path_reachable(self):
        """Verify the full happy path from draft to disbursement is reachable."""
        happy_path = [
            "draft",
            "branch_data_entry",
            "branch_manager_review",
            "regional_credit_review",
            "central_credit_review",
            "sanctioning_authority",
            "approved",
            "disbursement",
        ]
        for i in range(len(happy_path) - 1):
            from_stage = happy_path[i]
            to_stage = happy_path[i + 1]
            assert to_stage in LAP_TRANSITIONS[from_stage], (
                f"Cannot transition from '{from_stage}' to '{to_stage}'"
            )

    def test_refer_back_loop(self):
        """Verify referred_back → branch_data_entry loop."""
        assert "referred_back" in LAP_TRANSITIONS["branch_manager_review"]
        assert "referred_back" in LAP_TRANSITIONS["regional_credit_review"]
        assert "referred_back" in LAP_TRANSITIONS["central_credit_review"]
        assert "referred_back" in LAP_TRANSITIONS["sanctioning_authority"]
        assert "branch_data_entry" in LAP_TRANSITIONS["referred_back"]

    def test_rejection_from_review_stages(self):
        """Each review stage can reject."""
        review_stages = [
            "branch_manager_review",
            "regional_credit_review",
            "central_credit_review",
            "sanctioning_authority",
        ]
        for stage in review_stages:
            assert "rejected" in LAP_TRANSITIONS[stage], (
                f"Stage '{stage}' should allow rejection"
            )

    def test_stage_status_map_covers_all_stages(self):
        """Every stage should have a mapped LoanApplication status."""
        for stage in LAP_STAGES:
            assert stage in STAGE_STATUS_MAP, (
                f"Stage '{stage}' missing from STAGE_STATUS_MAP"
            )


class TestSeedLapWorkflowDefinition:
    def test_returns_existing_if_present(self):
        db = MagicMock()
        existing = SimpleNamespace(id=1, code=LAP_WORKFLOW_CODE)
        db.query.return_value.filter.return_value.first.return_value = existing

        result = seed_lap_workflow_definition(db)

        assert result.id == 1
        # Should NOT call create_workflow_definition since it already exists

    @patch("app.services.lap_workflow.workflow.create_workflow_definition")
    def test_creates_new_if_not_present(self, mock_create):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        new_def = SimpleNamespace(id=1, code=LAP_WORKFLOW_CODE)
        mock_create.return_value = new_def

        result = seed_lap_workflow_definition(db)

        mock_create.assert_called_once()
        assert result.id == 1


class TestStartLapWorkflow:
    @patch("app.services.lap_workflow.workflow.start_workflow")
    @patch("app.services.lap_workflow.seed_lap_workflow_definition")
    def test_start_workflow_success(self, mock_seed, mock_start):
        db = MagicMock()
        application = SimpleNamespace(id=1, status="submitted")
        db.query.return_value.filter.return_value.first.return_value = application

        instance = SimpleNamespace(
            id=100, current_stage="draft", is_active=True
        )
        mock_start.return_value = instance

        result = start_lap_workflow(
            application_id=1, started_by="user1", db=db
        )

        assert result.id == 100
        assert application.status == "draft"
        mock_seed.assert_called_once_with(db)
        mock_start.assert_called_once()

    def test_start_workflow_application_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Loan application 999 not found"):
            start_lap_workflow(application_id=999, started_by="user1", db=db)


class TestTransitionLapWorkflow:
    @patch("app.services.lap_workflow.workflow.transition_workflow")
    def test_transition_updates_application_status(self, mock_transition):
        db = MagicMock()
        application = SimpleNamespace(
            id=1, status="draft", decision_at=None
        )
        instance = SimpleNamespace(
            id=100,
            entity_type="loan_application",
            entity_id=1,
            is_active=True,
        )

        from app.models.loan_application import LoanApplication
        from app.models.workflow import WorkflowInstance

        call_count = [0]

        def side_effect_query(model):
            mock = MagicMock()
            if model == LoanApplication:
                mock.filter.return_value.first.return_value = application
            elif model == WorkflowInstance:
                mock.filter.return_value.first.return_value = instance
            return mock

        db.query.side_effect = side_effect_query

        transitioned = SimpleNamespace(
            id=100,
            current_stage="branch_data_entry",
            previous_stage="draft",
            is_active=True,
        )
        mock_transition.return_value = transitioned

        result = transition_lap_workflow(
            application_id=1,
            to_stage="branch_data_entry",
            transitioned_by="user1",
            action="submit",
            db=db,
        )

        assert application.status == "data_entry"

    @patch("app.services.lap_workflow.workflow.transition_workflow")
    def test_transition_to_approved_sets_decision_at(self, mock_transition):
        db = MagicMock()
        application = SimpleNamespace(
            id=1, status="under_review", decision_at=None
        )
        instance = SimpleNamespace(
            id=100,
            entity_type="loan_application",
            entity_id=1,
            is_active=True,
        )

        from app.models.loan_application import LoanApplication
        from app.models.workflow import WorkflowInstance

        def side_effect_query(model):
            mock = MagicMock()
            if model == LoanApplication:
                mock.filter.return_value.first.return_value = application
            elif model == WorkflowInstance:
                mock.filter.return_value.first.return_value = instance
            return mock

        db.query.side_effect = side_effect_query

        transitioned = SimpleNamespace(
            id=100,
            current_stage="approved",
            previous_stage="sanctioning_authority",
            is_active=False,
        )
        mock_transition.return_value = transitioned

        result = transition_lap_workflow(
            application_id=1,
            to_stage="approved",
            transitioned_by="authority",
            action="approve",
            db=db,
        )

        assert application.status == "approved"
        assert application.decision_at is not None

    @patch("app.services.lap_workflow.workflow.transition_workflow")
    def test_transition_to_rejected_sets_decision_at(self, mock_transition):
        db = MagicMock()
        application = SimpleNamespace(
            id=1, status="under_review", decision_at=None
        )
        instance = SimpleNamespace(
            id=100, entity_type="loan_application", entity_id=1, is_active=True,
        )

        from app.models.loan_application import LoanApplication
        from app.models.workflow import WorkflowInstance

        def side_effect_query(model):
            mock = MagicMock()
            if model == LoanApplication:
                mock.filter.return_value.first.return_value = application
            elif model == WorkflowInstance:
                mock.filter.return_value.first.return_value = instance
            return mock

        db.query.side_effect = side_effect_query

        transitioned = SimpleNamespace(
            id=100, current_stage="rejected", previous_stage="branch_manager_review",
            is_active=False,
        )
        mock_transition.return_value = transitioned

        transition_lap_workflow(
            application_id=1, to_stage="rejected",
            transitioned_by="manager", action="reject", db=db,
        )

        assert application.status == "rejected"
        assert application.decision_at is not None

    def test_transition_no_active_workflow(self):
        db = MagicMock()
        application = SimpleNamespace(id=1, status="submitted", decision_at=None)

        from app.models.loan_application import LoanApplication
        from app.models.workflow import WorkflowInstance

        def side_effect_query(model):
            mock = MagicMock()
            if model == LoanApplication:
                mock.filter.return_value.first.return_value = application
            elif model == WorkflowInstance:
                mock.filter.return_value.first.return_value = None
            return mock

        db.query.side_effect = side_effect_query

        with pytest.raises(ValueError, match="No active workflow found"):
            transition_lap_workflow(
                application_id=1,
                to_stage="branch_data_entry",
                transitioned_by="user1",
                action="submit",
                db=db,
            )

    @patch("app.services.lap_workflow.workflow.transition_workflow")
    def test_invalid_transition_raises_error(self, mock_transition):
        """workflow.transition_workflow raises ValueError for invalid transitions."""
        db = MagicMock()
        application = SimpleNamespace(id=1, status="draft", decision_at=None)
        instance = SimpleNamespace(
            id=100, entity_type="loan_application", entity_id=1, is_active=True,
        )

        from app.models.loan_application import LoanApplication
        from app.models.workflow import WorkflowInstance

        def side_effect_query(model):
            mock = MagicMock()
            if model == LoanApplication:
                mock.filter.return_value.first.return_value = application
            elif model == WorkflowInstance:
                mock.filter.return_value.first.return_value = instance
            return mock

        db.query.side_effect = side_effect_query

        mock_transition.side_effect = ValueError(
            "Transition from 'draft' to 'approved' is not allowed"
        )

        with pytest.raises(ValueError, match="not allowed"):
            transition_lap_workflow(
                application_id=1,
                to_stage="approved",
                transitioned_by="user1",
                action="approve",
                db=db,
            )


class TestAssignLapWorkflow:
    @patch("app.services.lap_workflow.workflow.assign_workflow")
    def test_assign_success(self, mock_assign):
        db = MagicMock()
        instance = SimpleNamespace(
            id=100, entity_type="loan_application", entity_id=1, is_active=True,
        )
        db.query.return_value.filter.return_value.first.return_value = instance

        assigned = SimpleNamespace(
            id=100, assigned_to="manager1", assigned_role="branch_manager",
        )
        mock_assign.return_value = assigned

        result = assign_lap_workflow(
            application_id=1,
            assigned_to="manager1",
            assigned_role="branch_manager",
            db=db,
        )

        assert result.assigned_to == "manager1"

    def test_assign_no_active_workflow(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="No active workflow found"):
            assign_lap_workflow(
                application_id=1, assigned_to="user1", db=db
            )


class TestGetLapWorkflowStatus:
    @patch("app.services.lap_workflow.workflow.get_workflow_status")
    def test_returns_status(self, mock_get):
        db = MagicMock()
        mock_get.return_value = {
            "instance_id": 100,
            "current_stage": "branch_manager_review",
            "is_active": True,
        }

        result = get_lap_workflow_status(1, db)

        assert result["current_stage"] == "branch_manager_review"
        mock_get.assert_called_once_with(
            entity_type="loan_application", entity_id=1, db=db
        )

    @patch("app.services.lap_workflow.workflow.get_workflow_status")
    def test_returns_none_when_no_workflow(self, mock_get):
        db = MagicMock()
        mock_get.return_value = None

        result = get_lap_workflow_status(1, db)

        assert result is None
