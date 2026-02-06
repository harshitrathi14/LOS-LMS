"""
LAP PAR report variable mapping service.

Provides:
- Canonical PAR header list
- LOS row builder (application-stage)
- LMS row builder (account-stage)
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import func as sql_func
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.loan_account import LoanAccount
    from app.models.loan_application import LoanApplication

from app.models.delinquency import DelinquencySnapshot
from app.models.loan_account import LoanAccount
from app.models.loan_participation import LoanParticipation
from app.models.loan_partner import LoanPartner
from app.models.payment import Payment
from app.models.payment_allocation import PaymentAllocation
from app.models.repayment_schedule import RepaymentSchedule
from app.models.schedule_config import ScheduleConfiguration
from app.services.delinquency import calculate_delinquency_metrics, get_bucket_for_dpd, get_dpd_classification
from app.services.payments import compute_dpd

LAP_PAR_HEADERS = [
    "Loan number",
    "Customer number",
    "Member Name",
    "Spouse Name",
    "Guarantor Name",
    "Guarantor Relation",
    "Office Name",
    "Office Code",
    "Center Name",
    "Center Code",
    "Group Name",
    "Group Code",
    "Center Formation Date",
    "Center Meeting Day",
    "Meeting Time",
    "Date of Birth",
    "Guarantor Date of Birth",
    "Religion",
    "Caste",
    "Occupation",
    "Residence Address Line-1(H no/Block)",
    "Village",
    "Gram Panchayat",
    "Block/Municipality",
    "District",
    "Pincode",
    "State",
    "Village Locale",
    "Residence Phone Number",
    "Mobile Number",
    "Gross Income",
    "Gender",
    "Officer Name",
    "Officer Employee Number",
    "Sales Officer Name",
    "Sales Officer Code",
    "Purpose of Loan",
    "Land Holding(Acres)",
    "Sub-Purpose",
    "Vendor Type",
    "Business Type",
    "Category of Loan",
    "Cycle Number",
    "Approval Date",
    "Disbursement Date",
    "First Installment Date",
    "Last Installment Date",
    "Product Name",
    "Product Code",
    "Product Interest Rate(%)",
    "Loan Amount",
    "Approved Amount",
    "LTV",
    "Processing Fees",
    "Insurance Charges",
    "Other Charges",
    "Installment Amount(First Slab)",
    "Loan Tenure",
    "Number of Installments",
    "Installment Frequency",
    "Current OD",
    "Principal Overdue",
    "Total Interest Collected",
    "Interest OverDue",
    "Overdue Days",
    "Voter ID Card",
    "Ration Card",
    "Aadhaar Number",
    "Pan Card",
    "Udhyam Registration No",
    "Number of Installments(Paid)",
    "Completed Installment Number",
    "Last Payment Date",
    "Last Payment Amount",
    "Parked Amount",
    "Principal Outstanding",
    "Interest Outstanding",
    "Loan Status",
    "Fund Source",
    "COVID19 Moratorium",
    "Is Restructured",
    "Account DPD Classification",
    "Customer DPD",
    "Customer DPD Classification",
    "Balance tenure",
    "Current Principal",
    "DPD Bucket",
    "Tenure",
    "BT Buckets",
    "Interest rate buckets",
    "LTV Buckets",
    "Loan amount bucket",
    "frequency",
    "partner_name",
    "Previous month POS",
    "Previous month CDPD",
    "Prev_Disbursement_Date",
    "New NPA",
    "Account Classification",
    "Actual Outstanding",
    "DA name",
    "NACL POS Factor",
    "UCIS ID COUNT",
    "UCIS",
    "month end file NPA",
    "Final DPD",
    "CDPD + UCIS",
    "CDPD + UCIS + QBRIK NPA",
    "CDPD + month end NPA",
    "Category",
    "Write off status",
    "Proposed writeoff",
]

DEMO_LAP_PAR_DEFAULTS = {
    "Spouse Name": "Sangeeta Devi",
    "Guarantor Name": "Mukesh Kumar",
    "Guarantor Relation": "Brother",
    "Office Name": "Patna Main Branch",
    "Office Code": "OFF-001",
    "Center Name": "Danapur Center 01",
    "Center Code": "CTR-001",
    "Group Name": "Sakhi Group A",
    "Group Code": "GRP-001",
    "Center Formation Date": date(2020, 1, 15),
    "Center Meeting Day": "Monday",
    "Meeting Time": "11:00 AM",
    "Guarantor Date of Birth": date(1980, 6, 1),
    "Religion": "Hindu",
    "Caste": "OBC",
    "Occupation": "Self Employed",
    "Residence Address Line-1(H no/Block)": "H-12, Ward 4",
    "Village": "Rampur",
    "Gram Panchayat": "Rampur GP",
    "Block/Municipality": "Danapur",
    "District": "Patna",
    "Pincode": "801503",
    "State": "Bihar",
    "Village Locale": "Rural",
    "Residence Phone Number": "0612-4000000",
    "Gross Income": 480000,
    "Gender": "M",
    "Officer Name": "Anita Kumari",
    "Officer Employee Number": "EMP-1007",
    "Sales Officer Name": "Rohit Sinha",
    "Sales Officer Code": "SO-204",
    "Purpose of Loan": "Business Expansion",
    "Land Holding(Acres)": 1.5,
    "Sub-Purpose": "Working Capital",
    "Vendor Type": "Retail",
    "Business Type": "Kirana",
    "Category of Loan": "LAP",
    "Cycle Number": 2,
    "LTV": 62.5,
    "Processing Fees": 2500,
    "Insurance Charges": 1400,
    "Other Charges": 300,
    "Voter ID Card": "VTR1234567",
    "Ration Card": "RAT9876543",
    "Aadhaar Number": "999988887777",
    "Pan Card": "ABCDE1234F",
    "Udhyam Registration No": "UDYAM-BR-12-0001111",
    "UCIS": "UCIS-DEMO-0001",
    "frequency": "monthly",
}


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _full_name(first_name: str | None, last_name: str | None) -> str | None:
    joined = " ".join([part for part in [first_name, last_name] if part])
    return joined or None


def _loan_amount_bucket(amount: float | Decimal | None) -> str | None:
    if amount is None:
        return None
    value = _to_float(amount)
    if value <= 100000:
        return "0-1L"
    if value <= 500000:
        return "1L-5L"
    if value <= 1000000:
        return "5L-10L"
    return "10L+"


def _interest_rate_bucket(rate: float | Decimal | None) -> str | None:
    if rate is None:
        return None
    value = _to_float(rate)
    if value < 10:
        return "<10%"
    if value < 12:
        return "10-12%"
    if value < 15:
        return "12-15%"
    return "15%+"


def _tenure_bucket(balance_tenure: int | None) -> str | None:
    if balance_tenure is None:
        return None
    if balance_tenure <= 12:
        return "0-12M"
    if balance_tenure <= 24:
        return "13-24M"
    if balance_tenure <= 36:
        return "25-36M"
    return "36M+"


def _ltv_bucket(ltv: float | Decimal | None) -> str | None:
    if ltv is None:
        return None
    value = _to_float(ltv)
    if value <= 50:
        return "<=50%"
    if value <= 70:
        return "51-70%"
    if value <= 80:
        return "71-80%"
    return ">80%"


def _account_classification(loan_account: "LoanAccount") -> str:
    if loan_account.is_written_off:
        return "written_off"
    if loan_account.is_npa:
        return "npa"
    if (loan_account.dpd or 0) > 0:
        return "delinquent"
    return "standard"


def _get_schedule_stats(loan_account_id: int, db: Session) -> dict[str, Any]:
    schedules = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.loan_account_id == loan_account_id
    ).order_by(RepaymentSchedule.installment_number).all()

    if not schedules:
        return {
            "first_installment_date": None,
            "last_installment_date": None,
            "first_installment_amount": None,
            "number_of_installments": 0,
            "installments_paid": 0,
            "completed_installment_number": 0,
            "balance_tenure": 0,
        }

    installments_paid = sum(1 for item in schedules if item.status == "paid")
    completed_installment_number = max(
        [item.installment_number for item in schedules if item.status == "paid"],
        default=0
    )
    number_of_installments = len(schedules)

    return {
        "first_installment_date": schedules[0].due_date,
        "last_installment_date": schedules[-1].due_date,
        "first_installment_amount": _to_float(schedules[0].total_due),
        "number_of_installments": number_of_installments,
        "installments_paid": installments_paid,
        "completed_installment_number": completed_installment_number,
        "balance_tenure": max(number_of_installments - completed_installment_number, 0),
    }


def _get_last_payment(loan_account_id: int, db: Session) -> Payment | None:
    return db.query(Payment).filter(
        Payment.loan_account_id == loan_account_id
    ).order_by(Payment.paid_at.desc()).first()


def _get_total_interest_collected(loan_account_id: int, db: Session) -> float:
    total_interest = db.query(sql_func.sum(PaymentAllocation.interest_allocated)).join(
        Payment, Payment.id == PaymentAllocation.payment_id
    ).filter(
        Payment.loan_account_id == loan_account_id
    ).scalar()
    return _to_float(total_interest)


def _get_parked_amount(loan_account_id: int, db: Session) -> float:
    parked = db.query(sql_func.sum(Payment.unallocated_amount)).filter(
        Payment.loan_account_id == loan_account_id
    ).scalar()
    return _to_float(parked)


def _get_previous_month_snapshot(
    loan_account_id: int,
    as_of_date: date,
    db: Session
) -> DelinquencySnapshot | None:
    month_start = as_of_date.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)

    snapshot = db.query(DelinquencySnapshot).filter(
        DelinquencySnapshot.loan_account_id == loan_account_id,
        DelinquencySnapshot.snapshot_date == prev_month_end
    ).first()
    if snapshot:
        return snapshot

    return db.query(DelinquencySnapshot).filter(
        DelinquencySnapshot.loan_account_id == loan_account_id,
        DelinquencySnapshot.snapshot_date <= prev_month_end
    ).order_by(DelinquencySnapshot.snapshot_date.desc()).first()


def _get_partner_context(loan_account_id: int, db: Session) -> dict[str, Any]:
    participation = db.query(LoanParticipation).filter(
        LoanParticipation.loan_account_id == loan_account_id
    ).order_by(LoanParticipation.share_percent.desc()).first()

    if not participation:
        return {
            "partner_name": None,
            "da_name": None,
        }

    partner = db.query(LoanPartner).filter(
        LoanPartner.id == participation.partner_id
    ).first()

    partner_name = partner.name if partner else None
    da_name = partner_name if participation.participation_type == "assignment" else None

    return {
        "partner_name": partner_name,
        "da_name": da_name,
    }


def _get_moratorium_flag(loan_account_id: int, db: Session) -> bool:
    config = db.query(ScheduleConfiguration).filter(
        ScheduleConfiguration.loan_account_id == loan_account_id
    ).first()
    if not config:
        return False
    return bool((config.moratorium_months or 0) > 0)


def _with_custom_values(row: dict[str, Any], custom_values: dict[str, Any] | None) -> dict[str, Any]:
    if not custom_values:
        return row
    for key, value in custom_values.items():
        if key in row:
            row[key] = value
    return row


def _apply_demo_defaults(row: dict[str, Any], use_demo_defaults: bool) -> dict[str, Any]:
    if not use_demo_defaults:
        return row

    for key, value in DEMO_LAP_PAR_DEFAULTS.items():
        if key in row and row[key] in (None, ""):
            row[key] = value
    return row


def _derive_report_fields(row: dict[str, Any]) -> dict[str, Any]:
    loan_amount = row.get("Loan Amount")
    if loan_amount is not None:
        row["Loan amount bucket"] = _loan_amount_bucket(loan_amount)

    rate = row.get("Product Interest Rate(%)")
    if rate is not None:
        row["Interest rate buckets"] = _interest_rate_bucket(rate)

    ltv = row.get("LTV")
    if isinstance(ltv, (int, float, Decimal)):
        row["LTV Buckets"] = _ltv_bucket(ltv)

    balance_tenure = row.get("Balance tenure")
    if isinstance(balance_tenure, (int, float, Decimal)):
        row["BT Buckets"] = _tenure_bucket(int(balance_tenure))

    final_dpd = row.get("Final DPD")
    if isinstance(final_dpd, (int, float, Decimal)):
        dpd_int = int(final_dpd)
        row["DPD Bucket"] = get_bucket_for_dpd(dpd_int)
        npa_flag = bool(row.get("month end file NPA"))
        row["Account DPD Classification"] = get_dpd_classification(dpd_int, npa_flag)
        row["Customer DPD Classification"] = get_dpd_classification(dpd_int, npa_flag)

    return row


def get_lap_par_headers() -> list[str]:
    return list(LAP_PAR_HEADERS)


def get_lap_par_demo_defaults() -> dict[str, Any]:
    return dict(DEMO_LAP_PAR_DEFAULTS)


def blank_lap_par_row() -> dict[str, Any]:
    return {header: None for header in LAP_PAR_HEADERS}


def build_lap_lms_row(
    loan_account: "LoanAccount",
    as_of_date: date,
    db: Session,
    custom_values: dict[str, Any] | None = None,
    use_demo_defaults: bool = False,
) -> dict[str, Any]:
    """
    Build LAP PAR row for LMS stage (disbursed loan account).
    """
    row = blank_lap_par_row()

    application = loan_account.application
    borrower = application.borrower if application else None
    product = application.product if application else None

    dpd = compute_dpd(db, loan_account.id, as_of_date=as_of_date)
    delinquency_metrics = calculate_delinquency_metrics(loan_account, as_of_date, db)
    schedule_stats = _get_schedule_stats(loan_account.id, db)
    last_payment = _get_last_payment(loan_account.id, db)
    total_interest_collected = _get_total_interest_collected(loan_account.id, db)
    parked_amount = _get_parked_amount(loan_account.id, db)
    prev_snapshot = _get_previous_month_snapshot(loan_account.id, as_of_date, db)
    partner_context = _get_partner_context(loan_account.id, db)
    moratorium_flag = _get_moratorium_flag(loan_account.id, db)

    principal_outstanding = _to_float(loan_account.principal_outstanding)
    interest_outstanding = _to_float(loan_account.interest_outstanding)
    fees_outstanding = _to_float(loan_account.fees_outstanding)
    actual_outstanding = principal_outstanding + interest_outstanding + fees_outstanding

    member_name = _full_name(
        borrower.first_name if borrower else None,
        borrower.last_name if borrower else None
    )
    customer_number = (
        borrower.external_id
        if borrower and borrower.external_id
        else (borrower.id if borrower else None)
    )

    ltv_value = None
    if use_demo_defaults:
        ltv_value = DEMO_LAP_PAR_DEFAULTS.get("LTV")
    if custom_values and "LTV" in custom_values:
        ltv_value = custom_values["LTV"]
    nacl_pos_factor = None
    if _to_float(loan_account.principal_amount) > 0:
        nacl_pos_factor = round(
            actual_outstanding / _to_float(loan_account.principal_amount),
            6
        )

    row.update({
        "Loan number": loan_account.account_number,
        "Customer number": customer_number,
        "Member Name": member_name,
        "Date of Birth": borrower.date_of_birth if borrower else None,
        "Mobile Number": borrower.phone if borrower else None,
        "Approval Date": application.decision_at.date() if application and application.decision_at else None,
        "Disbursement Date": loan_account.disbursed_at.date() if loan_account.disbursed_at else None,
        "First Installment Date": schedule_stats["first_installment_date"],
        "Last Installment Date": schedule_stats["last_installment_date"],
        "Product Name": product.name if product else None,
        "Product Code": product.code if product else None,
        "Product Interest Rate(%)": _to_float(loan_account.interest_rate),
        "Loan Amount": _to_float(loan_account.principal_amount),
        "Approved Amount": _to_float(application.approved_amount) if application else None,
        "LTV": ltv_value,
        "Installment Amount(First Slab)": schedule_stats["first_installment_amount"],
        "Loan Tenure": loan_account.tenure_months,
        "Number of Installments": schedule_stats["number_of_installments"],
        "Installment Frequency": loan_account.repayment_frequency,
        "Current OD": delinquency_metrics["total_overdue"],
        "Principal Overdue": delinquency_metrics["overdue_principal"],
        "Total Interest Collected": total_interest_collected,
        "Interest OverDue": delinquency_metrics["overdue_interest"],
        "Overdue Days": dpd,
        "Number of Installments(Paid)": schedule_stats["installments_paid"],
        "Completed Installment Number": schedule_stats["completed_installment_number"],
        "Last Payment Date": last_payment.paid_at.date() if last_payment else None,
        "Last Payment Amount": _to_float(last_payment.amount) if last_payment else None,
        "Parked Amount": parked_amount,
        "Principal Outstanding": principal_outstanding,
        "Interest Outstanding": interest_outstanding,
        "Loan Status": loan_account.status,
        "Fund Source": application.channel if application else None,
        "COVID19 Moratorium": moratorium_flag,
        "Is Restructured": bool(loan_account.is_restructured),
        "Account DPD Classification": get_dpd_classification(dpd, bool(loan_account.is_npa)),
        "Customer DPD": dpd,
        "Customer DPD Classification": get_dpd_classification(dpd, bool(loan_account.is_npa)),
        "Balance tenure": schedule_stats["balance_tenure"],
        "Current Principal": principal_outstanding,
        "DPD Bucket": get_bucket_for_dpd(dpd),
        "Tenure": loan_account.tenure_months,
        "BT Buckets": _tenure_bucket(schedule_stats["balance_tenure"]),
        "Interest rate buckets": _interest_rate_bucket(loan_account.interest_rate),
        "LTV Buckets": _ltv_bucket(ltv_value if isinstance(ltv_value, (int, float, Decimal)) else None),
        "Loan amount bucket": _loan_amount_bucket(loan_account.principal_amount),
        "frequency": loan_account.repayment_frequency,
        "partner_name": partner_context["partner_name"],
        "Previous month POS": _to_float(prev_snapshot.principal_outstanding) if prev_snapshot else None,
        "Previous month CDPD": prev_snapshot.dpd if prev_snapshot else None,
        "Prev_Disbursement_Date": loan_account.disbursed_at.date() if loan_account.disbursed_at else None,
        "New NPA": bool(loan_account.npa_date == as_of_date) if loan_account.npa_date else False,
        "Account Classification": _account_classification(loan_account),
        "Actual Outstanding": round(actual_outstanding, 2),
        "DA name": partner_context["da_name"],
        "NACL POS Factor": nacl_pos_factor,
        "UCIS ID COUNT": 1 if borrower and borrower.external_id else 0,
        "UCIS": borrower.external_id if borrower else None,
        "month end file NPA": bool(loan_account.is_npa),
        "Final DPD": dpd,
        "CDPD + UCIS": f"{dpd}|{borrower.external_id}" if borrower and borrower.external_id else None,
        "CDPD + UCIS + QBRIK NPA": bool(dpd > 0 and borrower and borrower.external_id and loan_account.is_npa),
        "CDPD + month end NPA": bool(dpd > 0 and loan_account.is_npa),
        "Category": loan_account.npa_category or _account_classification(loan_account),
        "Write off status": bool(loan_account.is_written_off),
        "Proposed writeoff": bool(dpd >= 180 and not loan_account.is_written_off),
    })

    row = _apply_demo_defaults(row, use_demo_defaults=use_demo_defaults)
    row = _with_custom_values(row, custom_values)
    return _derive_report_fields(row)


def build_lap_los_row(
    application: "LoanApplication",
    as_of_date: date,
    db: Session,
    custom_values: dict[str, Any] | None = None,
    use_demo_defaults: bool = False,
) -> dict[str, Any]:
    """
    Build LAP PAR row for LOS stage (application).
    """
    loan_account = db.query(LoanAccount).filter(
        LoanAccount.application_id == application.id
    ).first()

    if loan_account:
        return build_lap_lms_row(
            loan_account=loan_account,
            as_of_date=as_of_date,
            db=db,
            custom_values=custom_values,
            use_demo_defaults=use_demo_defaults,
        )

    row = blank_lap_par_row()
    borrower = application.borrower
    product = application.product

    member_name = _full_name(
        borrower.first_name if borrower else None,
        borrower.last_name if borrower else None
    )
    customer_number = (
        borrower.external_id
        if borrower and borrower.external_id
        else (borrower.id if borrower else None)
    )

    row.update({
        "Loan number": None,
        "Customer number": customer_number,
        "Member Name": member_name,
        "Date of Birth": borrower.date_of_birth if borrower else None,
        "Mobile Number": borrower.phone if borrower else None,
        "Approval Date": application.decision_at.date() if application.decision_at else None,
        "Product Name": product.name if product else None,
        "Product Code": product.code if product else None,
        "Product Interest Rate(%)": _to_float(application.approved_rate) if application.approved_rate is not None else None,
        "Loan Amount": _to_float(application.requested_amount),
        "Approved Amount": _to_float(application.approved_amount) if application.approved_amount is not None else None,
        "Loan Tenure": application.requested_tenure_months,
        "Tenure": application.requested_tenure_months,
        "Loan Status": application.status,
        "Fund Source": application.channel,
        "Current OD": 0.0,
        "Principal Overdue": 0.0,
        "Interest OverDue": 0.0,
        "Overdue Days": 0,
        "Account DPD Classification": "standard",
        "Customer DPD": 0,
        "Customer DPD Classification": "standard",
        "DPD Bucket": get_bucket_for_dpd(0),
        "Final DPD": 0,
        "month end file NPA": False,
        "New NPA": False,
        "Account Classification": "standard",
        "Is Restructured": False,
        "Write off status": False,
        "Proposed writeoff": False,
    })

    row = _apply_demo_defaults(row, use_demo_defaults=use_demo_defaults)
    row = _with_custom_values(row, custom_values)
    return _derive_report_fields(row)
