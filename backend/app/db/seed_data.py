"""Seed demo data for LOS/LMS application."""
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models.benchmark_rate import BenchmarkRate, BenchmarkRateHistory
from app.models.borrower import Borrower
from app.models.collateral import (
    Collateral,
    CollateralInsurance,
    CollateralLegalVerification,
    CollateralValuation,
)
from app.models.collection import (
    CollectionAction,
    CollectionCase,
    EscalationRule,
    PromiseToPay,
)
from app.models.delinquency import DelinquencySnapshot
from app.models.document import Document
from app.models.ecl import ECLConfiguration
from app.models.fldg import FLDGArrangement
from app.models.holiday_calendar import Holiday, HolidayCalendar
from app.models.investment import (
    InvestmentIssuer,
    InvestmentProduct,
    Investment,
    InvestmentCouponSchedule,
)
from app.models.loan_account import LoanAccount
from app.models.loan_application import LoanApplication
from app.models.loan_partner import LoanPartner
from app.models.loan_participation import LoanParticipation
from app.models.loan_product import LoanProduct
from app.models.payment import Payment
from app.models.payment_allocation import PaymentAllocation
from app.models.repayment_schedule import RepaymentSchedule
from app.models.selldown import SelldownBuyer


def seed_borrowers(db: Session) -> list[Borrower]:
    """Create sample borrowers."""
    borrowers_data = [
        {
            "external_id": "BRW001",
            "first_name": "Rajesh",
            "last_name": "Kumar",
            "date_of_birth": date(1985, 3, 15),
            "email": "rajesh.kumar@email.com",
            "phone": "+91-9876543210",
            "kyc_status": "verified",
        },
        {
            "external_id": "BRW002",
            "first_name": "Priya",
            "last_name": "Sharma",
            "date_of_birth": date(1990, 7, 22),
            "email": "priya.sharma@email.com",
            "phone": "+91-9876543211",
            "kyc_status": "verified",
        },
        {
            "external_id": "BRW003",
            "first_name": "Amit",
            "last_name": "Patel",
            "date_of_birth": date(1982, 11, 8),
            "email": "amit.patel@email.com",
            "phone": "+91-9876543212",
            "kyc_status": "verified",
        },
        {
            "external_id": "BRW004",
            "first_name": "Sneha",
            "last_name": "Gupta",
            "date_of_birth": date(1995, 1, 30),
            "email": "sneha.gupta@email.com",
            "phone": "+91-9876543213",
            "kyc_status": "pending",
        },
        {
            "external_id": "BRW005",
            "first_name": "Vikram",
            "last_name": "Singh",
            "date_of_birth": date(1978, 5, 12),
            "email": "vikram.singh@email.com",
            "phone": "+91-9876543214",
            "kyc_status": "verified",
        },
    ]

    borrowers = []
    for data in borrowers_data:
        borrower = Borrower(**data)
        db.add(borrower)
        borrowers.append(borrower)

    db.flush()
    return borrowers


def seed_loan_products(db: Session) -> list[LoanProduct]:
    """Create sample loan products."""
    products_data = [
        {
            "code": "PL-001",
            "name": "Personal Loan - Standard",
            "currency": "INR",
            "interest_rate_type": "fixed",
            "base_rate": Decimal("12.5000"),
            "schedule_type": "emi",
            "repayment_frequency": "monthly",
            "processing_fee_rate": Decimal("2.0000"),
            "penalty_rate": Decimal("2.0000"),
            "grace_days": 5,
            "min_tenure_months": 12,
            "max_tenure_months": 60,
        },
        {
            "code": "HL-001",
            "name": "Home Loan - Prime",
            "currency": "INR",
            "interest_rate_type": "floating",
            "base_rate": Decimal("8.5000"),
            "schedule_type": "emi",
            "repayment_frequency": "monthly",
            "processing_fee_rate": Decimal("0.5000"),
            "penalty_rate": Decimal("2.0000"),
            "grace_days": 7,
            "min_tenure_months": 60,
            "max_tenure_months": 360,
        },
        {
            "code": "BL-001",
            "name": "Business Loan - SME",
            "currency": "INR",
            "interest_rate_type": "fixed",
            "base_rate": Decimal("14.0000"),
            "schedule_type": "emi",
            "repayment_frequency": "monthly",
            "processing_fee_rate": Decimal("2.5000"),
            "penalty_rate": Decimal("3.0000"),
            "grace_days": 10,
            "min_tenure_months": 12,
            "max_tenure_months": 84,
        },
        {
            "code": "VL-001",
            "name": "Vehicle Loan - Auto",
            "currency": "INR",
            "interest_rate_type": "fixed",
            "base_rate": Decimal("9.5000"),
            "schedule_type": "emi",
            "repayment_frequency": "monthly",
            "processing_fee_rate": Decimal("1.5000"),
            "penalty_rate": Decimal("2.0000"),
            "grace_days": 5,
            "min_tenure_months": 12,
            "max_tenure_months": 84,
        },
        {
            "code": "GL-001",
            "name": "Gold Loan - Express",
            "currency": "INR",
            "interest_rate_type": "fixed",
            "base_rate": Decimal("10.0000"),
            "schedule_type": "bullet",
            "repayment_frequency": "monthly",
            "processing_fee_rate": Decimal("1.0000"),
            "penalty_rate": Decimal("2.0000"),
            "grace_days": 3,
            "min_tenure_months": 3,
            "max_tenure_months": 24,
        },
    ]

    products = []
    for data in products_data:
        product = LoanProduct(**data)
        db.add(product)
        products.append(product)

    db.flush()
    return products


def seed_loan_applications(db: Session, borrowers: list[Borrower], products: list[LoanProduct]) -> list[LoanApplication]:
    """Create sample loan applications in various statuses."""
    applications_data = [
        {
            "borrower_id": borrowers[0].id,
            "product_id": products[0].id,  # Personal Loan
            "status": "disbursed",
            "channel": "branch",
            "requested_amount": Decimal("500000.00"),
            "requested_tenure_months": 36,
            "credit_score": 750,
            "approved_amount": Decimal("500000.00"),
            "approved_rate": Decimal("12.5000"),
            "approved_tenure_months": 36,
            "decision_reason": "Good credit score, stable income",
        },
        {
            "borrower_id": borrowers[1].id,
            "product_id": products[1].id,  # Home Loan
            "status": "disbursed",
            "channel": "online",
            "requested_amount": Decimal("5000000.00"),
            "requested_tenure_months": 240,
            "credit_score": 780,
            "approved_amount": Decimal("4500000.00"),
            "approved_rate": Decimal("8.5000"),
            "approved_tenure_months": 240,
            "decision_reason": "Excellent credit history, property valuation approved",
        },
        {
            "borrower_id": borrowers[2].id,
            "product_id": products[2].id,  # Business Loan
            "status": "disbursed",
            "channel": "branch",
            "requested_amount": Decimal("2000000.00"),
            "requested_tenure_months": 48,
            "credit_score": 720,
            "approved_amount": Decimal("1500000.00"),
            "approved_rate": Decimal("14.0000"),
            "approved_tenure_months": 48,
            "decision_reason": "Profitable business, adequate collateral",
        },
        {
            "borrower_id": borrowers[3].id,
            "product_id": products[0].id,  # Personal Loan
            "status": "submitted",
            "channel": "mobile",
            "requested_amount": Decimal("300000.00"),
            "requested_tenure_months": 24,
            "credit_score": None,
        },
        {
            "borrower_id": borrowers[4].id,
            "product_id": products[3].id,  # Vehicle Loan
            "status": "approved",
            "channel": "dealer",
            "requested_amount": Decimal("800000.00"),
            "requested_tenure_months": 60,
            "credit_score": 740,
            "approved_amount": Decimal("800000.00"),
            "approved_rate": Decimal("9.5000"),
            "approved_tenure_months": 60,
            "decision_reason": "Good credit score, dealer verified",
        },
    ]

    applications = []
    for data in applications_data:
        application = LoanApplication(**data)
        db.add(application)
        applications.append(application)

    db.flush()
    return applications


