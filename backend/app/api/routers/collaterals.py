"""Collateral API endpoints for LAP (Loan Against Property)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.collateral import (
    Collateral,
    CollateralInsurance,
    CollateralLegalVerification,
    CollateralValuation,
)
from app.models.loan_application import LoanApplication
from app.schemas.collateral import (
    CollateralCreate,
    CollateralInsuranceCreate,
    CollateralInsuranceRead,
    CollateralLegalVerificationCreate,
    CollateralLegalVerificationRead,
    CollateralRead,
    CollateralUpdate,
    CollateralValuationCreate,
    CollateralValuationRead,
)
from app.services import collateral as collateral_service

router = APIRouter(prefix="/collaterals", tags=["collaterals"])


class LinkAccountRequest(BaseModel):
    loan_account_id: int


@router.post("", response_model=CollateralRead, status_code=201)
def create_collateral(
    payload: CollateralCreate, db: Session = Depends(get_db)
) -> Collateral:
    application = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == payload.application_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Loan application not found")

    return collateral_service.create_collateral(payload.model_dump(), db)


@router.get("", response_model=list[CollateralRead])
def list_collaterals(
    db: Session = Depends(get_db),
    application_id: int | None = None,
    loan_account_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Collateral]:
    query = db.query(Collateral)
    if application_id is not None:
        query = query.filter(Collateral.application_id == application_id)
    if loan_account_id is not None:
        query = query.filter(Collateral.loan_account_id == loan_account_id)
    return query.offset(offset).limit(limit).all()


@router.get("/{collateral_id}", response_model=CollateralRead)
def get_collateral(collateral_id: int, db: Session = Depends(get_db)) -> Collateral:
    collateral = db.query(Collateral).filter(Collateral.id == collateral_id).first()
    if not collateral:
        raise HTTPException(status_code=404, detail="Collateral not found")
    return collateral


@router.patch("/{collateral_id}", response_model=CollateralRead)
def update_collateral(
    collateral_id: int, payload: CollateralUpdate, db: Session = Depends(get_db)
) -> Collateral:
    try:
        return collateral_service.update_collateral(
            collateral_id, payload.model_dump(exclude_unset=True), db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Valuations ---


@router.post(
    "/{collateral_id}/valuations",
    response_model=CollateralValuationRead,
    status_code=201,
)
def add_valuation(
    collateral_id: int,
    payload: CollateralValuationCreate,
    db: Session = Depends(get_db),
) -> CollateralValuation:
    try:
        return collateral_service.add_valuation(
            collateral_id, payload.model_dump(), db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{collateral_id}/valuations", response_model=list[CollateralValuationRead]
)
def list_valuations(
    collateral_id: int, db: Session = Depends(get_db)
) -> list[CollateralValuation]:
    return (
        db.query(CollateralValuation)
        .filter(CollateralValuation.collateral_id == collateral_id)
        .order_by(CollateralValuation.valuation_date.desc())
        .all()
    )


# --- Insurance ---


@router.post(
    "/{collateral_id}/insurance",
    response_model=CollateralInsuranceRead,
    status_code=201,
)
def add_insurance(
    collateral_id: int,
    payload: CollateralInsuranceCreate,
    db: Session = Depends(get_db),
) -> CollateralInsurance:
    try:
        return collateral_service.add_insurance(
            collateral_id, payload.model_dump(), db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{collateral_id}/insurance", response_model=list[CollateralInsuranceRead]
)
def list_insurance(
    collateral_id: int, db: Session = Depends(get_db)
) -> list[CollateralInsurance]:
    return (
        db.query(CollateralInsurance)
        .filter(CollateralInsurance.collateral_id == collateral_id)
        .all()
    )


# --- Legal Verifications ---


@router.post(
    "/{collateral_id}/legal-verifications",
    response_model=CollateralLegalVerificationRead,
    status_code=201,
)
def add_legal_verification(
    collateral_id: int,
    payload: CollateralLegalVerificationCreate,
    db: Session = Depends(get_db),
) -> CollateralLegalVerification:
    try:
        return collateral_service.add_legal_verification(
            collateral_id, payload.model_dump(), db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{collateral_id}/legal-verifications",
    response_model=list[CollateralLegalVerificationRead],
)
def list_legal_verifications(
    collateral_id: int, db: Session = Depends(get_db)
) -> list[CollateralLegalVerification]:
    return (
        db.query(CollateralLegalVerification)
        .filter(CollateralLegalVerification.collateral_id == collateral_id)
        .all()
    )


# --- LTV & Linking ---


@router.get("/{collateral_id}/ltv")
def get_ltv(collateral_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return collateral_service.calculate_ltv(collateral_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{collateral_id}/link-account", response_model=CollateralRead)
def link_account(
    collateral_id: int,
    payload: LinkAccountRequest,
    db: Session = Depends(get_db),
) -> Collateral:
    try:
        return collateral_service.link_collateral_to_account(
            collateral_id, payload.loan_account_id, db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{collateral_id}/summary")
def get_summary(collateral_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return collateral_service.get_collateral_summary(collateral_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
