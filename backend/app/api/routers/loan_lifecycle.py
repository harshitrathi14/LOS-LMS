"""
Loan lifecycle management endpoints.

Handles restructuring, prepayment, closure, and write-off operations.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.loan_account import LoanAccount
from app.models.restructure import LoanRestructure
from app.models.prepayment import Prepayment
from app.models.write_off import WriteOff, WriteOffRecovery

router = APIRouter(prefix="/loan-lifecycle", tags=["loan-lifecycle"])


# ============ Pydantic Schemas ============

class RestructureRequest(BaseModel):
    """Request to create a restructure."""
    loan_account_id: int
    restructure_type: str  # rate_reduction, tenure_extension, principal_haircut, combination
    new_rate: Optional[float] = None
    new_tenure: Optional[int] = None
    principal_waiver: float = 0
    interest_waiver: float = 0
    fees_waiver: float = 0
    reason: str
    requested_by: str


class RestructureApproval(BaseModel):
    """Request to approve a restructure."""
    approved_by: str
    effective_date: Optional[date] = None


class RestructureRejection(BaseModel):
    """Request to reject a restructure."""
    rejected_by: str
    reason: str


class RestructureImpactRequest(BaseModel):
    """Request to calculate restructure impact."""
    loan_account_id: int
    new_rate: Optional[float] = None
    new_tenure: Optional[int] = None
    principal_waiver: float = 0


class PrepaymentRequest(BaseModel):
    """Request to process a prepayment."""
    loan_account_id: int
    prepayment_amount: float
    prepayment_date: date
    action_type: str  # reduce_emi, reduce_tenure, foreclosure
    payment_id: Optional[int] = None
    penalty_waived: float = 0
    processed_by: str


class PrepaymentOptionsRequest(BaseModel):
    """Request to get prepayment options."""
    loan_account_id: int
    prepayment_amount: float


class SettlementRequest(BaseModel):
    """Request for one-time settlement."""
    loan_account_id: int
    settlement_amount: float
    settlement_date: date
    approved_by: str
    reason: str


class WriteOffRequest(BaseModel):
    """Request to write off a loan."""
    loan_account_id: int
    write_off_date: date
    reason: str
    approved_by: str
    write_off_type: str = "full"  # full, partial, technical


class RecoveryRequest(BaseModel):
    """Request to record a recovery."""
    write_off_id: int
    recovery_date: date
    amount: float
    recovery_source: str  # borrower, guarantor, collateral, agency
    payment_id: Optional[int] = None
    agency_commission_percent: Optional[float] = None
    notes: str = ""


class AgencyAssignmentRequest(BaseModel):
    """Request to assign to collection agency."""
    write_off_id: int
    agency_name: str
    fee_percent: float


class RestructureResponse(BaseModel):
    """Restructure response."""
    id: int
    loan_account_id: int
    restructure_date: date
    restructure_type: str
    original_principal: float
    original_rate: float
    original_tenure: int
    new_principal: float
    new_rate: float
    new_tenure: int
    principal_waived: float
    status: str

    model_config = {"from_attributes": True}


class PrepaymentResponse(BaseModel):
    """Prepayment response."""
    id: int
    loan_account_id: int
    prepayment_date: date
    prepayment_amount: float
    penalty_amount: float
    principal_reduced: float
    action_type: str
    old_outstanding: float
    new_outstanding: float
    is_foreclosure: bool
    status: str

    model_config = {"from_attributes": True}


class WriteOffResponse(BaseModel):
    """Write-off response."""
    id: int
    loan_account_id: int
    write_off_date: date
    principal_written_off: float
    interest_written_off: float
    total_written_off: float
    dpd_at_write_off: int
    recovery_status: str
    total_recovered: float

    model_config = {"from_attributes": True}


class RecoveryResponse(BaseModel):
    """Recovery response."""
    id: int
    write_off_id: int
    recovery_date: date
    amount: float
    principal_recovered: float
    interest_recovered: float
    recovery_source: str
    net_recovery: float

    model_config = {"from_attributes": True}


# ============ Restructure Endpoints ============

@router.post("/restructure", response_model=RestructureResponse)
def create_restructure(request: RestructureRequest, db: Session = Depends(get_db)):
    """Create a restructure request for approval."""
    from app.services.restructure import create_restructure_request

    loan_account = db.query(LoanAccount).filter(
        LoanAccount.id == request.loan_account_id
    ).first()

    if not loan_account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    if loan_account.status not in ["active", "delinquent"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot restructure loan with status {loan_account.status}"
        )

    restructure = create_restructure_request(
        loan_account=loan_account,
        restructure_type=request.restructure_type,
        new_rate=request.new_rate,
        new_tenure=request.new_tenure,
        principal_waiver=request.principal_waiver,
        interest_waiver=request.interest_waiver,
        fees_waiver=request.fees_waiver,
        reason=request.reason,
        requested_by=request.requested_by,
        db=db
    )

    return restructure


@router.post("/restructure/{restructure_id}/approve", response_model=RestructureResponse)
def approve_restructure(
    restructure_id: int,
    approval: RestructureApproval,
    db: Session = Depends(get_db)
):
    """Approve a restructure request."""
    from app.services.restructure import approve_restructure as approve_svc

    try:
        restructure = approve_svc(
            restructure_id=restructure_id,
            approved_by=approval.approved_by,
            effective_date=approval.effective_date,
            db=db
        )
        return restructure
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/restructure/{restructure_id}/apply", response_model=dict)
def apply_restructure(restructure_id: int, db: Session = Depends(get_db)):
    """Apply an approved restructure to the loan."""
    from app.services.restructure import apply_restructure as apply_svc

    try:
        loan_account = apply_svc(restructure_id=restructure_id, db=db)
        return {
            "message": "Restructure applied successfully",
            "loan_account_id": loan_account.id,
            "new_principal": float(loan_account.principal_outstanding),
            "new_rate": float(loan_account.interest_rate),
            "new_tenure": loan_account.tenure_months
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/restructure/{restructure_id}/reject", response_model=RestructureResponse)
def reject_restructure(
    restructure_id: int,
    rejection: RestructureRejection,
    db: Session = Depends(get_db)
):
    """Reject a restructure request."""
    from app.services.restructure import reject_restructure as reject_svc

    try:
        restructure = reject_svc(
            restructure_id=restructure_id,
            rejected_by=rejection.rejected_by,
            reason=rejection.reason,
            db=db
        )
        return restructure
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/restructure/impact")
def calculate_restructure_impact(request: RestructureImpactRequest, db: Session = Depends(get_db)):
    """Calculate the impact of a proposed restructure."""
    from app.services.restructure import calculate_restructure_impact as calc_impact

    loan_account = db.query(LoanAccount).filter(
        LoanAccount.id == request.loan_account_id
    ).first()

    if not loan_account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    return calc_impact(
        loan_account=loan_account,
        new_rate=request.new_rate,
        new_tenure=request.new_tenure,
        principal_waiver=request.principal_waiver
    )


@router.get("/restructure/history/{loan_account_id}", response_model=list[RestructureResponse])
def get_restructure_history(loan_account_id: int, db: Session = Depends(get_db)):
    """Get restructure history for a loan account."""
    from app.services.restructure import get_restructure_history as get_history

    return get_history(loan_account_id=loan_account_id, db=db)


# ============ Prepayment Endpoints ============

@router.post("/prepayment/calculate")
def calculate_prepayment(loan_account_id: int, db: Session = Depends(get_db)):
    """Calculate full prepayment/foreclosure amount."""
    from app.services.prepayment import calculate_prepayment_amount

    loan_account = db.query(LoanAccount).filter(
        LoanAccount.id == loan_account_id
    ).first()

    if not loan_account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    return calculate_prepayment_amount(
        loan_account=loan_account,
        as_of_date=date.today(),
        db=db
    )


@router.post("/prepayment/options")
def get_prepayment_options(request: PrepaymentOptionsRequest, db: Session = Depends(get_db)):
    """Get prepayment options comparing reduce_emi vs reduce_tenure."""
    from app.services.prepayment import get_prepayment_options as get_options

    loan_account = db.query(LoanAccount).filter(
        LoanAccount.id == request.loan_account_id
    ).first()

    if not loan_account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    return get_options(
        loan_account=loan_account,
        prepayment_amount=request.prepayment_amount,
        db=db
    )


@router.post("/prepayment", response_model=PrepaymentResponse)
def process_prepayment(request: PrepaymentRequest, db: Session = Depends(get_db)):
    """Process a prepayment on a loan."""
    from app.services.prepayment import process_prepayment as process_svc

    loan_account = db.query(LoanAccount).filter(
        LoanAccount.id == request.loan_account_id
    ).first()

    if not loan_account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    if loan_account.status not in ["active", "delinquent"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot prepay loan with status {loan_account.status}"
        )

    try:
        prepayment = process_svc(
            loan_account=loan_account,
            prepayment_amount=request.prepayment_amount,
            prepayment_date=request.prepayment_date,
            action_type=request.action_type,
            payment_id=request.payment_id,
            penalty_waived=request.penalty_waived,
            processed_by=request.processed_by,
            db=db
        )
        return prepayment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/prepayment/history/{loan_account_id}", response_model=list[PrepaymentResponse])
def get_prepayment_history(loan_account_id: int, db: Session = Depends(get_db)):
    """Get prepayment history for a loan account."""
    from app.services.prepayment import get_prepayment_history as get_history

    return get_history(loan_account_id=loan_account_id, db=db)


# ============ Closure Endpoints ============

@router.get("/closure/options/{loan_account_id}")
def get_closure_options(loan_account_id: int, db: Session = Depends(get_db)):
    """Check loan closure eligibility and options."""
    from app.services.closure import can_close_loan

    loan_account = db.query(LoanAccount).filter(
        LoanAccount.id == loan_account_id
    ).first()

    if not loan_account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    return can_close_loan(loan_account=loan_account, db=db)


@router.post("/closure/normal/{loan_account_id}")
def close_loan_normal(loan_account_id: int, db: Session = Depends(get_db)):
    """Close a fully paid loan."""
    from app.services.closure import close_loan_normal as close_svc

    loan_account = db.query(LoanAccount).filter(
        LoanAccount.id == loan_account_id
    ).first()

    if not loan_account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    try:
        loan_account = close_svc(
            loan_account=loan_account,
            closure_date=date.today(),
            db=db
        )
        return {
            "message": "Loan closed successfully",
            "loan_account_id": loan_account.id,
            "closure_type": loan_account.closure_type,
            "closure_date": loan_account.closure_date
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/closure/settlement")
def close_loan_settlement(request: SettlementRequest, db: Session = Depends(get_db)):
    """Close a loan via one-time settlement."""
    from app.services.closure import close_loan_settlement as settle_svc

    loan_account = db.query(LoanAccount).filter(
        LoanAccount.id == request.loan_account_id
    ).first()

    if not loan_account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    try:
        loan_account = settle_svc(
            loan_account=loan_account,
            settlement_amount=request.settlement_amount,
            settlement_date=request.settlement_date,
            approved_by=request.approved_by,
            reason=request.reason,
            db=db
        )
        return {
            "message": "Loan settled successfully",
            "loan_account_id": loan_account.id,
            "closure_type": loan_account.closure_type,
            "settlement_amount": float(loan_account.settlement_amount),
            "closure_date": loan_account.closure_date
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Write-off Endpoints ============

@router.post("/write-off", response_model=WriteOffResponse)
def write_off_loan(request: WriteOffRequest, db: Session = Depends(get_db)):
    """Write off a delinquent loan."""
    from app.services.closure import write_off_loan as writeoff_svc

    loan_account = db.query(LoanAccount).filter(
        LoanAccount.id == request.loan_account_id
    ).first()

    if not loan_account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    try:
        write_off = writeoff_svc(
            loan_account=loan_account,
            write_off_date=request.write_off_date,
            reason=request.reason,
            approved_by=request.approved_by,
            write_off_type=request.write_off_type,
            db=db
        )
        return write_off
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/write-off/recovery", response_model=RecoveryResponse)
def record_recovery(request: RecoveryRequest, db: Session = Depends(get_db)):
    """Record a recovery against a written-off loan."""
    from app.services.closure import record_recovery as recovery_svc

    try:
        recovery = recovery_svc(
            write_off_id=request.write_off_id,
            recovery_date=request.recovery_date,
            amount=request.amount,
            recovery_source=request.recovery_source,
            payment_id=request.payment_id,
            agency_commission_percent=request.agency_commission_percent,
            notes=request.notes,
            db=db
        )
        return recovery
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/write-off/assign-agency")
def assign_to_agency(request: AgencyAssignmentRequest, db: Session = Depends(get_db)):
    """Assign a written-off loan to a collection agency."""
    from app.services.closure import assign_to_collection_agency

    try:
        write_off = assign_to_collection_agency(
            write_off_id=request.write_off_id,
            agency_name=request.agency_name,
            fee_percent=request.fee_percent,
            db=db
        )
        return {
            "message": "Assigned to collection agency",
            "write_off_id": write_off.id,
            "agency_name": write_off.assigned_to_agency,
            "fee_percent": float(write_off.agency_fee_percent)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/write-off/summary")
def get_write_off_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """Get write-off summary statistics."""
    from app.services.closure import get_write_off_summary as summary_svc

    return summary_svc(db=db, start_date=start_date, end_date=end_date)


@router.get("/write-off/{write_off_id}/recoveries", response_model=list[RecoveryResponse])
def get_recovery_history(write_off_id: int, db: Session = Depends(get_db)):
    """Get recovery history for a write-off."""
    from app.services.closure import get_recovery_history as history_svc

    return history_svc(write_off_id=write_off_id, db=db)