def seed_loan_accounts(db: Session, applications: list[LoanApplication]) -> list[LoanAccount]:
    """Create loan accounts for disbursed applications."""
    today = date.today()

    accounts_data = [
        {
            "application_id": applications[0].id,
            "account_number": "LN2024000001",
            "principal_amount": Decimal("500000.00"),
            "principal_outstanding": Decimal("425000.00"),
            "interest_outstanding": Decimal("4500.00"),
            "fees_outstanding": Decimal("0.00"),
            "interest_rate": Decimal("12.5000"),
            "interest_rate_type": "fixed",
            "schedule_type": "emi",
            "tenure_months": 36,
            "start_date": today - timedelta(days=180),
            "disbursed_at": datetime.now() - timedelta(days=180),
            "next_due_date": today + timedelta(days=15),
            "next_due_amount": Decimal("16700.00"),
            "dpd": 0,
            "status": "active",
            "ecl_stage": 1,
        },
        {
            "application_id": applications[1].id,
            "account_number": "LN2024000002",
            "principal_amount": Decimal("4500000.00"),
            "principal_outstanding": Decimal("4450000.00"),
            "interest_outstanding": Decimal("32000.00"),
            "fees_outstanding": Decimal("0.00"),
            "interest_rate": Decimal("8.5000"),
            "interest_rate_type": "floating",
            "schedule_type": "emi",
            "tenure_months": 240,
            "start_date": today - timedelta(days=90),
            "disbursed_at": datetime.now() - timedelta(days=90),
            "next_due_date": today + timedelta(days=5),
            "next_due_amount": Decimal("42500.00"),
            "dpd": 0,
            "status": "active",
            "ecl_stage": 1,
            "is_co_lent": True,
            "co_lending_ratio": "80:20",
        },
        {
            "application_id": applications[2].id,
            "account_number": "LN2024000003",
            "principal_amount": Decimal("1500000.00"),
            "principal_outstanding": Decimal("1350000.00"),
            "interest_outstanding": Decimal("18500.00"),
            "fees_outstanding": Decimal("1500.00"),
            "interest_rate": Decimal("14.0000"),
            "interest_rate_type": "fixed",
            "schedule_type": "emi",
            "tenure_months": 48,
            "start_date": today - timedelta(days=120),
            "disbursed_at": datetime.now() - timedelta(days=120),
            "next_due_date": today - timedelta(days=25),
            "next_due_amount": Decimal("41000.00"),
            "dpd": 25,
            "status": "active",
            "ecl_stage": 1,
        },
    ]

    accounts = []
    for data in accounts_data:
        account = LoanAccount(**data)
        db.add(account)
        accounts.append(account)

    db.flush()
    return accounts


def seed_repayment_schedules(db: Session, accounts: list[LoanAccount]) -> None:
    """Create sample repayment schedules."""
    today = date.today()

    # Schedule for first account (Personal Loan)
    for i in range(6):
        schedule = RepaymentSchedule(
            loan_account_id=accounts[0].id,
            installment_number=i + 1,
            due_date=accounts[0].start_date + timedelta(days=30 * (i + 1)),
            principal_due=Decimal("13900.00"),
            interest_due=Decimal("2800.00"),
            total_due=Decimal("16700.00"),
            principal_paid=Decimal("13900.00") if i < 5 else Decimal("0.00"),
            interest_paid=Decimal("2800.00") if i < 5 else Decimal("0.00"),
            status="paid" if i < 5 else "pending",
        )
        db.add(schedule)

    # Schedule for second account (Home Loan)
    for i in range(3):
        schedule = RepaymentSchedule(
            loan_account_id=accounts[1].id,
            installment_number=i + 1,
            due_date=accounts[1].start_date + timedelta(days=30 * (i + 1)),
            principal_due=Decimal("10500.00"),
            interest_due=Decimal("32000.00"),
            total_due=Decimal("42500.00"),
            principal_paid=Decimal("10500.00") if i < 2 else Decimal("0.00"),
            interest_paid=Decimal("32000.00") if i < 2 else Decimal("0.00"),
            status="paid" if i < 2 else "pending",
        )
        db.add(schedule)

    # Schedule for third account (Business Loan - with overdue)
    for i in range(4):
        status = "paid" if i < 3 else "overdue"
        paid = i < 3
        schedule = RepaymentSchedule(
            loan_account_id=accounts[2].id,
            installment_number=i + 1,
            due_date=accounts[2].start_date + timedelta(days=30 * (i + 1)),
            principal_due=Decimal("23500.00"),
            interest_due=Decimal("17500.00"),
            total_due=Decimal("41000.00"),
            principal_paid=Decimal("23500.00") if paid else Decimal("0.00"),
            interest_paid=Decimal("17500.00") if paid else Decimal("0.00"),
            status=status,
        )
        db.add(schedule)

    db.flush()


def seed_loan_partners(db: Session) -> list[LoanPartner]:
    """Create sample loan partners for co-lending."""
    partners_data = [
        {
            "name": "State Bank of India",
            "partner_type": "lender",
            "external_code": "SBI001",
            "registration_type": "bank",
            "rbi_license_number": "BKID0001234",
            "default_share_percent": Decimal("80.0000"),
            "default_yield_rate": Decimal("7.5000"),
            "provides_fldg": False,
            "total_exposure_limit": Decimal("10000000000.00"),
            "current_exposure": Decimal("450000000.00"),
            "contact_email": "colending@sbi.co.in",
            "is_active": True,
        },
        {
            "name": "Bajaj Finance Limited",
            "partner_type": "originator",
            "external_code": "BAJFIN001",
            "registration_type": "nbfc",
            "rbi_license_number": "N-13.02567",
            "default_share_percent": Decimal("20.0000"),
            "provides_fldg": True,
            "default_fldg_percent": Decimal("5.0000"),
            "fldg_guarantee_form": "cash_deposit",
            "is_servicer": True,
            "default_servicer_fee_rate": Decimal("0.5000"),
            "total_exposure_limit": Decimal("5000000000.00"),
            "current_exposure": Decimal("120000000.00"),
            "contact_email": "partnerships@bajajfinserv.in",
            "is_active": True,
        },
        {
            "name": "HDFC Bank",
            "partner_type": "lender",
            "external_code": "HDFC001",
            "registration_type": "bank",
            "rbi_license_number": "BKID0001235",
            "default_share_percent": Decimal("80.0000"),
            "default_yield_rate": Decimal("7.8000"),
            "total_exposure_limit": Decimal("15000000000.00"),
            "current_exposure": Decimal("680000000.00"),
            "contact_email": "colending@hdfcbank.com",
            "is_active": True,
        },
    ]

    partners = []
    for data in partners_data:
        partner = LoanPartner(**data)
        db.add(partner)
        partners.append(partner)

    db.flush()
    return partners


def seed_loan_participations(db: Session, accounts: list[LoanAccount], partners: list[LoanPartner]) -> None:
    """Create co-lending participations."""
    # Co-lending participation for the home loan (80:20 split)
    participation_lender = LoanParticipation(
        loan_account_id=accounts[1].id,
        partner_id=partners[0].id,  # SBI as lender
        participation_type="co_lending",
        share_percent=Decimal("80.0000"),
        principal_disbursed=Decimal("3600000.00"),
        principal_outstanding=Decimal("3560000.00"),
        interest_rate=Decimal("7.5000"),
        fldg_covered=True,
        fldg_coverage_percent=Decimal("5.0000"),
        status="active",
        effective_date=date.today() - timedelta(days=90),
    )
    db.add(participation_lender)

    participation_originator = LoanParticipation(
        loan_account_id=accounts[1].id,
        partner_id=partners[1].id,  # Bajaj as originator
        participation_type="co_lending",
        share_percent=Decimal("20.0000"),
        principal_disbursed=Decimal("900000.00"),
        principal_outstanding=Decimal("890000.00"),
        interest_rate=Decimal("8.5000"),
        fee_share_percent=Decimal("100.0000"),
        excess_spread_rate=Decimal("1.0000"),
        status="active",
        effective_date=date.today() - timedelta(days=90),
    )
    db.add(participation_originator)

    db.flush()


def seed_investment_issuers(db: Session) -> list[InvestmentIssuer]:
    """Create sample investment issuers."""
    issuers_data = [
        {
            "issuer_code": "RELIND",
            "issuer_name": "Reliance Industries Limited",
            "issuer_type": "corporate",
            "cin": "L17110MH1973PLC019786",
            "industry_sector": "Conglomerate",
            "industry_sub_sector": "Energy & Retail",
            "long_term_rating": "AAA",
            "rating_agency": "CRISIL",
            "rating_outlook": "stable",
            "internal_limit": Decimal("50000000000.00"),
            "current_exposure": Decimal("2500000000.00"),
            "is_active": True,
        },
        {
            "issuer_code": "HDFCLTD",
            "issuer_name": "HDFC Limited",
            "issuer_type": "nbfc",
            "cin": "L70100MH1977PLC019916",
            "industry_sector": "Financial Services",
            "industry_sub_sector": "Housing Finance",
            "long_term_rating": "AAA",
            "rating_agency": "ICRA",
            "rating_outlook": "stable",
            "internal_limit": Decimal("75000000000.00"),
            "current_exposure": Decimal("5000000000.00"),
            "is_active": True,
        },
        {
            "issuer_code": "TATASTL",
            "issuer_name": "Tata Steel Limited",
            "issuer_type": "corporate",
            "cin": "L27100MH1907PLC000260",
            "industry_sector": "Manufacturing",
            "industry_sub_sector": "Steel",
            "long_term_rating": "AA",
            "rating_agency": "CARE",
            "rating_outlook": "positive",
            "internal_limit": Decimal("25000000000.00"),
            "current_exposure": Decimal("1500000000.00"),
            "is_active": True,
        },
        {
            "issuer_code": "GOI",
            "issuer_name": "Government of India",
            "issuer_type": "government",
            "long_term_rating": "SOV",
            "rating_agency": "N/A",
            "rating_outlook": "stable",
            "internal_limit": Decimal("100000000000.00"),
            "current_exposure": Decimal("15000000000.00"),
            "is_active": True,
        },
    ]

    issuers = []
    for data in issuers_data:
        issuer = InvestmentIssuer(**data)
        db.add(issuer)
        issuers.append(issuer)

    db.flush()
    return issuers


