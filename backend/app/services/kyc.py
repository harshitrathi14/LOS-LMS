"""
KYC verification service.

Handles:
- KYC verification tracking
- Document verification
- Credit bureau integration
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.kyc import (
    KYCVerification,
    KYCRequirement,
    CreditBureauReport
)


def create_kyc_verification(
    borrower_id: int,
    verification_type: str,
    document_id: int | None = None,
    document_type: str | None = None,
    document_number: str | None = None,
    db: Session = None
) -> KYCVerification:
    """
    Create a new KYC verification record.

    Args:
        borrower_id: Borrower ID
        verification_type: Type of verification
        document_id: Optional document ID
        document_type: Document type
        document_number: Document number
        db: Database session

    Returns:
        Created KYCVerification
    """
    verification = KYCVerification(
        borrower_id=borrower_id,
        verification_type=verification_type,
        document_id=document_id,
        document_type=document_type,
        document_number=document_number,
        verification_status="pending"
    )

    db.add(verification)
    db.commit()
    db.refresh(verification)

    return verification


def update_verification_status(
    verification_id: int,
    status: str,
    verified_by: str | None = None,
    verification_method: str | None = None,
    match_score: int | None = None,
    verification_data: dict | None = None,
    failure_reason: str | None = None,
    expiry_days: int | None = None,
    db: Session = None
) -> KYCVerification:
    """
    Update KYC verification status.

    Args:
        verification_id: Verification ID
        status: New status (verified, failed, expired)
        verified_by: Verifier
        verification_method: Method used
        match_score: Match score if applicable
        verification_data: Extracted data
        failure_reason: Reason for failure
        expiry_days: Days until expiry
        db: Database session

    Returns:
        Updated KYCVerification
    """
    verification = db.query(KYCVerification).filter(
        KYCVerification.id == verification_id
    ).first()

    if not verification:
        raise ValueError(f"Verification {verification_id} not found")

    verification.verification_status = status

    if status == "verified":
        verification.verified_at = datetime.utcnow()
        verification.verified_by = verified_by
        verification.verification_method = verification_method

        if match_score is not None:
            verification.match_score = match_score

        if verification_data:
            verification.verification_data = json.dumps(verification_data)

        if expiry_days:
            verification.expiry_date = date.today() + timedelta(days=expiry_days)

    elif status == "failed":
        verification.failure_reason = failure_reason
        verification.retry_count = (verification.retry_count or 0) + 1

    db.commit()
    db.refresh(verification)

    return verification


def check_kyc_completeness(
    borrower_id: int,
    product_id: int,
    db: Session
) -> dict:
    """
    Check if KYC is complete for a borrower applying for a product.

    Args:
        borrower_id: Borrower ID
        product_id: Product ID
        db: Database session

    Returns:
        KYC status dictionary
    """
    # Get requirements for the product
    requirements = db.query(KYCRequirement).filter(
        and_(
            KYCRequirement.product_id == product_id,
            KYCRequirement.is_active == True
        )
    ).all()

    if not requirements:
        return {
            "complete": True,
            "message": "No KYC requirements defined for product",
            "verifications": []
        }

    # Get borrower's verifications
    verifications = db.query(KYCVerification).filter(
        KYCVerification.borrower_id == borrower_id
    ).all()

    verification_map = {}
    for v in verifications:
        key = v.verification_type
        if key not in verification_map or v.verified_at and (
            not verification_map[key].verified_at or
            v.verified_at > verification_map[key].verified_at
        ):
            verification_map[key] = v

    results = []
    all_complete = True
    mandatory_complete = True

    for req in requirements:
        verification = verification_map.get(req.verification_type)

        status = "missing"
        is_valid = False

        if verification:
            if verification.verification_status == "verified":
                # Check if expired
                if verification.expiry_date and verification.expiry_date < date.today():
                    status = "expired"
                elif verification.match_score and verification.match_score < req.min_match_score:
                    status = "low_score"
                else:
                    status = "verified"
                    is_valid = True
            else:
                status = verification.verification_status

        if not is_valid:
            all_complete = False
            if req.is_mandatory:
                mandatory_complete = False

        results.append({
            "verification_type": req.verification_type,
            "is_mandatory": req.is_mandatory,
            "status": status,
            "is_valid": is_valid,
            "verification_id": verification.id if verification else None,
            "verified_at": verification.verified_at.isoformat() if verification and verification.verified_at else None,
            "expiry_date": verification.expiry_date.isoformat() if verification and verification.expiry_date else None
        })

    return {
        "complete": all_complete,
        "mandatory_complete": mandatory_complete,
        "message": "KYC complete" if all_complete else "KYC incomplete",
        "verifications": results
    }


def flag_suspicious_kyc(
    verification_id: int,
    flags: list[str],
    db: Session
) -> KYCVerification:
    """
    Flag a KYC verification as suspicious.

    Args:
        verification_id: Verification ID
        flags: List of risk flags
        db: Database session

    Returns:
        Updated KYCVerification
    """
    verification = db.query(KYCVerification).filter(
        KYCVerification.id == verification_id
    ).first()

    if not verification:
        raise ValueError(f"Verification {verification_id} not found")

    existing_flags = json.loads(verification.risk_flags) if verification.risk_flags else []
    existing_flags.extend(flags)

    verification.risk_flags = json.dumps(list(set(existing_flags)))
    verification.is_suspicious = True

    db.commit()
    db.refresh(verification)

    return verification


def create_credit_bureau_report(
    borrower_id: int,
    bureau_name: str,
    reference_number: str,
    credit_score: int | None = None,
    loan_application_id: int | None = None,
    report_data: dict | None = None,
    db: Session = None
) -> CreditBureauReport:
    """
    Create a credit bureau report record.

    Args:
        borrower_id: Borrower ID
        bureau_name: Bureau name
        reference_number: Bureau reference number
        credit_score: Credit score
        loan_application_id: Optional application ID
        report_data: Full report data
        db: Database session

    Returns:
        Created CreditBureauReport
    """
    report = CreditBureauReport(
        borrower_id=borrower_id,
        loan_application_id=loan_application_id,
        bureau_name=bureau_name,
        report_date=datetime.utcnow(),
        reference_number=reference_number,
        credit_score=credit_score,
        status="received"
    )

    if report_data:
        report.report_json = json.dumps(report_data)

        # Extract summary data
        report.total_accounts = report_data.get("total_accounts")
        report.active_accounts = report_data.get("active_accounts")
        report.overdue_accounts = report_data.get("overdue_accounts")
        report.total_outstanding = report_data.get("total_outstanding")
        report.total_overdue = report_data.get("total_overdue")
        report.max_dpd_last_12_months = report_data.get("max_dpd_last_12_months")
        report.enquiries_last_30_days = report_data.get("enquiries_last_30_days")
        report.enquiries_last_90_days = report_data.get("enquiries_last_90_days")
        report.enquiries_last_6_months = report_data.get("enquiries_last_6_months")

    db.add(report)
    db.commit()
    db.refresh(report)

    return report


def get_latest_credit_report(
    borrower_id: int,
    max_age_days: int = 90,
    db: Session = None
) -> CreditBureauReport | None:
    """
    Get the latest credit report for a borrower.

    Args:
        borrower_id: Borrower ID
        max_age_days: Maximum age of report in days
        db: Database session

    Returns:
        CreditBureauReport or None
    """
    cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

    report = db.query(CreditBureauReport).filter(
        and_(
            CreditBureauReport.borrower_id == borrower_id,
            CreditBureauReport.status == "received",
            CreditBureauReport.report_date >= cutoff_date
        )
    ).order_by(CreditBureauReport.report_date.desc()).first()

    return report


def get_borrower_kyc_summary(
    borrower_id: int,
    db: Session
) -> dict:
    """
    Get a summary of borrower's KYC status.

    Args:
        borrower_id: Borrower ID
        db: Database session

    Returns:
        Summary dictionary
    """
    verifications = db.query(KYCVerification).filter(
        KYCVerification.borrower_id == borrower_id
    ).all()

    credit_reports = db.query(CreditBureauReport).filter(
        CreditBureauReport.borrower_id == borrower_id
    ).order_by(CreditBureauReport.report_date.desc()).all()

    verified_count = sum(1 for v in verifications if v.verification_status == "verified")
    pending_count = sum(1 for v in verifications if v.verification_status == "pending")
    failed_count = sum(1 for v in verifications if v.verification_status == "failed")
    expired_count = sum(
        1 for v in verifications
        if v.verification_status == "verified" and v.expiry_date and v.expiry_date < date.today()
    )
    suspicious_count = sum(1 for v in verifications if v.is_suspicious)

    latest_credit_score = None
    if credit_reports:
        latest_credit_score = credit_reports[0].credit_score

    return {
        "borrower_id": borrower_id,
        "total_verifications": len(verifications),
        "verified": verified_count,
        "pending": pending_count,
        "failed": failed_count,
        "expired": expired_count,
        "suspicious": suspicious_count,
        "has_suspicious": suspicious_count > 0,
        "credit_reports_count": len(credit_reports),
        "latest_credit_score": latest_credit_score,
        "verifications": [
            {
                "id": v.id,
                "type": v.verification_type,
                "status": v.verification_status,
                "document_type": v.document_type,
                "verified_at": v.verified_at.isoformat() if v.verified_at else None,
                "expiry_date": v.expiry_date.isoformat() if v.expiry_date else None,
                "is_suspicious": v.is_suspicious
            }
            for v in verifications
        ]
    }


def setup_product_kyc_requirements(
    product_id: int,
    requirements: list[dict],
    db: Session
) -> list[KYCRequirement]:
    """
    Set up KYC requirements for a product.

    Args:
        product_id: Product ID
        requirements: List of requirement dictionaries
        db: Database session

    Returns:
        List of created KYCRequirement records
    """
    # Deactivate existing requirements
    db.query(KYCRequirement).filter(
        KYCRequirement.product_id == product_id
    ).update({"is_active": False})

    created = []
    for req in requirements:
        kyc_req = KYCRequirement(
            product_id=product_id,
            verification_type=req["verification_type"],
            accepted_documents_json=json.dumps(req.get("accepted_documents", [])),
            is_mandatory=req.get("is_mandatory", True),
            min_match_score=req.get("min_match_score", 80),
            validity_days=req.get("validity_days"),
            is_active=True
        )
        db.add(kyc_req)
        created.append(kyc_req)

    db.commit()

    for req in created:
        db.refresh(req)

    return created
