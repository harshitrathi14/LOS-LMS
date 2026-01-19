"""
Rules engine service.

Handles:
- Rule evaluation
- Credit decisioning
- Score calculation
"""

from __future__ import annotations

import json
import operator
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.rules import RuleSet, DecisionRule, RuleExecutionLog


# Operator mappings
OPERATORS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
    "contains": lambda a, b: b in a if isinstance(a, str) else False,
    "starts_with": lambda a, b: a.startswith(b) if isinstance(a, str) else False,
    "ends_with": lambda a, b: a.endswith(b) if isinstance(a, str) else False,
    "is_null": lambda a, _: a is None,
    "is_not_null": lambda a, _: a is not None,
    "between": lambda a, b: b[0] <= a <= b[1] if isinstance(b, (list, tuple)) and len(b) == 2 else False,
}


def _get_nested_value(data: dict, field: str) -> Any:
    """
    Get a nested value from a dictionary using dot notation.

    Example: "borrower.income" gets data["borrower"]["income"]
    """
    keys = field.split(".")
    value = data
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value


def _evaluate_condition(condition: dict, data: dict) -> bool:
    """
    Evaluate a single condition against data.

    Supports:
    - Simple conditions: {"field": "credit_score", "operator": ">=", "value": 700}
    - AND conditions: {"and": [condition1, condition2, ...]}
    - OR conditions: {"or": [condition1, condition2, ...]}
    - NOT conditions: {"not": condition}
    """
    # Handle logical operators
    if "and" in condition:
        return all(_evaluate_condition(c, data) for c in condition["and"])

    if "or" in condition:
        return any(_evaluate_condition(c, data) for c in condition["or"])

    if "not" in condition:
        return not _evaluate_condition(condition["not"], data)

    # Simple condition
    field = condition.get("field")
    op = condition.get("operator")
    expected = condition.get("value")

    if not field or not op:
        return False

    actual = _get_nested_value(data, field)

    # Handle None values
    if op in ("is_null", "is_not_null"):
        return OPERATORS[op](actual, expected)

    if actual is None:
        return False

    # Get operator function
    op_func = OPERATORS.get(op)
    if not op_func:
        return False

    try:
        return op_func(actual, expected)
    except (TypeError, ValueError):
        return False


def evaluate_rule(rule: DecisionRule, data: dict) -> tuple[bool, str | None, dict | None]:
    """
    Evaluate a single rule against data.

    Args:
        rule: Decision rule to evaluate
        data: Input data dictionary

    Returns:
        Tuple of (condition_matched, action_type, action_params)
    """
    try:
        condition = json.loads(rule.condition_json)
        matched = _evaluate_condition(condition, data)

        if matched:
            action_params = json.loads(rule.action_params) if rule.action_params else {}
            return True, rule.action_type, action_params

        return False, None, None

    except (json.JSONDecodeError, Exception):
        return False, None, None


def evaluate_rule_set(
    rule_set_id: int,
    entity_type: str,
    entity_id: int,
    data: dict,
    db: Session
) -> dict:
    """
    Evaluate all rules in a rule set.

    Args:
        rule_set_id: Rule set ID
        entity_type: Type of entity being evaluated
        entity_id: Entity ID
        data: Input data dictionary
        db: Database session

    Returns:
        Dictionary with evaluation results
    """
    rule_set = db.query(RuleSet).filter(
        and_(
            RuleSet.id == rule_set_id,
            RuleSet.is_active == True
        )
    ).first()

    if not rule_set:
        raise ValueError(f"Rule set {rule_set_id} not found or inactive")

    rules = db.query(DecisionRule).filter(
        and_(
            DecisionRule.rule_set_id == rule_set_id,
            DecisionRule.is_active == True
        )
    ).order_by(DecisionRule.rule_order).all()

    results = {
        "rule_set_id": rule_set_id,
        "rule_set_code": rule_set.code,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "timestamp": datetime.utcnow().isoformat(),
        "rules_evaluated": 0,
        "rules_matched": 0,
        "actions": [],
        "score_adjustments": 0,
        "final_decision": None,
        "decision_reasons": []
    }

    score_base = data.get("credit_score", 0) or 0
    score_adjustments = 0

    for rule in rules:
        matched, action_type, action_params = evaluate_rule(rule, data)
        results["rules_evaluated"] += 1

        # Log execution
        log = RuleExecutionLog(
            rule_set_id=rule_set_id,
            rule_id=rule.id,
            entity_type=entity_type,
            entity_id=entity_id,
            input_data=json.dumps(data),
            condition_result=matched,
            action_taken=action_type if matched else None,
            action_result=json.dumps(action_params) if matched and action_params else None
        )
        db.add(log)

        if matched:
            results["rules_matched"] += 1
            results["actions"].append({
                "rule_id": rule.id,
                "rule_name": rule.rule_name,
                "action_type": action_type,
                "action_params": action_params
            })

            # Handle different action types
            if action_type == "approve":
                results["final_decision"] = "approved"
                results["decision_reasons"].append(rule.rule_name)

            elif action_type == "reject":
                results["final_decision"] = "rejected"
                reason = action_params.get("message", rule.rule_name) if action_params else rule.rule_name
                results["decision_reasons"].append(reason)

            elif action_type == "refer":
                if results["final_decision"] is None:
                    results["final_decision"] = "referred"
                results["decision_reasons"].append(f"Refer: {rule.rule_name}")

            elif action_type == "score_adjustment":
                adjustment = action_params.get("adjustment", 0) if action_params else 0
                score_adjustments += adjustment

            # Check if we should stop
            if rule.stop_on_match:
                break

    results["score_adjustments"] = score_adjustments
    results["adjusted_score"] = score_base + score_adjustments

    # If no decision made, default to referred
    if results["final_decision"] is None and results["rules_evaluated"] > 0:
        results["final_decision"] = "referred"
        results["decision_reasons"].append("No conclusive decision from rules")

    db.commit()

    return results