def seed_investment_products(db: Session) -> list[InvestmentProduct]:
    """Create sample investment product configurations."""
    products_data = [
        {
            "product_code": "NCD-CORP",
            "product_name": "Corporate NCD",
            "product_type": "ncd",
            "category": "fixed_income",
            "coupon_type": "fixed",
            "coupon_frequency": "quarterly",
            "day_count_convention": "ACT/365",
            "min_tenure_days": 365,
            "max_tenure_days": 3650,
            "min_investment_amount": Decimal("1000000.00"),
            "lot_size": Decimal("100000.00"),
            "tds_applicable": True,
            "tds_rate": Decimal("10.00"),
            "listed": True,
            "exchange": "NSE",
            "is_active": True,
        },
        {
            "product_code": "CP-PRIME",
            "product_name": "Commercial Paper - Prime",
            "product_type": "cp",
            "category": "money_market",
            "coupon_type": "zero_coupon",
            "coupon_frequency": "at_maturity",
            "day_count_convention": "ACT/365",
            "min_tenure_days": 7,
            "max_tenure_days": 365,
            "min_investment_amount": Decimal("500000.00"),
            "lot_size": Decimal("500000.00"),
            "tds_applicable": True,
            "tds_rate": Decimal("10.00"),
            "is_active": True,
        },
        {
            "product_code": "GSEC",
            "product_name": "Government Securities",
            "product_type": "gsec",
            "category": "government_securities",
            "coupon_type": "fixed",
            "coupon_frequency": "semi_annual",
            "day_count_convention": "ACT/ACT",
            "min_tenure_days": 365,
            "max_tenure_days": 14600,
            "min_investment_amount": Decimal("10000.00"),
            "lot_size": Decimal("10000.00"),
            "tds_applicable": False,
            "tax_free": True,
            "listed": True,
            "exchange": "NSE",
            "is_active": True,
        },
        {
            "product_code": "BOND-PSU",
            "product_name": "PSU Bond",
            "product_type": "psu_bond",
            "category": "fixed_income",
            "coupon_type": "fixed",
            "coupon_frequency": "annual",
            "day_count_convention": "30/360",
            "min_tenure_days": 365,
            "max_tenure_days": 7300,
            "min_investment_amount": Decimal("100000.00"),
            "lot_size": Decimal("100000.00"),
            "tds_applicable": True,
            "tds_rate": Decimal("10.00"),
            "listed": True,
            "is_active": True,
        },
    ]

    products = []
    for data in products_data:
        product = InvestmentProduct(**data)
        db.add(product)
        products.append(product)

    db.flush()
    return products


def seed_investments(db: Session, issuers: list[InvestmentIssuer], inv_products: list[InvestmentProduct]) -> list[Investment]:
    """Create sample investments."""
    today = date.today()

    investments_data = [
        {
            "investment_code": "INV2024001",
            "isin": "INE002A08015",
            "security_name": "Reliance Industries NCD Series A 9.25% 2027",
            "product_id": inv_products[0].id,  # NCD
            "issuer_id": issuers[0].id,  # Reliance
            "instrument_type": "ncd",
            "series": "Series A",
            "face_value_per_unit": Decimal("100000.00"),
            "units_held": Decimal("50.0000"),
            "total_face_value": Decimal("5000000.00"),
            "purchase_date": today - timedelta(days=90),
            "purchase_price_per_unit": Decimal("99500.0000"),
            "purchase_yield": Decimal("9.3500"),
            "total_purchase_cost": Decimal("4975000.00"),
            "purchase_premium_discount": Decimal("-25000.00"),
            "acquisition_type": "primary",
            "coupon_rate": Decimal("9.2500"),
            "coupon_type": "fixed",
            "coupon_frequency": "quarterly",
            "next_coupon_date": today + timedelta(days=90),
            "issue_date": today - timedelta(days=90),
            "maturity_date": today + timedelta(days=1005),
            "original_tenure_days": 1095,
            "remaining_tenure_days": 1005,
            "amortized_cost": Decimal("4977000.00"),
            "accrued_interest": Decimal("115625.00"),
            "classification": "HTM",
            "rating_at_investment": "AAA",
            "current_rating": "AAA",
            "status": "active",
            "original_units": Decimal("50.0000"),
        },
        {
            "investment_code": "INV2024002",
            "isin": "INE001A08110",
            "security_name": "HDFC Ltd NCD 8.75% 2026",
            "product_id": inv_products[0].id,  # NCD
            "issuer_id": issuers[1].id,  # HDFC
            "instrument_type": "ncd",
            "series": "2026-A",
            "face_value_per_unit": Decimal("100000.00"),
            "units_held": Decimal("100.0000"),
            "total_face_value": Decimal("10000000.00"),
            "purchase_date": today - timedelta(days=180),
            "purchase_price_per_unit": Decimal("101200.0000"),
            "purchase_yield": Decimal("8.5000"),
            "total_purchase_cost": Decimal("10120000.00"),
            "purchase_premium_discount": Decimal("120000.00"),
            "acquisition_type": "secondary",
            "coupon_rate": Decimal("8.7500"),
            "coupon_type": "fixed",
            "coupon_frequency": "quarterly",
            "next_coupon_date": today + timedelta(days=45),
            "issue_date": today - timedelta(days=365),
            "maturity_date": today + timedelta(days=545),
            "original_tenure_days": 910,
            "remaining_tenure_days": 545,
            "amortized_cost": Decimal("10080000.00"),
            "accrued_interest": Decimal("437500.00"),
            "classification": "AFS",
            "current_market_price": Decimal("100800.0000"),
            "current_market_value": Decimal("10080000.00"),
            "rating_at_investment": "AAA",
            "current_rating": "AAA",
            "status": "active",
            "original_units": Decimal("100.0000"),
        },
        {
            "investment_code": "INV2024003",
            "isin": "IN0020240001",
            "security_name": "GOI 7.26% 2033",
            "product_id": inv_products[2].id,  # G-Sec
            "issuer_id": issuers[3].id,  # GOI
            "instrument_type": "gsec",
            "face_value_per_unit": Decimal("100.00"),
            "units_held": Decimal("1000000.0000"),
            "total_face_value": Decimal("100000000.00"),
            "purchase_date": today - timedelta(days=60),
            "purchase_price_per_unit": Decimal("98.5000"),
            "purchase_yield": Decimal("7.4500"),
            "total_purchase_cost": Decimal("98500000.00"),
            "purchase_premium_discount": Decimal("-1500000.00"),
            "acquisition_type": "primary",
            "coupon_rate": Decimal("7.2600"),
            "coupon_type": "fixed",
            "coupon_frequency": "semi_annual",
            "next_coupon_date": today + timedelta(days=120),
            "issue_date": today - timedelta(days=60),
            "maturity_date": today + timedelta(days=3225),
            "original_tenure_days": 3285,
            "remaining_tenure_days": 3225,
            "amortized_cost": Decimal("98550000.00"),
            "accrued_interest": Decimal("1193424.66"),
            "classification": "HTM",
            "rating_at_investment": "SOV",
            "current_rating": "SOV",
            "status": "active",
            "original_units": Decimal("1000000.0000"),
        },
        {
            "investment_code": "INV2024004",
            "security_name": "Tata Steel CP Mar 2025",
            "product_id": inv_products[1].id,  # CP
            "issuer_id": issuers[2].id,  # Tata Steel
            "instrument_type": "cp",
            "face_value_per_unit": Decimal("500000.00"),
            "units_held": Decimal("20.0000"),
            "total_face_value": Decimal("10000000.00"),
            "purchase_date": today - timedelta(days=30),
            "purchase_price_per_unit": Decimal("485000.0000"),
            "purchase_yield": Decimal("8.2500"),
            "total_purchase_cost": Decimal("9700000.00"),
            "purchase_premium_discount": Decimal("-300000.00"),
            "acquisition_type": "primary",
            "coupon_rate": Decimal("0.0000"),
            "coupon_type": "zero_coupon",
            "coupon_frequency": "none",
            "issue_date": today - timedelta(days=30),
            "maturity_date": today + timedelta(days=60),
            "original_tenure_days": 90,
            "remaining_tenure_days": 60,
            "amortized_cost": Decimal("9800000.00"),
            "accrued_interest": Decimal("0.00"),
            "classification": "HFT",
            "rating_at_investment": "AA",
            "current_rating": "AA",
            "status": "active",
            "original_units": Decimal("20.0000"),
        },
    ]

    investments = []
    for data in investments_data:
        investment = Investment(**data)
        db.add(investment)
        investments.append(investment)

    db.flush()
    return investments


