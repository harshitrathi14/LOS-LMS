from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.loan_product import LoanProduct
from app.schemas.loan_product import LoanProductCreate, LoanProductRead

router = APIRouter(prefix="/loan-products", tags=["loan-products"])


@router.post("", response_model=LoanProductRead, status_code=201)
def create_loan_product(
    payload: LoanProductCreate, db: Session = Depends(get_db)
) -> LoanProduct:
    product = LoanProduct(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=list[LoanProductRead])
def list_loan_products(
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
) -> list[LoanProduct]:
    return db.query(LoanProduct).offset(offset).limit(limit).all()


@router.get("/{product_id}", response_model=LoanProductRead)
def get_loan_product(product_id: int, db: Session = Depends(get_db)) -> LoanProduct:
    product = db.query(LoanProduct).filter(LoanProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Loan product not found")
    return product
