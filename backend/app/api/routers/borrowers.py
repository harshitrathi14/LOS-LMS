from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.borrower import Borrower
from app.schemas.borrower import BorrowerCreate, BorrowerRead

router = APIRouter(prefix="/borrowers", tags=["borrowers"])


@router.post("", response_model=BorrowerRead, status_code=201)
def create_borrower(payload: BorrowerCreate, db: Session = Depends(get_db)) -> Borrower:
    borrower = Borrower(**payload.model_dump())
    db.add(borrower)
    db.commit()
    db.refresh(borrower)
    return borrower


@router.get("", response_model=list[BorrowerRead])
def list_borrowers(
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
) -> list[Borrower]:
    return db.query(Borrower).offset(offset).limit(limit).all()


@router.get("/{borrower_id}", response_model=BorrowerRead)
def get_borrower(borrower_id: int, db: Session = Depends(get_db)) -> Borrower:
    borrower = db.query(Borrower).filter(Borrower.id == borrower_id).first()
    if not borrower:
        raise HTTPException(status_code=404, detail="Borrower not found")
    return borrower