def seed_selldown_buyers(db: Session) -> list[SelldownBuyer]:
    """Create sample selldown buyers."""
    buyers_data = [
        {
            "buyer_code": "ICICIBANK",
            "buyer_name": "ICICI Bank Limited",
            "buyer_type": "bank",
            "registration_number": "L65190GJ1994PLC021012",
            "regulatory_category": "scheduled_bank",
            "contact_person": "Treasury Department",
            "contact_email": "treasury@icicibank.com",
            "total_exposure_limit": Decimal("50000000000.00"),
            "current_exposure": Decimal("8500000000.00"),
            "min_ticket_size": Decimal("10000000.00"),
            "is_active": True,
            "onboarded_date": date(2023, 1, 15),
        },
        {
            "buyer_code": "ABORIG",
            "buyer_name": "Aditya Birla Sun Life AMC",
            "buyer_type": "mutual_fund",
            "registration_number": "MF123456",
            "regulatory_category": "mutual_fund",
            "contact_person": "Fixed Income Team",
            "contact_email": "fixedincome@adityabirlacapital.com",
            "total_exposure_limit": Decimal("25000000000.00"),
            "current_exposure": Decimal("3200000000.00"),
            "min_ticket_size": Decimal("5000000.00"),
            "preferred_rating": "AA",
            "is_active": True,
            "onboarded_date": date(2023, 6, 1),
        },
        {
            "buyer_code": "KOTAK_AIF",
            "buyer_name": "Kotak Special Situations Fund",
            "buyer_type": "aif",
            "registration_number": "IN/AIF2/14-15/0123",
            "regulatory_category": "aif_cat2",
            "contact_person": "Investment Team",
            "contact_email": "aif@kotak.com",
            "total_exposure_limit": Decimal("5000000000.00"),
            "current_exposure": Decimal("850000000.00"),
            "min_ticket_size": Decimal("25000000.00"),
            "is_active": True,
            "onboarded_date": date(2024, 1, 10),
        },
    ]

    buyers = []
    for data in buyers_data:
        buyer = SelldownBuyer(**data)
        db.add(buyer)
        buyers.append(buyer)

    db.flush()
    return buyers


def seed_additional_borrowers(db: Session) -> list[Borrower]:
    """Create additional borrowers for LAP and delinquent scenarios."""
    borrowers_data = [
        {
            "external_id": "BRW006",
            "first_name": "Meera",
            "last_name": "Reddy",
            "date_of_birth": date(1988, 9, 14),
            "email": "meera.reddy@email.com",
            "phone": "+91-9876543215",
            "kyc_status": "verified",
        },
        {
            "external_id": "BRW007",
            "first_name": "Arjun",
            "last_name": "Nair",
            "date_of_birth": date(1975, 12, 3),
            "email": "arjun.nair@email.com",
            "phone": "+91-9876543216",
            "kyc_status": "verified",
        },
        {
            "external_id": "BRW008",
            "first_name": "Kavita",
            "last_name": "Deshmukh",
            "date_of_birth": date(1992, 4, 18),
            "email": "kavita.deshmukh@email.com",
            "phone": "+91-9876543217",
            "kyc_status": "verified",
        },
        {
            "external_id": "BRW009",
            "first_name": "Suresh",
            "last_name": "Iyer",
            "date_of_birth": date(1980, 6, 25),
            "email": "suresh.iyer@email.com",
            "phone": "+91-9876543218",
            "kyc_status": "verified",
        },
        {
            "external_id": "BRW010",
            "first_name": "Anita",
            "last_name": "Joshi",
            "date_of_birth": date(1987, 2, 10),
            "email": "anita.joshi@email.com",
            "phone": "+91-9876543219",
            "kyc_status": "pending",
        },
    ]

    borrowers = []
    for data in borrowers_data:
        borrower = Borrower(**data)
        db.add(borrower)
        borrowers.append(borrower)

    db.flush()
    return borrowers


def seed_lap_product(db: Session) -> LoanProduct:
    """Create LAP (Loan Against Property) product."""
    product = LoanProduct(
        code="LAP-001",
        name="Loan Against Property - Standard",
        currency="INR",
        interest_rate_type="floating",
        base_rate=Decimal("9.7500"),
        schedule_type="emi",
        repayment_frequency="monthly",
        day_count_convention="act/365",
        processing_fee_rate=Decimal("1.0000"),
        penalty_rate=Decimal("2.0000"),
        prepayment_penalty_rate=Decimal("3.0000"),
        grace_days=7,
        min_tenure_months=36,
        max_tenure_months=180,
    )
    db.add(product)
    db.flush()
    return product


def seed_lap_applications(
    db: Session, borrowers: list[Borrower], lap_product: LoanProduct
) -> list[LoanApplication]:
    """Create LAP loan applications in various workflow stages."""
    today = date.today()
    applications_data = [
        {
            "borrower_id": borrowers[0].id,
            "product_id": lap_product.id,
            "status": "disbursed",
            "channel": "branch",
            "requested_amount": Decimal("3500000.00"),
            "requested_tenure_months": 120,
            "credit_score": 760,
            "approved_amount": Decimal("3000000.00"),
            "approved_rate": Decimal("9.7500"),
            "approved_tenure_months": 120,
            "decision_reason": "Property valuation approved, good credit history",
            "branch_id": "BR001",
            "branch_name": "Mumbai Andheri West",
            "decision_at": datetime.now() - timedelta(days=200),
        },
        {
            "borrower_id": borrowers[1].id,
            "product_id": lap_product.id,
            "status": "under_review",
            "channel": "branch",
            "requested_amount": Decimal("8000000.00"),
            "requested_tenure_months": 180,
            "credit_score": 710,
            "branch_id": "BR002",
            "branch_name": "Delhi Connaught Place",
        },
        {
            "borrower_id": borrowers[2].id,
            "product_id": lap_product.id,
            "status": "disbursed",
            "channel": "branch",
            "requested_amount": Decimal("2000000.00"),
            "requested_tenure_months": 60,
            "credit_score": 680,
            "approved_amount": Decimal("1500000.00"),
            "approved_rate": Decimal("10.2500"),
            "approved_tenure_months": 60,
            "decision_reason": "Property approved with lower LTV",
            "branch_id": "BR003",
            "branch_name": "Pune Koregaon Park",
            "decision_at": datetime.now() - timedelta(days=300),
        },
        {
            "borrower_id": borrowers[3].id,
            "product_id": lap_product.id,
            "status": "disbursed",
            "channel": "branch",
            "requested_amount": Decimal("5000000.00"),
            "requested_tenure_months": 120,
            "credit_score": 690,
            "approved_amount": Decimal("4000000.00"),
            "approved_rate": Decimal("10.0000"),
            "approved_tenure_months": 120,
            "decision_reason": "Commercial property, adequate collateral",
            "branch_id": "BR004",
            "branch_name": "Chennai T. Nagar",
            "decision_at": datetime.now() - timedelta(days=400),
        },
    ]

    applications = []
    for data in applications_data:
        application = LoanApplication(**data)
        db.add(application)
        applications.append(application)

    db.flush()
    return applications


