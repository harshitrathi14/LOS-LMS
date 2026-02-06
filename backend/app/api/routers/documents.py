from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.borrower import Borrower
from app.models.collateral import Collateral
from app.models.document import Document
from app.models.loan_account import LoanAccount
from app.models.loan_application import LoanApplication
from app.schemas.document import DocumentCreate, DocumentRead

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentRead, status_code=201)
def create_document(
    payload: DocumentCreate, db: Session = Depends(get_db)
) -> Document:
    if not any([payload.borrower_id, payload.application_id, payload.loan_account_id, payload.collateral_id]):
        raise HTTPException(
            status_code=400,
            detail="Document must be linked to a borrower, application, loan account, or collateral",
        )
    if payload.borrower_id:
        borrower = (
            db.query(Borrower)
            .filter(Borrower.id == payload.borrower_id)
            .first()
        )
        if not borrower:
            raise HTTPException(status_code=404, detail="Borrower not found")
    if payload.application_id:
        application = (
            db.query(LoanApplication)
            .filter(LoanApplication.id == payload.application_id)
            .first()
        )
        if not application:
            raise HTTPException(status_code=404, detail="Loan application not found")
    if payload.loan_account_id:
        account = (
            db.query(LoanAccount)
            .filter(LoanAccount.id == payload.loan_account_id)
            .first()
        )
        if not account:
            raise HTTPException(status_code=404, detail="Loan account not found")
    if payload.collateral_id:
        collateral = (
            db.query(Collateral)
            .filter(Collateral.id == payload.collateral_id)
            .first()
        )
        if not collateral:
            raise HTTPException(status_code=404, detail="Collateral not found")

    document = Document(**payload.model_dump())
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("", response_model=list[DocumentRead])
def list_documents(
    db: Session = Depends(get_db),
    borrower_id: int | None = None,
    application_id: int | None = None,
    loan_account_id: int | None = None,
    collateral_id: int | None = None,
    media_type: str | None = None,
    section: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Document]:
    query = db.query(Document)
    if borrower_id is not None:
        query = query.filter(Document.borrower_id == borrower_id)
    if application_id is not None:
        query = query.filter(Document.application_id == application_id)
    if loan_account_id is not None:
        query = query.filter(Document.loan_account_id == loan_account_id)
    if collateral_id is not None:
        query = query.filter(Document.collateral_id == collateral_id)
    if media_type is not None:
        query = query.filter(Document.media_type == media_type)
    if section is not None:
        query = query.filter(Document.section == section)
    return query.offset(offset).limit(limit).all()


@router.get("/by-collateral/{collateral_id}", response_model=list[DocumentRead])
def list_documents_by_collateral(
    collateral_id: int,
    media_type: str | None = None,
    section: str | None = None,
    db: Session = Depends(get_db),
) -> list[Document]:
    query = db.query(Document).filter(Document.collateral_id == collateral_id)
    if media_type is not None:
        query = query.filter(Document.media_type == media_type)
    if section is not None:
        query = query.filter(Document.section == section)
    return query.all()


@router.get("/by-section/{section}", response_model=list[DocumentRead])
def list_documents_by_section(
    section: str,
    application_id: int | None = None,
    collateral_id: int | None = None,
    media_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[Document]:
    query = db.query(Document).filter(Document.section == section)
    if application_id is not None:
        query = query.filter(Document.application_id == application_id)
    if collateral_id is not None:
        query = query.filter(Document.collateral_id == collateral_id)
    if media_type is not None:
        query = query.filter(Document.media_type == media_type)
    return query.all()
