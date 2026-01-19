from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.loan_partner import LoanPartner
from app.schemas.loan_partner import LoanPartnerCreate, LoanPartnerRead

router = APIRouter(prefix="/loan-partners", tags=["loan-partners"])


@router.post("", response_model=LoanPartnerRead, status_code=201)
def create_loan_partner(
    payload: LoanPartnerCreate, db: Session = Depends(get_db)
) -> LoanPartner:
    partner = LoanPartner(**payload.model_dump())
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


@router.get("", response_model=list[LoanPartnerRead])
def list_loan_partners(
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
) -> list[LoanPartner]:
    return db.query(LoanPartner).offset(offset).limit(limit).all()


@router.get("/{partner_id}", response_model=LoanPartnerRead)
def get_loan_partner(partner_id: int, db: Session = Depends(get_db)) -> LoanPartner:
    partner = db.query(LoanPartner).filter(LoanPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Loan partner not found")
    return partner