def seed_lap_accounts(
    db: Session, applications: list[LoanApplication]
) -> list[LoanAccount]:
    """Create LAP loan accounts including delinquent ones."""
    today = date.today()

    accounts_data = [
        {
            # Current LAP account - no DPD
            "application_id": applications[0].id,
            "account_number": "LAP2024000001",
            "principal_amount": Decimal("3000000.00"),
            "principal_outstanding": Decimal("2850000.00"),
            "interest_outstanding": Decimal("23200.00"),
            "fees_outstanding": Decimal("0.00"),
            "interest_rate": Decimal("9.7500"),
            "interest_rate_type": "floating",
            "schedule_type": "emi",
            "tenure_months": 120,
            "start_date": today - timedelta(days=200),
            "disbursed_at": datetime.now() - timedelta(days=200),
            "next_due_date": today + timedelta(days=10),
            "next_due_amount": Decimal("39500.00"),
            "dpd": 0,
            "status": "active",
            "ecl_stage": 1,
        },
        {
            # SMA-1 LAP account - 45 DPD
            "application_id": applications[2].id,
            "account_number": "LAP2024000002",
            "principal_amount": Decimal("1500000.00"),
            "principal_outstanding": Decimal("1280000.00"),
            "interest_outstanding": Decimal("32000.00"),
            "fees_outstanding": Decimal("3500.00"),
            "interest_rate": Decimal("10.2500"),
            "interest_rate_type": "floating",
            "schedule_type": "emi",
            "tenure_months": 60,
            "start_date": today - timedelta(days=300),
            "disbursed_at": datetime.now() - timedelta(days=300),
            "next_due_date": today - timedelta(days=45),
            "next_due_amount": Decimal("32500.00"),
            "dpd": 45,
            "status": "active",
            "ecl_stage": 2,
        },
        {
            # NPA LAP account - 95 DPD
            "application_id": applications[3].id,
            "account_number": "LAP2024000003",
            "principal_amount": Decimal("4000000.00"),
            "principal_outstanding": Decimal("3700000.00"),
            "interest_outstanding": Decimal("98000.00"),
            "fees_outstanding": Decimal("12000.00"),
            "interest_rate": Decimal("10.0000"),
            "interest_rate_type": "floating",
            "schedule_type": "emi",
            "tenure_months": 120,
            "start_date": today - timedelta(days=400),
            "disbursed_at": datetime.now() - timedelta(days=400),
            "next_due_date": today - timedelta(days=95),
            "next_due_amount": Decimal("52800.00"),
            "dpd": 95,
            "status": "npa",
            "is_npa": True,
            "npa_date": today - timedelta(days=5),
            "npa_category": "substandard",
            "ecl_stage": 3,
        },
    ]

    accounts = []
    for data in accounts_data:
        account = LoanAccount(**data)
        db.add(account)
        accounts.append(account)

    db.flush()
    return accounts


def seed_collaterals(
    db: Session,
    lap_applications: list[LoanApplication],
    lap_accounts: list[LoanAccount],
) -> list[Collateral]:
    """Create collateral records with valuations, insurance, and legal verifications."""
    today = date.today()

    collaterals_data = [
        {
            "application_id": lap_applications[0].id,
            "loan_account_id": lap_accounts[0].id,
            "property_type": "residential",
            "property_sub_type": "flat",
            "address_line1": "B-402, Harmony Heights",
            "address_line2": "Lokhandwala Complex",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400053",
            "district": "Mumbai Suburban",
            "area_sqft": 1200.0,
            "carpet_area_sqft": 950.0,
            "built_up_area_sqft": 1100.0,
            "owner_name": "Meera Reddy",
            "ownership_type": "freehold",
            "title_deed_number": "TD-MUM-2018-45678",
            "registration_number": "REG-MH-2018-098765",
            "registration_date": date(2018, 6, 15),
            "survey_number": "CTS-456/A",
            "market_value": 7500000.0,
            "distress_value": 5500000.0,
            "realizable_value": 6500000.0,
            "ltv_ratio": 0.38,
            "valuation_date": today - timedelta(days=210),
            "valuer_name": "ABC Property Valuers",
            "legal_status": "clear",
            "encumbrance_status": "clear",
            "insurance_policy_number": "HDFCERGO-PROP-2024-001",
            "insurance_expiry_date": today + timedelta(days=155),
            "insured_value": 7000000.0,
            "charge_type": "first_charge",
            "charge_creation_date": today - timedelta(days=200),
            "charge_id": "ROC-MH-2024-001234",
            "status": "approved",
            "is_primary_security": True,
        },
        {
            "application_id": lap_applications[1].id,
            "property_type": "commercial",
            "property_sub_type": "office",
            "address_line1": "Unit 1205, DLF Cyber City",
            "address_line2": "Phase III",
            "city": "Gurgaon",
            "state": "Haryana",
            "pincode": "122002",
            "district": "Gurgaon",
            "area_sqft": 2500.0,
            "carpet_area_sqft": 2100.0,
            "built_up_area_sqft": 2300.0,
            "owner_name": "Arjun Nair",
            "co_owner_name": "Nair Enterprises Pvt Ltd",
            "ownership_type": "leasehold",
            "title_deed_number": "TD-HR-2020-11223",
            "registration_number": "REG-HR-2020-334455",
            "registration_date": date(2020, 3, 10),
            "market_value": 18000000.0,
            "realizable_value": 15000000.0,
            "distress_value": 12000000.0,
            "valuation_date": today - timedelta(days=30),
            "valuer_name": "Knight Frank India",
            "legal_status": "pending",
            "encumbrance_status": "clear",
            "status": "pending",
            "is_primary_security": True,
        },
        {
            "application_id": lap_applications[2].id,
            "loan_account_id": lap_accounts[1].id,
            "property_type": "residential",
            "property_sub_type": "bungalow",
            "address_line1": "Plot 15, Aundh Road",
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411007",
            "district": "Pune",
            "area_sqft": 3000.0,
            "land_area_acres": 0.07,
            "owner_name": "Kavita Deshmukh",
            "ownership_type": "freehold",
            "title_deed_number": "TD-MH-2015-99887",
            "registration_number": "REG-MH-2015-776655",
            "registration_date": date(2015, 11, 20),
            "survey_number": "SV-789/B",
            "market_value": 4500000.0,
            "distress_value": 3200000.0,
            "realizable_value": 3800000.0,
            "ltv_ratio": 0.2844,
            "valuation_date": today - timedelta(days=310),
            "valuer_name": "XYZ Valuers Pune",
            "legal_status": "clear",
            "encumbrance_status": "clear",
            "insurance_policy_number": "ICICI-PROP-2024-005",
            "insurance_expiry_date": today + timedelta(days=60),
            "insured_value": 4000000.0,
            "charge_type": "first_charge",
            "charge_creation_date": today - timedelta(days=300),
            "charge_id": "ROC-MH-2024-005678",
            "status": "approved",
            "is_primary_security": True,
        },
        {
            "application_id": lap_applications[3].id,
            "loan_account_id": lap_accounts[2].id,
            "property_type": "commercial",
            "property_sub_type": "shop",
            "address_line1": "Shop G-12, Spencer Plaza",
            "address_line2": "Anna Salai",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "pincode": "600002",
            "district": "Chennai",
            "area_sqft": 800.0,
            "carpet_area_sqft": 700.0,
            "owner_name": "Suresh Iyer",
            "ownership_type": "freehold",
            "title_deed_number": "TD-TN-2016-33221",
            "registration_number": "REG-TN-2016-998877",
            "registration_date": date(2016, 8, 5),
            "market_value": 8000000.0,
            "distress_value": 5500000.0,
            "realizable_value": 6500000.0,
            "ltv_ratio": 0.4625,
            "valuation_date": today - timedelta(days=410),
            "valuer_name": "Colliers India",
            "legal_status": "issue_found",
            "encumbrance_status": "encumbered",
            "charge_type": "first_charge",
            "charge_creation_date": today - timedelta(days=400),
            "charge_id": "ROC-TN-2024-009876",
            "status": "approved",
            "is_primary_security": True,
        },
    ]

    collaterals = []
    for data in collaterals_data:
        c = Collateral(**data)
        db.add(c)
        collaterals.append(c)

    db.flush()
    return collaterals


