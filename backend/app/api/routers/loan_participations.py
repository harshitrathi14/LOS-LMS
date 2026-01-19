from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.loan_account import LoanAccount
from app.models.loan_participation import LoanParticipation
from app.models.loan_partner import LoanPartner
from app.schemas.loan_participation import (
    LoanParticipationCreate,
    LoanParticipationRead,
)

router = APIRouter(prefix="/loan-participations", tags=["loan-participations"])


@router.post("", response_model=LoanParticipationRead, status_code=201)
def create_participation(
    payload: LoanParticipationCreate, db: Session = Depends(get_db)
) -> LoanParticipation:
    if payload.share_percent <= 0 or payload.share_percent > 100:
        raise HTTPException(
            status_code=400, detail="Share percent must be between 0 and 100"
        )
    account = (
        db.query(LoanAccount)
        .filter(LoanAccount.id == payload.loan_account_id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    partner = db.query(LoanPartner).filter(LoanPartner.id == payload.partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Loan partner not found")

    participation = LoanParticipation(**payload.model_dump())
    db.add(participation)
    db.commit()
    db.refresh(participation)
    return participation


@router.get("", response_model=list[LoanParticipationRead])
def list_participations(
    db: Session = Depends(get_db),
    loan_account_id: int | None = None,
    partner_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[LoanParticipation]:
    query = db.query(LoanParticipation)
    if loan_account_id is not None:
        query = query.filter(LoanParticipation.loan_account_id == loan_account_id)
    if partner_id is not None:
        query = query.filter(LoanParticipation.partner_id == partner_id)
    return query.offset(offset).limit(limit).all()
