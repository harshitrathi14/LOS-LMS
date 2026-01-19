from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter(prefix="/loan-applications", tags=["loan-applications"])


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