def seed_collateral_sub_records(db: Session, collaterals: list[Collateral]) -> None:
    """Create valuations, insurance, and legal verifications for collaterals."""
    today = date.today()

    # Valuations for collateral 0 (Mumbai flat)
    for i, (vtype, days_ago, mv) in enumerate([
        ("initial", 220, 7200000.0),
        ("periodic", 210, 7500000.0),
    ]):
        db.add(CollateralValuation(
            collateral_id=collaterals[0].id,
            valuation_date=today - timedelta(days=days_ago),
            valuer_name="ABC Property Valuers",
            valuer_agency="ABC Valuers Pvt Ltd",
            valuation_type=vtype,
            market_value=mv,
            realizable_value=mv * 0.85,
            distress_value=mv * 0.72,
            forced_sale_value=mv * 0.65,
            report_reference=f"RPT-MUM-2024-{i+1:03d}",
        ))

    # Valuation for collateral 1 (Gurgaon office)
    db.add(CollateralValuation(
        collateral_id=collaterals[1].id,
        valuation_date=today - timedelta(days=30),
        valuer_name="Knight Frank India",
        valuer_agency="Knight Frank (India) Pvt Ltd",
        valuation_type="initial",
        market_value=18000000.0,
        realizable_value=15000000.0,
        distress_value=12000000.0,
        forced_sale_value=10000000.0,
        report_reference="RPT-GGN-2025-001",
    ))

    # Insurance for collateral 0
    db.add(CollateralInsurance(
        collateral_id=collaterals[0].id,
        policy_number="HDFCERGO-PROP-2024-001",
        provider="HDFC ERGO General Insurance",
        insured_value=7000000.0,
        premium_amount=18500.0,
        start_date=today - timedelta(days=210),
        expiry_date=today + timedelta(days=155),
        status="active",
        is_assigned_to_lender=True,
    ))

    # Insurance for collateral 2
    db.add(CollateralInsurance(
        collateral_id=collaterals[2].id,
        policy_number="ICICI-PROP-2024-005",
        provider="ICICI Lombard",
        insured_value=4000000.0,
        premium_amount=12000.0,
        start_date=today - timedelta(days=300),
        expiry_date=today + timedelta(days=60),
        status="active",
        is_assigned_to_lender=True,
    ))

    # Legal verifications for collateral 0 (all clear)
    for vtype in ["title_search", "encumbrance_check", "cersai_search"]:
        db.add(CollateralLegalVerification(
            collateral_id=collaterals[0].id,
            verification_type=vtype,
            verification_date=today - timedelta(days=215),
            verified_by="Sharma & Associates Legal",
            verification_status="clear",
            report_reference=f"LGL-MUM-{vtype[:3].upper()}-001",
        ))

    # Legal verifications for collateral 1 (pending)
    db.add(CollateralLegalVerification(
        collateral_id=collaterals[1].id,
        verification_type="title_search",
        verification_date=today - timedelta(days=25),
        verified_by="Rajiv Legal Consultants",
        verification_status="clear",
        report_reference="LGL-GGN-TIT-001",
    ))
    db.add(CollateralLegalVerification(
        collateral_id=collaterals[1].id,
        verification_type="encumbrance_check",
        verification_date=today - timedelta(days=20),
        verified_by="Rajiv Legal Consultants",
        verification_status="pending",
        report_reference="LGL-GGN-ENC-001",
    ))

    # Legal verifications for collateral 3 (issue found)
    db.add(CollateralLegalVerification(
        collateral_id=collaterals[3].id,
        verification_type="title_search",
        verification_date=today - timedelta(days=410),
        verified_by="Chennai Legal Services",
        verification_status="clear",
    ))
    db.add(CollateralLegalVerification(
        collateral_id=collaterals[3].id,
        verification_type="encumbrance_check",
        verification_date=today - timedelta(days=405),
        verified_by="Chennai Legal Services",
        verification_status="issue_found",
        findings="Existing second charge by NBFC identified. Partial encumbrance.",
    ))

    db.flush()


def seed_documents(
    db: Session,
    lap_applications: list[LoanApplication],
    collaterals: list[Collateral],
    borrowers: list[Borrower],
) -> None:
    """Create document records with media types and geo-tags."""
    today = date.today()

    docs_data = [
        # KYC docs for borrower
        {
            "borrower_id": borrowers[0].id,
            "application_id": lap_applications[0].id,
            "document_type": "aadhaar_card",
            "file_name": "aadhaar_meera_reddy.pdf",
            "storage_path": "/docs/kyc/aadhaar_meera_reddy.pdf",
            "status": "verified",
            "media_type": "document",
            "section": "due_diligence",
            "mime_type": "application/pdf",
            "file_size_bytes": 245000,
        },
        {
            "borrower_id": borrowers[0].id,
            "application_id": lap_applications[0].id,
            "document_type": "pan_card",
            "file_name": "pan_meera_reddy.pdf",
            "storage_path": "/docs/kyc/pan_meera_reddy.pdf",
            "status": "verified",
            "media_type": "document",
            "section": "due_diligence",
            "mime_type": "application/pdf",
            "file_size_bytes": 180000,
        },
        # Collateral exterior photos
        {
            "application_id": lap_applications[0].id,
            "collateral_id": collaterals[0].id,
            "document_type": "property_photo",
            "file_name": "harmony_heights_exterior_01.jpg",
            "storage_path": "/docs/collateral/harmony_exterior_01.jpg",
            "status": "uploaded",
            "media_type": "photo",
            "section": "collateral_exterior",
            "mime_type": "image/jpeg",
            "file_size_bytes": 3500000,
            "capture_latitude": 19.1364,
            "capture_longitude": 72.8296,
            "captured_at": datetime.now() - timedelta(days=215),
            "captured_by": "Site Visit Team A",
            "description": "Front elevation of Harmony Heights building B",
        },
        {
            "application_id": lap_applications[0].id,
            "collateral_id": collaterals[0].id,
            "document_type": "property_photo",
            "file_name": "harmony_heights_interior_01.jpg",
            "storage_path": "/docs/collateral/harmony_interior_01.jpg",
            "status": "uploaded",
            "media_type": "photo",
            "section": "collateral_interior",
            "mime_type": "image/jpeg",
            "file_size_bytes": 2800000,
            "capture_latitude": 19.1364,
            "capture_longitude": 72.8296,
            "captured_at": datetime.now() - timedelta(days=215),
            "captured_by": "Site Visit Team A",
            "description": "Living room of flat B-402",
        },
        # Site visit video
        {
            "application_id": lap_applications[0].id,
            "collateral_id": collaterals[0].id,
            "document_type": "site_visit_video",
            "file_name": "harmony_heights_sitevisit.mp4",
            "storage_path": "/docs/collateral/harmony_sitevisit.mp4",
            "status": "uploaded",
            "media_type": "video",
            "section": "site_visit",
            "mime_type": "video/mp4",
            "file_size_bytes": 45000000,
            "capture_latitude": 19.1364,
            "capture_longitude": 72.8296,
            "captured_at": datetime.now() - timedelta(days=215),
            "captured_by": "Site Visit Team A",
            "description": "Complete site visit walkthrough video",
        },
        # Title deed document
        {
            "application_id": lap_applications[0].id,
            "collateral_id": collaterals[0].id,
            "document_type": "title_deed",
            "file_name": "title_deed_harmony_b402.pdf",
            "storage_path": "/docs/legal/title_deed_harmony_b402.pdf",
            "status": "verified",
            "media_type": "document",
            "section": "title_deed",
            "mime_type": "application/pdf",
            "file_size_bytes": 520000,
        },
        # Valuation report
        {
            "application_id": lap_applications[0].id,
            "collateral_id": collaterals[0].id,
            "document_type": "valuation_report",
            "file_name": "valuation_report_harmony_b402.pdf",
            "storage_path": "/docs/valuation/valuation_harmony_b402.pdf",
            "status": "verified",
            "media_type": "document",
            "section": "valuation_report",
            "mime_type": "application/pdf",
            "file_size_bytes": 890000,
        },
        # Gurgaon office photos
        {
            "application_id": lap_applications[1].id,
            "collateral_id": collaterals[1].id,
            "document_type": "property_photo",
            "file_name": "dlf_cyber_exterior.jpg",
            "storage_path": "/docs/collateral/dlf_cyber_exterior.jpg",
            "status": "uploaded",
            "media_type": "photo",
            "section": "collateral_exterior",
            "mime_type": "image/jpeg",
            "file_size_bytes": 4200000,
            "capture_latitude": 28.4945,
            "capture_longitude": 77.0892,
            "captured_at": datetime.now() - timedelta(days=28),
            "captured_by": "Site Visit Team B",
            "description": "DLF Cyber City Phase III building exterior",
        },
    ]

    for data in docs_data:
        db.add(Document(**data))

    db.flush()


def seed_payments(db: Session, accounts: list[LoanAccount]) -> None:
    """Create payment records for existing accounts."""
    today = date.today()

    # Payments for first account (current)
    for i in range(5):
        payment = Payment(
            loan_account_id=accounts[0].id,
            amount=Decimal("16700.00"),
            unallocated_amount=Decimal("0.00"),
            currency="INR",
            channel="nach",
            reference=f"NACH-{accounts[0].account_number}-{i+1:03d}",
            paid_at=datetime(
                (today - timedelta(days=180 - 30 * i)).year,
                (today - timedelta(days=180 - 30 * i)).month,
                (today - timedelta(days=180 - 30 * i)).day,
                10, 0, 0,
            ),
        )
        db.add(payment)

    # Payments for home loan account (2 payments made)
    for i in range(2):
        payment = Payment(
            loan_account_id=accounts[1].id,
            amount=Decimal("42500.00"),
            unallocated_amount=Decimal("0.00"),
            currency="INR",
            channel="nach",
            reference=f"NACH-{accounts[1].account_number}-{i+1:03d}",
            paid_at=datetime(
                (today - timedelta(days=90 - 30 * i)).year,
                (today - timedelta(days=90 - 30 * i)).month,
                (today - timedelta(days=90 - 30 * i)).day,
                10, 0, 0,
            ),
        )
        db.add(payment)

    db.flush()


