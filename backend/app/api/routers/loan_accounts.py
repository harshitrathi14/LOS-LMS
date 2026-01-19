from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.loan_account import LoanAccount
from app.models.loan_application import LoanApplication
from app.models.loan_product import LoanProduct
from app.models.payment import Payment
from app.models.repayment_schedule import RepaymentSchedule
from app.schemas.loan_account import LoanAccountCreate, LoanAccountRead
from app.schemas.payment import PaymentCreate, PaymentRead
from app.schemas.repayment_schedule import RepaymentScheduleRead
from app.services.payments import apply_payment_and_update_dpd, compute_dpd
from app.services.schedule import generate_amortization_schedule

router = APIRouter(prefix="/loan-accounts", tags=["loan-accounts"])


@router.post("", response_model=LoanAccountRead, status_code=201)
def create_loan_account(
    payload: LoanAccountCreate, db: Session = Depends(get_db)
) -> LoanAccount:
    if payload.principal_amount <= 0:
        raise HTTPException(status_code=400, detail="Principal amount must be positive")
    if payload.tenure_months <= 0:
        raise HTTPException(status_code=400, detail="Tenure must be at least 1 month")
    if payload.interest_rate < 0:
        raise HTTPException(status_code=400, detail="Interest rate cannot be negative")
    application = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == payload.application_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Loan application not found")

    product = db.query(LoanProduct).filter(LoanProduct.id == application.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Loan product not found")

    account = LoanAccount(
        application_id=payload.application_id,
        account_number=payload.account_number,
        principal_amount=payload.principal_amount,
        principal_outstanding=payload.principal_amount,
        interest_outstanding=0,
        fees_outstanding=0,
        interest_rate=payload.interest_rate,
        interest_rate_type=payload.interest_rate_type or product.interest_rate_type,
        schedule_type=payload.schedule_type or product.schedule_type,
        repayment_frequency=payload.repayment_frequency or product.repayment_frequency,
        currency=payload.currency or product.currency,
        tenure_months=payload.tenure_months,
        start_date=payload.start_date,
        disbursed_at=payload.disbursed_at,
        status="active",
    )
    db.add(account)
    db.flush()

    try:
        schedule_items = generate_amortization_schedule(
            principal=float(payload.principal_amount),
            annual_rate=float(payload.interest_rate),
            tenure_months=int(payload.tenure_months),
            start_date=payload.start_date,
            schedule_type=payload.schedule_type or product.schedule_type,
            repayment_frequency=payload.repayment_frequency or product.repayment_frequency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    for item in schedule_items:
        schedule = RepaymentSchedule(
            loan_account_id=account.id,
            installment_number=item["installment_number"],
            due_date=item["due_date"],
            principal_due=item["principal_due"],
            interest_due=item["interest_due"],
            fees_due=item["fees_due"],
            total_due=item["total_due"],
        )
        db.add(schedule)

    if schedule_items:
        account.next_due_date = schedule_items[0]["due_date"]
        account.next_due_amount = schedule_items[0]["total_due"]

    if application.approved_amount is None:
        application.approved_amount = payload.principal_amount
    if application.approved_rate is None:
        application.approved_rate = payload.interest_rate
    if application.approved_tenure_months is None:
        application.approved_tenure_months = payload.tenure_months

    if payload.disbursed_at:
        application.status = "disbursed"
        application.decision_at = application.decision_at or datetime.utcnow()
    else:
        if application.status not in {"approved", "disbursed"}:
            application.status = "approved"
            application.decision_at = application.decision_at or datetime.utcnow()

    db.commit()
    db.refresh(account)
    return account


@router.get("", response_model=list[LoanAccountRead])
def list_loan_accounts(
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
) -> list[LoanAccount]:
    return db.query(LoanAccount).offset(offset).limit(limit).all()


@router.get("/{loan_account_id}", response_model=LoanAccountRead)
def get_loan_account(
    loan_account_id: int, db: Session = Depends(get_db)
) -> LoanAccount:
    account = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    account.dpd = compute_dpd(db, account.id)
    db.commit()
    db.refresh(account)
    return account


@router.get(
    "/{loan_account_id}/schedule",
    response_model=list[RepaymentScheduleRead],
)
def get_loan_schedule(
    loan_account_id: int, db: Session = Depends(get_db)
) -> list[RepaymentSchedule]:
    account = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Loan account not found")

    return (
        db.query(RepaymentSchedule)
        .filter(RepaymentSchedule.loan_account_id == account.id)
        .order_by(RepaymentSchedule.installment_number)
        .all()
    )


@router.post(
    "/{loan_account_id}/payments",
    response_model=PaymentRead,
    status_code=201,
)
def post_payment(
    loan_account_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
) -> Payment:
    account = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Loan account not found")
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be positive")

    payment = Payment(
        loan_account_id=loan_account_id,
        amount=payload.amount,
        currency=payload.currency,
        channel=payload.channel,
        reference=payload.reference,
    )
    if payload.paid_at is not None:
        payment.paid_at = payload.paid_at
    db.add(payment)
    db.flush()

    apply_payment_and_update_dpd(db, account, payment)

    db.commit()
    db.refresh(payment)
    return payment
