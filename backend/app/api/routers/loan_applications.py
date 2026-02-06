from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.borrower import Borrower
from app.models.loan_application import LoanApplication
from app.models.loan_product import LoanProduct
from app.schemas.loan_application import (
    LoanApplicationCreate,
    LoanApplicationRead,
    LoanApplicationUpdate,
)
from app.services.par_report import (
    build_lap_los_row,
    get_lap_par_demo_defaults,
    get_lap_par_headers,
)
from app.services import lap_workflow

router = APIRouter(prefix="/loan-applications", tags=["loan-applications"])


class LapLosParRequest(BaseModel):
    as_of_date: date | None = None
    use_demo_defaults: bool = False
    custom_values: dict[str, str | int | float | bool | None] | None = None


# --- LAP Workflow Schemas ---

class WorkflowStartRequest(BaseModel):
    started_by: str
    priority: str = "medium"
    sla_hours: int | None = None


class WorkflowTransitionRequest(BaseModel):
    to_stage: str
    transitioned_by: str
    action: str
    comments: str | None = None


class WorkflowAssignRequest(BaseModel):
    assigned_to: str
    assigned_role: str | None = None


# --- LAP Workflow Endpoints ---


@router.post("/{application_id}/workflow/start")
def start_workflow(
    application_id: int,
    payload: WorkflowStartRequest,
    db: Session = Depends(get_db),
) -> dict:
    try:
        instance = lap_workflow.start_lap_workflow(
            application_id=application_id,
            started_by=payload.started_by,
            priority=payload.priority,
            sla_hours=payload.sla_hours,
            db=db,
        )
        return {
            "instance_id": instance.id,
            "current_stage": instance.current_stage,
            "is_active": instance.is_active,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{application_id}/workflow/transition")
def transition_workflow(
    application_id: int,
    payload: WorkflowTransitionRequest,
    db: Session = Depends(get_db),
) -> dict:
    try:
        instance = lap_workflow.transition_lap_workflow(
            application_id=application_id,
            to_stage=payload.to_stage,
            transitioned_by=payload.transitioned_by,
            action=payload.action,
            comments=payload.comments,
            db=db,
        )
        return {
            "instance_id": instance.id,
            "current_stage": instance.current_stage,
            "previous_stage": instance.previous_stage,
            "is_active": instance.is_active,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{application_id}/workflow/status")
def get_workflow_status(
    application_id: int,
    db: Session = Depends(get_db),
) -> dict:
    status = lap_workflow.get_lap_workflow_status(application_id, db)
    if not status:
        raise HTTPException(
            status_code=404,
            detail="No workflow found for this application",
        )
    return status


@router.post("/{application_id}/workflow/assign")
def assign_workflow(
    application_id: int,
    payload: WorkflowAssignRequest,
    db: Session = Depends(get_db),
) -> dict:
    try:
        instance = lap_workflow.assign_lap_workflow(
            application_id=application_id,
            assigned_to=payload.assigned_to,
            assigned_role=payload.assigned_role,
            db=db,
        )
        return {
            "instance_id": instance.id,
            "assigned_to": instance.assigned_to,
            "assigned_role": instance.assigned_role,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=LoanApplicationRead, status_code=201)
def create_loan_application(
    payload: LoanApplicationCreate, db: Session = Depends(get_db)
) -> LoanApplication:
    borrower = db.query(Borrower).filter(Borrower.id == payload.borrower_id).first()
    if not borrower:
        raise HTTPException(status_code=404, detail="Borrower not found")
    product = db.query(LoanProduct).filter(LoanProduct.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Loan product not found")

    application = LoanApplication(**payload.model_dump())
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("", response_model=list[LoanApplicationRead])
def list_loan_applications(
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
) -> list[LoanApplication]:
    return db.query(LoanApplication).offset(offset).limit(limit).all()


@router.get("/lap-par/headers")
def list_lap_par_headers() -> dict:
    return {"headers": get_lap_par_headers()}


@router.get("/lap-par/demo-defaults")
def list_lap_par_demo_defaults() -> dict:
    return {"demo_defaults": get_lap_par_demo_defaults()}


@router.get("/{application_id}/lap-los-par")
def get_lap_los_row(
    application_id: int,
    as_of_date: date | None = None,
    use_demo_defaults: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    application = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == application_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Loan application not found")

    report_date = as_of_date or date.today()
    return build_lap_los_row(
        application,
        report_date,
        db,
        use_demo_defaults=use_demo_defaults,
    )


@router.post("/{application_id}/lap-los-par")
def get_lap_los_row_with_overrides(
    application_id: int,
    payload: LapLosParRequest,
    db: Session = Depends(get_db),
) -> dict:
    application = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == application_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Loan application not found")

    report_date = payload.as_of_date or date.today()
    return build_lap_los_row(
        application,
        report_date,
        db,
        custom_values=payload.custom_values,
        use_demo_defaults=payload.use_demo_defaults,
    )


@router.get("/{application_id}", response_model=LoanApplicationRead)
def get_loan_application(
    application_id: int, db: Session = Depends(get_db)
) -> LoanApplication:
    application = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == application_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Loan application not found")
    return application


@router.patch("/{application_id}", response_model=LoanApplicationRead)
def update_loan_application(
    application_id: int,
    payload: LoanApplicationUpdate,
    db: Session = Depends(get_db),
) -> LoanApplication:
    application = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == application_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Loan application not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(application, field, value)

    if application.status in {"approved", "rejected", "disbursed"} and not application.decision_at:
        application.decision_at = payload.decision_at or datetime.utcnow()

    db.commit()
    db.refresh(application)
    return application