def run_eligibility_check(
    product_id: int,
    borrower_data: dict,
    db: Session
) -> dict:
    """
    Run eligibility rules for a product.

    Args:
        product_id: Loan product ID
        borrower_data: Borrower information dictionary
        db: Database session

    Returns:
        Eligibility result dictionary
    """
    # Find eligibility rule set for product
    rule_set = db.query(RuleSet).filter(
        and_(
            RuleSet.product_id == product_id,
            RuleSet.rule_type == "eligibility",
            RuleSet.is_active == True
        )
    ).first()

    if not rule_set:
        # No rules, assume eligible
        return {
            "eligible": True,
            "message": "No eligibility rules defined",
            "checks": []
        }

    result = evaluate_rule_set(
        rule_set_id=rule_set.id,
        entity_type="borrower",
        entity_id=borrower_data.get("id", 0),
        data=borrower_data,
        db=db
    )

    return {
        "eligible": result["final_decision"] != "rejected",
        "decision": result["final_decision"],
        "reasons": result["decision_reasons"],
        "rules_evaluated": result["rules_evaluated"],
        "rules_matched": result["rules_matched"]
    }


def run_credit_decision(
    application_id: int,
    application_data: dict,
    db: Session
) -> dict:
    """
    Run credit decision rules for a loan application.

    Args:
        application_id: Loan application ID
        application_data: Application data including borrower info
        db: Database session

    Returns:
        Credit decision result
    """
    product_id = application_data.get("product_id")

    # Find credit decision rule set
    rule_set = db.query(RuleSet).filter(
        and_(
            RuleSet.rule_type == "credit_decision",
            RuleSet.is_active == True,
            ((RuleSet.product_id == product_id) | (RuleSet.product_id.is_(None)))
        )
    ).order_by(RuleSet.priority).first()

    if not rule_set:
        return {
            "decision": "referred",
            "message": "No credit decision rules defined",
            "score": application_data.get("credit_score")
        }

    result = evaluate_rule_set(
        rule_set_id=rule_set.id,
        entity_type="loan_application",
        entity_id=application_id,
        data=application_data,
        db=db
    )

    return {
        "decision": result["final_decision"],
        "reasons": result["decision_reasons"],
        "base_score": application_data.get("credit_score"),
        "score_adjustments": result["score_adjustments"],
        "adjusted_score": result["adjusted_score"],
        "actions": result["actions"]
    }


def create_rule_set(
    code: str,
    name: str,
    rule_type: str,
    product_id: int | None = None,
    db: Session = None
) -> RuleSet:
    """
    Create a new rule set.

    Args:
        code: Unique code
        name: Display name
        rule_type: Type (eligibility, credit_decision, pricing, collection)
        product_id: Optional product ID
        db: Database session

    Returns:
        Created RuleSet
    """
    rule_set = RuleSet(
        code=code,
        name=name,
        rule_type=rule_type,
        product_id=product_id,
        is_active=True
    )

    db.add(rule_set)
    db.commit()
    db.refresh(rule_set)

    return rule_set


def add_rule(
    rule_set_id: int,
    rule_name: str,
    condition: dict,
    action_type: str,
    action_params: dict | None = None,
    rule_order: int = 1,
    stop_on_match: bool = False,
    db: Session = None
) -> DecisionRule:
    """
    Add a rule to a rule set.

    Args:
        rule_set_id: Rule set ID
        rule_name: Rule name
        condition: Condition dictionary
        action_type: Action type (approve, reject, refer, score_adjustment)
        action_params: Action parameters
        rule_order: Evaluation order
        stop_on_match: Whether to stop evaluation on match
        db: Database session

    Returns:
        Created DecisionRule
    """
    rule = DecisionRule(
        rule_set_id=rule_set_id,
        rule_name=rule_name,
        condition_json=json.dumps(condition),
        action_type=action_type,
        action_params=json.dumps(action_params) if action_params else None,
        rule_order=rule_order,
        stop_on_match=stop_on_match,
        is_active=True
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return rule
