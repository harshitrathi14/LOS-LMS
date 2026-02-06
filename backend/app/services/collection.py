"""
Collection service for external collection software integration.

Handles collection case management, actions, PTP tracking,
escalation rules, and dashboard analytics.
"""

from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.collection import (
    CollectionAction,
    CollectionCase,
    EscalationRule,
    PromiseToPay,
)
from app.models.loan_account import LoanAccount


def _generate_case_number(db: Session) -> str:
    """Generate a unique case number."""
    count = db.query(func.count(CollectionCase.id)).scalar() or 0
    return f"COL-{count + 1:06d}"


def open_collection_case(
    loan_account_id: int,
    assigned_to: str | None = None,
    assigned_queue: str | None = None,
    priority: str = "medium",
    notes: str | None = None,
    db: Session = None,
) -> CollectionCase:
    """
    Open a new collection case for a delinquent loan account.

    Auto-generates case_number and captures current DPD and overdue amount.
    """
    account = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if not account:
        raise ValueError(f"Loan account {loan_account_id} not found")

    dpd = account.dpd or 0
    overdue = float(
        (account.interest_outstanding or 0)
        + (account.fees_outstanding or 0)
    )

    case = CollectionCase(
        loan_account_id=loan_account_id,
        case_number=_generate_case_number(db),
        status="open",
        priority=priority,
        assigned_to=assigned_to,
        assigned_queue=assigned_queue,
        opened_date=date.today(),
        dpd_at_open=dpd,
        overdue_at_open=overdue,
        notes=notes,
    )

    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def update_case_status(
    case_id: int,
    status: str,
    resolution_type: str | None = None,
    db: Session = None,
) -> CollectionCase:
    """Update case status with validation."""
    case = db.query(CollectionCase).filter(CollectionCase.id == case_id).first()
    if not case:
        raise ValueError(f"Collection case {case_id} not found")

    valid_transitions = {
        "open": ["in_progress", "resolved", "closed"],
        "in_progress": ["resolved", "closed", "written_off"],
        "resolved": ["closed"],
    }

    allowed = valid_transitions.get(case.status, [])
    if status not in allowed:
        raise ValueError(
            f"Cannot transition from '{case.status}' to '{status}'. "
            f"Allowed: {allowed}"
        )

    case.status = status

    if status in ("resolved", "closed", "written_off"):
        case.resolution_date = date.today()
        if resolution_type:
            case.resolution_type = resolution_type

    db.commit()
    db.refresh(case)
    return case


def log_collection_action(
    case_id: int,
    action_type: str,
    performed_by: str,
    outcome: str | None = None,
    outcome_details: str | None = None,
    notes: str | None = None,
    next_action_date: date | None = None,
    next_action_type: str | None = None,
    db: Session = None,
) -> CollectionAction:
    """Log a collection action and update case dates."""
    case = db.query(CollectionCase).filter(CollectionCase.id == case_id).first()
    if not case:
        raise ValueError(f"Collection case {case_id} not found")

    action = CollectionAction(
        case_id=case_id,
        action_type=action_type,
        action_date=datetime.utcnow(),
        performed_by=performed_by,
        outcome=outcome,
        outcome_details=outcome_details,
        notes=notes,
        next_action_date=next_action_date,
        next_action_type=next_action_type,
    )
    db.add(action)
    db.flush()

    # Update case dates
    case.last_action_date = date.today()
    if next_action_date:
        case.next_action_date = next_action_date

    # Auto-transition to in_progress if open
    if case.status == "open":
        case.status = "in_progress"

    db.commit()
    db.refresh(action)
    return action


def record_promise_to_pay(
    case_id: int,
    promise_date: date,
    payment_due_date: date,
    promised_amount: float,
    notes: str | None = None,
    db: Session = None,
) -> PromiseToPay:
    """Record a customer's promise to pay."""
    case = db.query(CollectionCase).filter(CollectionCase.id == case_id).first()
    if not case:
        raise ValueError(f"Collection case {case_id} not found")

    ptp = PromiseToPay(
        case_id=case_id,
        promise_date=promise_date,
        payment_due_date=payment_due_date,
        promised_amount=promised_amount,
        status="pending",
        notes=notes,
    )

    db.add(ptp)
    db.commit()
    db.refresh(ptp)
    return ptp


def update_promise_status(
    promise_id: int,
    actual_date: date | None = None,
    actual_amount: float | None = None,
    status: str | None = None,
    notes: str | None = None,
    db: Session = None,
) -> PromiseToPay:
    """Update PTP status (kept/broken/partial)."""
    ptp = db.query(PromiseToPay).filter(PromiseToPay.id == promise_id).first()
    if not ptp:
        raise ValueError(f"Promise to pay {promise_id} not found")

    if actual_date:
        ptp.actual_payment_date = actual_date
    if actual_amount is not None:
        ptp.actual_amount = actual_amount
    if status:
        ptp.status = status
    if notes:
        ptp.notes = notes

    db.commit()
    db.refresh(ptp)
    return ptp


