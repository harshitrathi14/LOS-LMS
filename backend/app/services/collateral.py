"""
Collateral service for LAP (Loan Against Property).

Handles collateral CRUD, valuation tracking, insurance, legal verification, and LTV.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.collateral import (
    Collateral,
    CollateralInsurance,
    CollateralLegalVerification,
    CollateralValuation,
)
from app.models.loan_account import LoanAccount

CENT = Decimal("0.01")


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def create_collateral(data: dict, db: Session) -> Collateral:
    """Create a new collateral record."""
    collateral = Collateral(**data)
    db.add(collateral)
    db.commit()
    db.refresh(collateral)
    return collateral


def update_collateral(collateral_id: int, data: dict, db: Session) -> Collateral:
    """Update an existing collateral record."""
    collateral = db.query(Collateral).filter(Collateral.id == collateral_id).first()
    if not collateral:
        raise ValueError(f"Collateral {collateral_id} not found")

    for field, value in data.items():
        setattr(collateral, field, value)

    db.commit()
    db.refresh(collateral)
    return collateral


def add_valuation(
    collateral_id: int, data: dict, db: Session
) -> CollateralValuation:
    """
    Add a valuation record and auto-update parent collateral snapshot fields.
    """
    collateral = db.query(Collateral).filter(Collateral.id == collateral_id).first()
    if not collateral:
        raise ValueError(f"Collateral {collateral_id} not found")

    valuation = CollateralValuation(collateral_id=collateral_id, **data)
    db.add(valuation)
    db.flush()

    # Auto-update parent snapshot
    collateral.market_value = valuation.market_value
    collateral.realizable_value = valuation.realizable_value
    collateral.distress_value = valuation.distress_value
    collateral.valuation_date = valuation.valuation_date
    collateral.valuer_name = valuation.valuer_name
    collateral.ltv_ratio = valuation.ltv_at_valuation

    # Recalculate LTV if linked to a loan account
    if collateral.loan_account_id:
        account = db.query(LoanAccount).filter(
            LoanAccount.id == collateral.loan_account_id
        ).first()
        if account and valuation.market_value:
            ltv = _to_decimal(account.principal_outstanding) / _to_decimal(
                valuation.market_value
            )
            collateral.ltv_ratio = float(ltv.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))

    db.commit()
    db.refresh(valuation)
    return valuation


def add_insurance(
    collateral_id: int, data: dict, db: Session
) -> CollateralInsurance:
    """Add an insurance record and auto-update parent collateral snapshot."""
    collateral = db.query(Collateral).filter(Collateral.id == collateral_id).first()
    if not collateral:
        raise ValueError(f"Collateral {collateral_id} not found")

    insurance = CollateralInsurance(collateral_id=collateral_id, **data)
    db.add(insurance)
    db.flush()

    # Auto-update parent snapshot with latest active insurance
    collateral.insurance_policy_number = insurance.policy_number
    collateral.insurance_expiry_date = insurance.expiry_date
    collateral.insured_value = insurance.insured_value

    db.commit()
    db.refresh(insurance)
    return insurance


def add_legal_verification(
    collateral_id: int, data: dict, db: Session
) -> CollateralLegalVerification:
    """
    Add a legal verification record.
    If all verifications are 'clear', sets parent legal_status='clear'.
    """
    collateral = db.query(Collateral).filter(Collateral.id == collateral_id).first()
    if not collateral:
        raise ValueError(f"Collateral {collateral_id} not found")

    verification = CollateralLegalVerification(collateral_id=collateral_id, **data)
    db.add(verification)
    db.flush()

    # Check if all verifications are clear
    all_verifications = (
        db.query(CollateralLegalVerification)
        .filter(CollateralLegalVerification.collateral_id == collateral_id)
        .all()
    )
    if all_verifications and all(
        v.verification_status == "clear" for v in all_verifications
    ):
        collateral.legal_status = "clear"
    elif any(v.verification_status == "issue_found" for v in all_verifications):
        collateral.legal_status = "issue_found"
    else:
        collateral.legal_status = "pending"

    db.commit()
    db.refresh(verification)
    return verification


def calculate_ltv(collateral_id: int, db: Session) -> dict:
    """
    Calculate LTV ratio for a collateral.

    Returns dict with ltv_ratio, outstanding, market_value.
    """
    collateral = db.query(Collateral).filter(Collateral.id == collateral_id).first()
    if not collateral:
        raise ValueError(f"Collateral {collateral_id} not found")

    market_value = _to_decimal(collateral.market_value)
    if market_value <= 0:
        return {
            "collateral_id": collateral_id,
            "ltv_ratio": None,
            "outstanding": None,
            "market_value": float(market_value),
            "message": "No market value available for LTV calculation",
        }

    outstanding = Decimal("0")
    if collateral.loan_account_id:
        account = db.query(LoanAccount).filter(
            LoanAccount.id == collateral.loan_account_id
        ).first()
        if account:
            outstanding = _to_decimal(account.principal_outstanding)
    elif collateral.application_id:
        from app.models.loan_application import LoanApplication

        application = db.query(LoanApplication).filter(
            LoanApplication.id == collateral.application_id
        ).first()
        if application:
            outstanding = _to_decimal(
                application.approved_amount or application.requested_amount
            )

    ltv = (outstanding / market_value * 100).quantize(CENT, rounding=ROUND_HALF_UP)

    return {
        "collateral_id": collateral_id,
        "ltv_ratio": float(ltv),
        "outstanding": float(outstanding),
        "market_value": float(market_value),
    }


def link_collateral_to_account(
    collateral_id: int, loan_account_id: int, db: Session
) -> Collateral:
    """Link a collateral to a loan account after disbursement."""
    collateral = db.query(Collateral).filter(Collateral.id == collateral_id).first()
    if not collateral:
        raise ValueError(f"Collateral {collateral_id} not found")

    account = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if not account:
        raise ValueError(f"Loan account {loan_account_id} not found")

    collateral.loan_account_id = loan_account_id
    db.commit()
    db.refresh(collateral)
    return collateral


def get_collaterals_for_application(
    application_id: int, db: Session
) -> list[Collateral]:
    """Get all collaterals for a loan application."""
    return (
        db.query(Collateral)
        .filter(Collateral.application_id == application_id)
        .all()
    )


def get_collateral_summary(collateral_id: int, db: Session) -> dict:
    """Get a full summary of a collateral with sub-records."""
    collateral = db.query(Collateral).filter(Collateral.id == collateral_id).first()
    if not collateral:
        raise ValueError(f"Collateral {collateral_id} not found")

    valuations = (
        db.query(CollateralValuation)
        .filter(CollateralValuation.collateral_id == collateral_id)
        .order_by(CollateralValuation.valuation_date.desc())
        .all()
    )

    insurance_records = (
        db.query(CollateralInsurance)
        .filter(CollateralInsurance.collateral_id == collateral_id)
        .all()
    )

    legal_verifications = (
        db.query(CollateralLegalVerification)
        .filter(CollateralLegalVerification.collateral_id == collateral_id)
        .all()
    )

    ltv_info = calculate_ltv(collateral_id, db)

    return {
        "collateral_id": collateral.id,
        "property_type": collateral.property_type,
        "address": f"{collateral.address_line1}, {collateral.city}, {collateral.state} - {collateral.pincode}",
        "owner_name": collateral.owner_name,
        "status": collateral.status,
        "is_primary_security": collateral.is_primary_security,
        "market_value": collateral.market_value,
        "legal_status": collateral.legal_status,
        "ltv": ltv_info,
        "valuation_count": len(valuations),
        "latest_valuation": {
            "date": str(valuations[0].valuation_date) if valuations else None,
            "market_value": valuations[0].market_value if valuations else None,
            "valuer": valuations[0].valuer_name if valuations else None,
        },
        "insurance": {
            "policy_number": collateral.insurance_policy_number,
            "expiry_date": str(collateral.insurance_expiry_date) if collateral.insurance_expiry_date else None,
            "insured_value": collateral.insured_value,
            "active_records": len([r for r in insurance_records if r.status == "active"]),
        },
        "legal_verifications": {
            "total": len(legal_verifications),
            "clear": len([v for v in legal_verifications if v.verification_status == "clear"]),
            "pending": len([v for v in legal_verifications if v.verification_status == "pending"]),
            "issues": len([v for v in legal_verifications if v.verification_status == "issue_found"]),
        },
    }
