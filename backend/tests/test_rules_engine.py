"""
Tests for rules engine service.
"""

import pytest
from unittest.mock import MagicMock


class TestConditionEvaluation:
    """Tests for condition evaluation logic."""

    def test_simple_equality(self):
        """Test simple equality condition."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "status", "operator": "==", "value": "active"}
        data = {"status": "active"}

        assert _evaluate_condition(condition, data) == True

        data = {"status": "inactive"}
        assert _evaluate_condition(condition, data) == False

    def test_numeric_comparison(self):
        """Test numeric comparison operators."""
        from app.services.rules_engine import _evaluate_condition

        data = {"credit_score": 720}

        # Greater than or equal
        condition = {"field": "credit_score", "operator": ">=", "value": 700}
        assert _evaluate_condition(condition, data) == True

        condition = {"field": "credit_score", "operator": ">=", "value": 750}
        assert _evaluate_condition(condition, data) == False

        # Less than
        condition = {"field": "credit_score", "operator": "<", "value": 750}
        assert _evaluate_condition(condition, data) == True

    def test_between_operator(self):
        """Test between operator."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "age", "operator": "between", "value": [21, 65]}

        data = {"age": 30}
        assert _evaluate_condition(condition, data) == True

        data = {"age": 18}
        assert _evaluate_condition(condition, data) == False

        data = {"age": 70}
        assert _evaluate_condition(condition, data) == False

    def test_in_operator(self):
        """Test in operator."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "employment_type", "operator": "in", "value": ["salaried", "self_employed"]}

        data = {"employment_type": "salaried"}
        assert _evaluate_condition(condition, data) == True

        data = {"employment_type": "unemployed"}
        assert _evaluate_condition(condition, data) == False

    def test_not_in_operator(self):
        """Test not_in operator."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "industry", "operator": "not_in", "value": ["gambling", "tobacco"]}

        data = {"industry": "technology"}
        assert _evaluate_condition(condition, data) == True

        data = {"industry": "gambling"}
        assert _evaluate_condition(condition, data) == False

    def test_is_null_operator(self):
        """Test is_null operator."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "guarantor", "operator": "is_null", "value": None}

        data = {"guarantor": None}
        assert _evaluate_condition(condition, data) == True

        data = {"guarantor": "John Doe"}
        assert _evaluate_condition(condition, data) == False

    def test_nested_field_access(self):
        """Test nested field access with dot notation."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "borrower.income", "operator": ">=", "value": 50000}

        data = {"borrower": {"income": 75000}}
        assert _evaluate_condition(condition, data) == True

        data = {"borrower": {"income": 30000}}
        assert _evaluate_condition(condition, data) == False

    def test_and_condition(self):
        """Test AND logical operator."""
        from app.services.rules_engine import _evaluate_condition

        condition = {
            "and": [
                {"field": "credit_score", "operator": ">=", "value": 700},
                {"field": "income", "operator": ">=", "value": 50000}
            ]
        }

        # Both true
        data = {"credit_score": 750, "income": 60000}
        assert _evaluate_condition(condition, data) == True

        # One false
        data = {"credit_score": 650, "income": 60000}
        assert _evaluate_condition(condition, data) == False

        # Both false
        data = {"credit_score": 650, "income": 40000}
        assert _evaluate_condition(condition, data) == False

    def test_or_condition(self):
        """Test OR logical operator."""
        from app.services.rules_engine import _evaluate_condition

        condition = {
            "or": [
                {"field": "employment_type", "operator": "==", "value": "salaried"},
                {"field": "business_years", "operator": ">=", "value": 3}
            ]
        }

        # First true
        data = {"employment_type": "salaried", "business_years": 0}
        assert _evaluate_condition(condition, data) == True

        # Second true
        data = {"employment_type": "self_employed", "business_years": 5}
        assert _evaluate_condition(condition, data) == True

        # Neither true
        data = {"employment_type": "self_employed", "business_years": 1}
        assert _evaluate_condition(condition, data) == False

    def test_not_condition(self):
        """Test NOT logical operator."""
        from app.services.rules_engine import _evaluate_condition

        condition = {
            "not": {"field": "blacklisted", "operator": "==", "value": True}
        }

        data = {"blacklisted": False}
        assert _evaluate_condition(condition, data) == True

        data = {"blacklisted": True}
        assert _evaluate_condition(condition, data) == False

    def test_complex_nested_condition(self):
        """Test complex nested conditions."""
        from app.services.rules_engine import _evaluate_condition

        condition = {
            "and": [
                {"field": "credit_score", "operator": ">=", "value": 650},
                {
                    "or": [
                        {"field": "income", "operator": ">=", "value": 100000},
                        {
                            "and": [
                                {"field": "income", "operator": ">=", "value": 50000},
                                {"field": "employment_type", "operator": "==", "value": "salaried"}
                            ]
                        }
                    ]
                }
            ]
        }

        # High income path
        data = {"credit_score": 700, "income": 120000, "employment_type": "self_employed"}
        assert _evaluate_condition(condition, data) == True

        # Salaried with medium income path
        data = {"credit_score": 700, "income": 60000, "employment_type": "salaried"}
        assert _evaluate_condition(condition, data) == True

        # Low income, not salaried
        data = {"credit_score": 700, "income": 60000, "employment_type": "self_employed"}
        assert _evaluate_condition(condition, data) == False