def get_case_details(case_id: int, db: Session) -> dict:
    """Get full case details with actions, PTPs, loan account summary, and collateral info."""
    case = db.query(CollectionCase).filter(CollectionCase.id == case_id).first()
    if not case:
        raise ValueError(f"Collection case {case_id} not found")

    account = db.query(LoanAccount).filter(
        LoanAccount.id == case.loan_account_id
    ).first()

    actions = (
        db.query(CollectionAction)
        .filter(CollectionAction.case_id == case_id)
        .order_by(CollectionAction.action_date.desc())
        .all()
    )

    promises = (
        db.query(PromiseToPay)
        .filter(PromiseToPay.case_id == case_id)
        .order_by(PromiseToPay.promise_date.desc())
        .all()
    )

    # Get collateral info if available
    collateral_info = None
    try:
        from app.models.collateral import Collateral

        collaterals = (
            db.query(Collateral)
            .filter(Collateral.loan_account_id == case.loan_account_id)
            .all()
        )
        if collaterals:
            collateral_info = [
                {
                    "id": c.id,
                    "property_type": c.property_type,
                    "city": c.city,
                    "market_value": c.market_value,
                    "status": c.status,
                }
                for c in collaterals
            ]
    except Exception:
        pass

    return {
        "case": {
            "id": case.id,
            "case_number": case.case_number,
            "status": case.status,
            "priority": case.priority,
            "assigned_to": case.assigned_to,
            "opened_date": str(case.opened_date),
            "dpd_at_open": case.dpd_at_open,
            "overdue_at_open": case.overdue_at_open,
            "last_action_date": str(case.last_action_date) if case.last_action_date else None,
            "next_action_date": str(case.next_action_date) if case.next_action_date else None,
            "resolution_date": str(case.resolution_date) if case.resolution_date else None,
            "resolution_type": case.resolution_type,
        },
        "loan_account": {
            "id": account.id,
            "account_number": account.account_number,
            "principal_outstanding": account.principal_outstanding,
            "interest_outstanding": account.interest_outstanding,
            "fees_outstanding": account.fees_outstanding,
            "dpd": account.dpd,
            "status": account.status,
        } if account else None,
        "collaterals": collateral_info,
        "actions": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "action_date": a.action_date.isoformat() if a.action_date else None,
                "performed_by": a.performed_by,
                "outcome": a.outcome,
                "notes": a.notes,
            }
            for a in actions
        ],
        "promises_to_pay": [
            {
                "id": p.id,
                "promise_date": str(p.promise_date),
                "payment_due_date": str(p.payment_due_date),
                "promised_amount": p.promised_amount,
                "actual_amount": p.actual_amount,
                "status": p.status,
            }
            for p in promises
        ],
    }


def get_overdue_accounts(
    min_dpd: int = 1,
    max_dpd: int | None = None,
    db: Session = None,
) -> list[dict]:
    """Query delinquent loan accounts for case allocation."""
    query = db.query(LoanAccount).filter(
        LoanAccount.dpd >= min_dpd,
        LoanAccount.status == "active",
    )
    if max_dpd is not None:
        query = query.filter(LoanAccount.dpd <= max_dpd)

    accounts = query.order_by(LoanAccount.dpd.desc()).all()

    return [
        {
            "loan_account_id": a.id,
            "account_number": a.account_number,
            "dpd": a.dpd,
            "principal_outstanding": a.principal_outstanding,
            "interest_outstanding": a.interest_outstanding,
            "fees_outstanding": a.fees_outstanding,
            "status": a.status,
            "has_open_case": db.query(CollectionCase).filter(
                CollectionCase.loan_account_id == a.id,
                CollectionCase.status.in_(["open", "in_progress"]),
            ).first() is not None,
        }
        for a in accounts
    ]


def get_collection_dashboard(db: Session) -> dict:
    """Summary dashboard: cases by status, priority, DPD bucket, resolution rates."""
    total = db.query(func.count(CollectionCase.id)).scalar() or 0

    # By status
    status_counts = dict(
        db.query(CollectionCase.status, func.count(CollectionCase.id))
        .group_by(CollectionCase.status)
        .all()
    )

    # By priority
    priority_counts = dict(
        db.query(CollectionCase.priority, func.count(CollectionCase.id))
        .group_by(CollectionCase.priority)
        .all()
    )

    # Resolution rate
    resolved = (status_counts.get("resolved", 0) + status_counts.get("closed", 0))
    resolution_rate = (resolved / total * 100) if total > 0 else 0

    return {
        "total_cases": total,
        "by_status": status_counts,
        "by_priority": priority_counts,
        "resolution_rate": round(resolution_rate, 2),
        "open_cases": status_counts.get("open", 0),
        "in_progress_cases": status_counts.get("in_progress", 0),
        "resolved_cases": resolved,
    }


def evaluate_escalation_rules(
    loan_account_id: int, db: Session
) -> list[dict]:
    """Evaluate escalation rules against a loan account's current state."""
    account = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if not account:
        raise ValueError(f"Loan account {loan_account_id} not found")

    rules = (
        db.query(EscalationRule)
        .filter(EscalationRule.is_active == True)
        .order_by(EscalationRule.priority)
        .all()
    )

    triggered = []
    for rule in rules:
        # Check product filter
        if rule.applies_to_product_id:
            app = account.application
            if app and app.product_id != rule.applies_to_product_id:
                continue

        match = True

        if rule.trigger_dpd is not None and account.dpd < rule.trigger_dpd:
            match = False

        if rule.trigger_amount is not None:
            overdue = (account.interest_outstanding or 0) + (account.fees_outstanding or 0)
            if overdue < rule.trigger_amount:
                match = False

        if rule.trigger_bucket is not None:
            # Map DPD to bucket
            dpd = account.dpd or 0
            if dpd <= 30:
                bucket = "SMA-0"
            elif dpd <= 60:
                bucket = "SMA-1"
            elif dpd <= 90:
                bucket = "SMA-2"
            else:
                bucket = "NPA"

            if bucket != rule.trigger_bucket:
                match = False

        if match:
            triggered.append({
                "rule_id": rule.id,
                "rule_name": rule.name,
                "action_type": rule.action_type,
                "action_config": json.loads(rule.action_config) if rule.action_config else None,
            })

    return triggered