def seed_delinquency_snapshots(db: Session, lap_accounts: list[LoanAccount]) -> None:
    """Create delinquency snapshots for LAP accounts."""
    today = date.today()

    # Snapshot for SMA-1 account (45 DPD)
    db.add(DelinquencySnapshot(
        loan_account_id=lap_accounts[1].id,
        snapshot_date=today,
        dpd=45,
        bucket="31-60",
        overdue_principal=Decimal("23000.00"),
        overdue_interest=Decimal("32000.00"),
        overdue_fees=Decimal("3500.00"),
        total_overdue=Decimal("58500.00"),
        principal_outstanding=Decimal("1280000.00"),
        missed_installments=2,
        oldest_due_date=today - timedelta(days=45),
    ))

    # Snapshot for NPA account (95 DPD)
    db.add(DelinquencySnapshot(
        loan_account_id=lap_accounts[2].id,
        snapshot_date=today,
        dpd=95,
        bucket="90+",
        overdue_principal=Decimal("78000.00"),
        overdue_interest=Decimal("98000.00"),
        overdue_fees=Decimal("12000.00"),
        total_overdue=Decimal("188000.00"),
        principal_outstanding=Decimal("3700000.00"),
        missed_installments=3,
        oldest_due_date=today - timedelta(days=95),
    ))

    db.flush()


def seed_collection_cases(db: Session, lap_accounts: list[LoanAccount]) -> None:
    """Create collection cases, actions, and PTPs."""
    today = date.today()

    # Case for SMA-1 account
    case1 = CollectionCase(
        loan_account_id=lap_accounts[1].id,
        case_number="COL-000001",
        status="in_progress",
        priority="medium",
        assigned_to="collector_ramesh",
        assigned_queue="sma_queue",
        opened_date=today - timedelta(days=15),
        last_action_date=today - timedelta(days=2),
        next_action_date=today + timedelta(days=5),
        dpd_at_open=30,
        overdue_at_open=35500.0,
        notes="SMA-1 account, customer facing temporary cash flow issues",
    )
    db.add(case1)
    db.flush()

    # Actions for case 1
    db.add(CollectionAction(
        case_id=case1.id,
        action_type="call",
        action_date=datetime.now() - timedelta(days=14),
        performed_by="collector_ramesh",
        outcome="contacted",
        outcome_details="Customer acknowledged overdue, promised to pay within a week",
        next_action_date=today - timedelta(days=7),
        next_action_type="call",
        notes="Customer was cooperative, family medical emergency caused delay",
    ))
    db.add(CollectionAction(
        case_id=case1.id,
        action_type="call",
        action_date=datetime.now() - timedelta(days=7),
        performed_by="collector_ramesh",
        outcome="promise_to_pay",
        outcome_details="Customer promised partial payment by month-end",
        next_action_date=today + timedelta(days=5),
        next_action_type="call",
    ))
    db.add(CollectionAction(
        case_id=case1.id,
        action_type="sms",
        action_date=datetime.now() - timedelta(days=2),
        performed_by="system",
        outcome="sent",
        outcome_details="Payment reminder SMS sent",
    ))

    # PTP for case 1
    db.add(PromiseToPay(
        case_id=case1.id,
        promise_date=today - timedelta(days=7),
        payment_due_date=today + timedelta(days=3),
        promised_amount=20000.0,
        status="pending",
        notes="Partial payment promised, balance next month",
    ))

    # Case for NPA account
    case2 = CollectionCase(
        loan_account_id=lap_accounts[2].id,
        case_number="COL-000002",
        status="in_progress",
        priority="high",
        assigned_to="collector_sunita",
        assigned_queue="npa_queue",
        opened_date=today - timedelta(days=30),
        last_action_date=today - timedelta(days=1),
        next_action_date=today + timedelta(days=7),
        dpd_at_open=65,
        overdue_at_open=110000.0,
        notes="NPA account, commercial property. Legal notice stage.",
    )
    db.add(case2)
    db.flush()

    # Actions for case 2
    db.add(CollectionAction(
        case_id=case2.id,
        action_type="call",
        action_date=datetime.now() - timedelta(days=28),
        performed_by="collector_sunita",
        outcome="no_answer",
        notes="Multiple call attempts, no response",
    ))
    db.add(CollectionAction(
        case_id=case2.id,
        action_type="visit",
        action_date=datetime.now() - timedelta(days=20),
        performed_by="collector_sunita",
        outcome="contacted",
        outcome_details="Met borrower at property. Business slowdown cited as reason.",
        notes="Borrower requested 3-month moratorium",
    ))
    db.add(CollectionAction(
        case_id=case2.id,
        action_type="letter",
        action_date=datetime.now() - timedelta(days=10),
        performed_by="legal_team",
        outcome="sent",
        outcome_details="Demand notice sent via registered post",
    ))
    db.add(CollectionAction(
        case_id=case2.id,
        action_type="legal_notice",
        action_date=datetime.now() - timedelta(days=1),
        performed_by="legal_team",
        outcome="sent",
        outcome_details="SARFAESI Section 13(2) notice issued",
        next_action_date=today + timedelta(days=7),
        next_action_type="call",
    ))

    # Broken PTP for case 2
    db.add(PromiseToPay(
        case_id=case2.id,
        promise_date=today - timedelta(days=20),
        payment_due_date=today - timedelta(days=10),
        promised_amount=50000.0,
        status="broken",
        notes="Customer failed to honor promise",
    ))

    db.flush()


def seed_escalation_rules(db: Session) -> None:
    """Create escalation rules for collection management."""
    rules_data = [
        {
            "name": "SMA-0 SMS Reminder",
            "trigger_dpd": 1,
            "trigger_bucket": "SMA-0",
            "action_type": "send_sms",
            "action_config": '{"template": "payment_reminder", "channel": "sms"}',
            "priority": 10,
            "is_active": True,
        },
        {
            "name": "SMA-1 Call Assignment",
            "trigger_dpd": 31,
            "trigger_bucket": "SMA-1",
            "action_type": "assign_queue",
            "action_config": '{"queue": "sma_queue", "priority": "medium"}',
            "priority": 20,
            "is_active": True,
        },
        {
            "name": "SMA-2 Manager Escalation",
            "trigger_dpd": 61,
            "trigger_bucket": "SMA-2",
            "action_type": "assign_queue",
            "action_config": '{"queue": "escalation_queue", "priority": "high"}',
            "priority": 30,
            "is_active": True,
        },
        {
            "name": "NPA Legal Action",
            "trigger_dpd": 90,
            "action_type": "legal_notice",
            "action_config": '{"notice_type": "sarfaesi_13_2", "queue": "npa_queue"}',
            "priority": 40,
            "is_active": True,
        },
        {
            "name": "High Amount Alert",
            "trigger_amount": 100000.0,
            "action_type": "send_email",
            "action_config": '{"template": "high_amount_alert", "notify": "branch_manager"}',
            "priority": 50,
            "is_active": True,
        },
    ]

    for data in rules_data:
        db.add(EscalationRule(**data))

    db.flush()


def seed_holiday_calendar(db: Session) -> HolidayCalendar:
    """Create India holiday calendar with holidays."""
    calendar = HolidayCalendar(
        calendar_code="IN",
        name="India National Holidays",
        country_code="IN",
        description="Standard Indian national and bank holidays",
        is_active=True,
    )
    db.add(calendar)
    db.flush()

    year = date.today().year
    holidays = [
        (date(year, 1, 26), "Republic Day", True),
        (date(year, 3, 14), "Holi", False),
        (date(year, 3, 29), "Good Friday", False),
        (date(year, 4, 14), "Ambedkar Jayanti", True),
        (date(year, 5, 1), "May Day", True),
        (date(year, 8, 15), "Independence Day", True),
        (date(year, 10, 2), "Gandhi Jayanti", True),
        (date(year, 10, 12), "Dussehra", False),
        (date(year, 11, 1), "Diwali", False),
        (date(year, 11, 15), "Guru Nanak Jayanti", False),
        (date(year, 12, 25), "Christmas", True),
    ]

    for hdate, hname, recurring in holidays:
        db.add(Holiday(
            calendar_id=calendar.id,
            holiday_date=hdate,
            name=hname,
            is_recurring=recurring,
        ))

    db.flush()
    return calendar