class TestRuleEvaluation:
    """Tests for rule evaluation."""

    def test_evaluate_single_rule(self):
        """Test evaluating a single rule."""
        from app.services.rules_engine import evaluate_rule
        import json

        rule = MagicMock()
        rule.condition_json = json.dumps({
            "field": "credit_score",
            "operator": ">=",
            "value": 750
        })
        rule.action_type = "approve"
        rule.action_params = json.dumps({"auto_approve": True})

        data = {"credit_score": 800}
        matched, action_type, action_params = evaluate_rule(rule, data)

        assert matched == True
        assert action_type == "approve"
        assert action_params == {"auto_approve": True}

    def test_rule_not_matched(self):
        """Test rule that doesn't match."""
        from app.services.rules_engine import evaluate_rule
        import json

        rule = MagicMock()
        rule.condition_json = json.dumps({
            "field": "credit_score",
            "operator": ">=",
            "value": 750
        })
        rule.action_type = "approve"
        rule.action_params = None

        data = {"credit_score": 650}
        matched, action_type, action_params = evaluate_rule(rule, data)

        assert matched == False
        assert action_type is None


class TestGetNestedValue:
    """Tests for nested value extraction."""

    def test_simple_key(self):
        """Test simple key access."""
        from app.services.rules_engine import _get_nested_value

        data = {"name": "John"}
        assert _get_nested_value(data, "name") == "John"

    def test_nested_key(self):
        """Test nested key access."""
        from app.services.rules_engine import _get_nested_value

        data = {"borrower": {"details": {"income": 50000}}}
        assert _get_nested_value(data, "borrower.details.income") == 50000

    def test_missing_key(self):
        """Test missing key returns None."""
        from app.services.rules_engine import _get_nested_value

        data = {"name": "John"}
        assert _get_nested_value(data, "age") is None
        assert _get_nested_value(data, "address.city") is None

    def test_non_dict_intermediate(self):
        """Test non-dict intermediate returns None."""
        from app.services.rules_engine import _get_nested_value

        data = {"name": "John"}
        assert _get_nested_value(data, "name.first") is None


class TestStringOperators:
    """Tests for string operators."""

    def test_contains_operator(self):
        """Test contains operator."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "email", "operator": "contains", "value": "@gmail"}

        data = {"email": "user@gmail.com"}
        assert _evaluate_condition(condition, data) == True

        data = {"email": "user@yahoo.com"}
        assert _evaluate_condition(condition, data) == False

    def test_starts_with_operator(self):
        """Test starts_with operator."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "phone", "operator": "starts_with", "value": "+91"}

        data = {"phone": "+91 9876543210"}
        assert _evaluate_condition(condition, data) == True

        data = {"phone": "+1 1234567890"}
        assert _evaluate_condition(condition, data) == False

    def test_ends_with_operator(self):
        """Test ends_with operator."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "email", "operator": "ends_with", "value": ".com"}

        data = {"email": "user@example.com"}
        assert _evaluate_condition(condition, data) == True

        data = {"email": "user@example.org"}
        assert _evaluate_condition(condition, data) == False


class TestEdgeCases:
    """Tests for edge cases."""

    def test_missing_field(self):
        """Test evaluation with missing field."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "missing_field", "operator": "==", "value": "test"}
        data = {"other_field": "value"}

        # Missing field should return False
        assert _evaluate_condition(condition, data) == False

    def test_invalid_operator(self):
        """Test evaluation with invalid operator."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "value", "operator": "invalid_op", "value": 10}
        data = {"value": 10}

        assert _evaluate_condition(condition, data) == False

    def test_empty_condition(self):
        """Test evaluation with empty condition."""
        from app.services.rules_engine import _evaluate_condition

        condition = {}
        data = {"value": 10}

        assert _evaluate_condition(condition, data) == False

    def test_type_mismatch(self):
        """Test evaluation with type mismatch."""
        from app.services.rules_engine import _evaluate_condition

        condition = {"field": "value", "operator": ">", "value": 10}
        data = {"value": "not a number"}

        # Should handle gracefully
        assert _evaluate_condition(condition, data) == False
