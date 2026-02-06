"""Collection API endpoints for external collection software integration."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.collection import (
    CollectionAction,
    CollectionCase,
    EscalationRule,
    PromiseToPay,
)
from app.schemas.collection import (
    CollectionActionCreate,
    CollectionActionRead,
    CollectionCaseCreate,
    CollectionCaseRead,
    CollectionCaseUpdate,
    EscalationRuleCreate,
    EscalationRuleRead,
    PromiseToPayCreate,
    PromiseToPayRead,
    PromiseToPayUpdate,
)
from app.services import collection as collection_service

router = APIRouter(prefix="/collections", tags=["collections"])


# --- Cases ---


@router.post("/cases", response_model=CollectionCaseRead, status_code=201)
def open_case(
    payload: CollectionCaseCreate, db: Session = Depends(get_db)
) -> CollectionCase:
    try:
        return collection_service.open_collection_case(
            loan_account_id=payload.loan_account_id,
            assigned_to=payload.assigned_to,
            assigned_queue=payload.assigned_queue,
            priority=payload.priority,
            notes=payload.notes,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/cases", response_model=list[CollectionCaseRead])
def list_cases(
    db: Session = Depends(get_db),
    status: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    loan_account_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[CollectionCase]:
    query = db.query(CollectionCase)
    if status:
        query = query.filter(CollectionCase.status == status)
    if priority:
        query = query.filter(CollectionCase.priority == priority)
    if assigned_to:
        query = query.filter(CollectionCase.assigned_to == assigned_to)
    if loan_account_id is not None:
        query = query.filter(CollectionCase.loan_account_id == loan_account_id)
    return query.offset(offset).limit(limit).all()


@router.get("/cases/{case_id}")
def get_case_details(case_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return collection_service.get_case_details(case_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/cases/{case_id}", response_model=CollectionCaseRead)
def update_case(
    case_id: int, payload: CollectionCaseUpdate, db: Session = Depends(get_db)
) -> CollectionCase:
    case = db.query(CollectionCase).filter(CollectionCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Collection case not found")

    updates = payload.model_dump(exclude_unset=True)

    # Handle status transitions via service if status is being changed
    if "status" in updates:
        try:
            collection_service.update_case_status(
                case_id,
                updates.pop("status"),
                resolution_type=updates.pop("resolution_type", None),
                db=db,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Apply remaining updates
    for field, value in updates.items():
        setattr(case, field, value)

    db.commit()
    db.refresh(case)
    return case


# --- Actions ---


@router.post(
    "/cases/{case_id}/actions",
    response_model=CollectionActionRead,
    status_code=201,
)
def log_action(
    case_id: int,
    payload: CollectionActionCreate,
    db: Session = Depends(get_db),
) -> CollectionAction:
    try:
        return collection_service.log_collection_action(
            case_id=case_id,
            action_type=payload.action_type,
            performed_by=payload.performed_by,
            outcome=payload.outcome,
            outcome_details=payload.outcome_details,
            notes=payload.notes,
            next_action_date=payload.next_action_date,
            next_action_type=payload.next_action_type,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/cases/{case_id}/actions", response_model=list[CollectionActionRead]
)
def list_actions(
    case_id: int, db: Session = Depends(get_db)
) -> list[CollectionAction]:
    return (
        db.query(CollectionAction)
        .filter(CollectionAction.case_id == case_id)
        .order_by(CollectionAction.action_date.desc())
        .all()
    )


# --- Promise to Pay ---


@router.post(
    "/cases/{case_id}/promise-to-pay",
    response_model=PromiseToPayRead,
    status_code=201,
)
def record_ptp(
    case_id: int,
    payload: PromiseToPayCreate,
    db: Session = Depends(get_db),
) -> PromiseToPay:
    try:
        return collection_service.record_promise_to_pay(
            case_id=case_id,
            promise_date=payload.promise_date,
            payment_due_date=payload.payment_due_date,
            promised_amount=payload.promised_amount,
            notes=payload.notes,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/cases/{case_id}/promise-to-pay", response_model=list[PromiseToPayRead]
)
def list_ptps(
    case_id: int, db: Session = Depends(get_db)
) -> list[PromiseToPay]:
    return (
        db.query(PromiseToPay)
        .filter(PromiseToPay.case_id == case_id)
        .order_by(PromiseToPay.promise_date.desc())
        .all()
    )


@router.patch("/promise-to-pay/{promise_id}", response_model=PromiseToPayRead)
def update_ptp(
    promise_id: int,
    payload: PromiseToPayUpdate,
    db: Session = Depends(get_db),
) -> PromiseToPay:
    try:
        return collection_service.update_promise_status(
            promise_id=promise_id,
            actual_date=payload.actual_payment_date,
            actual_amount=payload.actual_amount,
            status=payload.status,
            notes=payload.notes,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Overdue Accounts & Dashboard ---


@router.get("/overdue-accounts")
def get_overdue_accounts(
    min_dpd: int = 1,
    max_dpd: int | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    return collection_service.get_overdue_accounts(
        min_dpd=min_dpd, max_dpd=max_dpd, db=db
    )


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)) -> dict:
    return collection_service.get_collection_dashboard(db)


# --- Escalation Rules ---


@router.post("/escalation-rules", response_model=EscalationRuleRead, status_code=201)
def create_escalation_rule(
    payload: EscalationRuleCreate, db: Session = Depends(get_db)
) -> EscalationRule:
    rule = EscalationRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/escalation-rules", response_model=list[EscalationRuleRead])
def list_escalation_rules(db: Session = Depends(get_db)) -> list[EscalationRule]:
    return db.query(EscalationRule).order_by(EscalationRule.priority).all()


@router.post("/cases/{case_id}/evaluate-escalation")
def evaluate_escalation(case_id: int, db: Session = Depends(get_db)) -> dict:
    case = db.query(CollectionCase).filter(CollectionCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Collection case not found")

    try:
        triggered = collection_service.evaluate_escalation_rules(
            case.loan_account_id, db
        )
        return {"case_id": case_id, "triggered_rules": triggered}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