def seed_benchmark_rates(db: Session) -> list[BenchmarkRate]:
    """Create benchmark rates with history."""
    today = date.today()

    benchmarks = []

    repo = BenchmarkRate(
        rate_code="REPO",
        name="RBI Repo Rate",
        description="Reserve Bank of India Repo Rate",
        currency="INR",
        source="RBI",
        frequency="as_announced",
        is_active=True,
    )
    db.add(repo)

    mclr = BenchmarkRate(
        rate_code="MCLR_1Y",
        name="MCLR 1-Year",
        description="Marginal Cost of Funds based Lending Rate (1 Year)",
        currency="INR",
        source="SBI",
        frequency="monthly",
        is_active=True,
    )
    db.add(mclr)

    tbill = BenchmarkRate(
        rate_code="TBILL_91",
        name="91-Day T-Bill Rate",
        description="91-Day Treasury Bill yield",
        currency="INR",
        source="RBI",
        frequency="weekly",
        is_active=True,
    )
    db.add(tbill)

    db.flush()
    benchmarks = [repo, mclr, tbill]

    # History for Repo Rate
    repo_history = [
        (today - timedelta(days=365), 6.50),
        (today - timedelta(days=270), 6.50),
        (today - timedelta(days=180), 6.50),
        (today - timedelta(days=90), 6.25),
        (today - timedelta(days=30), 6.25),
        (today, 6.00),
    ]
    for edate, rate in repo_history:
        db.add(BenchmarkRateHistory(
            benchmark_id=repo.id,
            effective_date=edate,
            rate_value=Decimal(str(rate)),
        ))

    # History for MCLR
    mclr_history = [
        (today - timedelta(days=365), 8.50),
        (today - timedelta(days=270), 8.45),
        (today - timedelta(days=180), 8.40),
        (today - timedelta(days=90), 8.35),
        (today - timedelta(days=30), 8.30),
        (today, 8.25),
    ]
    for edate, rate in mclr_history:
        db.add(BenchmarkRateHistory(
            benchmark_id=mclr.id,
            effective_date=edate,
            rate_value=Decimal(str(rate)),
        ))

    # History for T-Bill
    tbill_history = [
        (today - timedelta(days=90), 6.80),
        (today - timedelta(days=60), 6.75),
        (today - timedelta(days=30), 6.70),
        (today, 6.65),
    ]
    for edate, rate in tbill_history:
        db.add(BenchmarkRateHistory(
            benchmark_id=tbill.id,
            effective_date=edate,
            rate_value=Decimal(str(rate)),
        ))

    db.flush()
    return benchmarks


def seed_ecl_config(db: Session) -> None:
    """Create ECL configuration for LAP and general products."""
    today = date.today()

    # General ECL config
    db.add(ECLConfiguration(
        config_code="ECL-GENERAL",
        name="General Loan ECL Configuration",
        description="Default ECL parameters for unsecured and general loans",
        stage1_max_dpd=30,
        stage2_max_dpd=90,
        stage2_restructure_flag=True,
        stage3_write_off_flag=True,
        stage3_npa_flag=True,
        pd_stage1_12m=Decimal("0.5000"),
        pd_stage2_lifetime=Decimal("5.0000"),
        pd_stage3=Decimal("100.0000"),
        lgd_secured=Decimal("35.0000"),
        lgd_unsecured=Decimal("65.0000"),
        is_active=True,
        effective_date=today - timedelta(days=365),
    ))

    # LAP-specific ECL config (lower LGD due to collateral)
    db.add(ECLConfiguration(
        config_code="ECL-LAP",
        name="LAP ECL Configuration",
        description="ECL parameters for Loan Against Property (secured by immovable property)",
        stage1_max_dpd=30,
        stage2_max_dpd=90,
        stage2_restructure_flag=True,
        stage3_write_off_flag=True,
        stage3_npa_flag=True,
        pd_stage1_12m=Decimal("0.3000"),
        pd_stage2_lifetime=Decimal("3.0000"),
        pd_stage3=Decimal("100.0000"),
        lgd_secured=Decimal("25.0000"),
        lgd_unsecured=Decimal("55.0000"),
        is_active=True,
        effective_date=today - timedelta(days=365),
    ))

    db.flush()


def seed_fldg_arrangement(db: Session, partners: list[LoanPartner]) -> None:
    """Create FLDG arrangement between partners."""
    today = date.today()

    db.add(FLDGArrangement(
        arrangement_code="FLDG-SBI-BAJAJ-001",
        name="SBI-Bajaj Finance Co-Lending FLDG",
        description="First loss default guarantee by Bajaj Finance for SBI co-lending portfolio",
        originator_id=partners[1].id,
        lender_id=partners[0].id,
        fldg_type="first_loss",
        fldg_percent=Decimal("5.0000"),
        fldg_absolute_amount=Decimal("50000000.00"),
        effective_fldg_limit=Decimal("22500000.00"),
        first_loss_threshold=Decimal("0.00"),
        covers_principal=True,
        covers_interest=True,
        covers_fees=False,
        guarantee_form="cash_deposit",
        cash_deposit_account="FLDG-ESCROW-001",
        cash_deposit_bank="State Bank of India",
        current_fldg_balance=Decimal("22500000.00"),
        total_utilized=Decimal("0.00"),
        total_recovered=Decimal("0.00"),
        effective_date=today - timedelta(days=180),
        expiry_date=today + timedelta(days=185),
        trigger_dpd=90,
        trigger_on_write_off=True,
        trigger_on_npa=False,
        requires_top_up=True,
        top_up_threshold_percent=Decimal("80.0000"),
        status="active",
    ))

    db.flush()


def seed_all():
    """Run all seed functions."""
    db = SessionLocal()
    try:
        print("Seeding demo data...")

        # Check if data already exists
        existing = db.query(Borrower).first()
        if existing:
            print("Demo data already exists. Skipping seed.")
            return

        print("  - Creating borrowers...")
        borrowers = seed_borrowers(db)

        print("  - Creating additional borrowers...")
        extra_borrowers = seed_additional_borrowers(db)

        print("  - Creating loan products...")
        loan_products = seed_loan_products(db)

        print("  - Creating LAP product...")
        lap_product = seed_lap_product(db)

        print("  - Creating loan applications...")
        applications = seed_loan_applications(db, borrowers, loan_products)

        print("  - Creating LAP applications...")
        lap_applications = seed_lap_applications(db, extra_borrowers, lap_product)

        print("  - Creating loan accounts...")
        accounts = seed_loan_accounts(db, applications)

        print("  - Creating LAP loan accounts...")
        lap_accounts = seed_lap_accounts(db, lap_applications)

        print("  - Creating repayment schedules...")
        seed_repayment_schedules(db, accounts)

        print("  - Creating payments...")
        seed_payments(db, accounts)

        print("  - Creating collaterals...")
        collaterals = seed_collaterals(db, lap_applications, lap_accounts)

        print("  - Creating collateral sub-records...")
        seed_collateral_sub_records(db, collaterals)

        print("  - Creating documents with media...")
        seed_documents(db, lap_applications, collaterals, extra_borrowers)

        print("  - Creating loan partners...")
        partners = seed_loan_partners(db)

        print("  - Creating loan participations...")
        seed_loan_participations(db, accounts, partners)

        print("  - Creating FLDG arrangement...")
        seed_fldg_arrangement(db, partners)

        print("  - Creating delinquency snapshots...")
        seed_delinquency_snapshots(db, lap_accounts)

        print("  - Creating collection cases...")
        seed_collection_cases(db, lap_accounts)

        print("  - Creating escalation rules...")
        seed_escalation_rules(db)

        print("  - Creating holiday calendar...")
        calendar = seed_holiday_calendar(db)

        print("  - Creating benchmark rates...")
        benchmarks = seed_benchmark_rates(db)

        print("  - Creating ECL configurations...")
        seed_ecl_config(db)

        print("  - Creating investment issuers...")
        issuers = seed_investment_issuers(db)

        print("  - Creating investment products...")
        inv_products = seed_investment_products(db)

        print("  - Creating investments...")
        investments = seed_investments(db, issuers, inv_products)

        print("  - Creating selldown buyers...")
        selldown_buyers = seed_selldown_buyers(db)

        db.commit()
        print("\nDemo data seeded successfully!")
        print(f"  Borrowers:              {len(borrowers) + len(extra_borrowers)}")
        print(f"  Loan products:          {len(loan_products) + 1}")
        print(f"  Loan applications:      {len(applications) + len(lap_applications)}")
        print(f"  Loan accounts:          {len(accounts) + len(lap_accounts)}")
        print(f"  Collaterals:            {len(collaterals)}")
        print(f"  Loan partners:          {len(partners)}")
        print(f"  Investment issuers:     {len(issuers)}")
        print(f"  Investment products:    {len(inv_products)}")
        print(f"  Investments:            {len(investments)}")
        print(f"  Selldown buyers:        {len(selldown_buyers)}")
        print(f"  Benchmark rates:        {len(benchmarks)}")
        print(f"  Collection cases:       2")
        print(f"  Escalation rules:       5")
        print(f"  Holiday calendar:       1 (with 11 holidays)")
        print(f"  ECL configurations:     2")
        print(f"  FLDG arrangements:      1")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
