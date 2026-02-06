"""
Collateral models for Loan Against Property (LAP).

Collateral: Property linked to a loan application/account
CollateralValuation: Valuation history
CollateralInsurance: Insurance records
CollateralLegalVerification: Legal verification records
"""

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Collateral(Base):
    """
    Collateral property linked to a loan application and optionally a loan account.
    """
    __tablename__ = "collaterals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("loan_applications.id"), index=True
    )
    loan_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_accounts.id"), nullable=True, index=True
    )

    # Property type
    property_type: Mapped[str] = mapped_column(String(50))  # residential, commercial, industrial, land, mixed_use
    property_sub_type: Mapped[str | None] = mapped_column(String(50))  # flat, bungalow, plot, warehouse, office, shop

    # Address
    address_line1: Mapped[str] = mapped_column(String(500))
    address_line2: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    pincode: Mapped[str] = mapped_column(String(10))
    district: Mapped[str | None] = mapped_column(String(100))
    taluka: Mapped[str | None] = mapped_column(String(100))
    village: Mapped[str | None] = mapped_column(String(100))

    # Area
    area_sqft: Mapped[float | None] = mapped_column(Numeric(12, 2))
    carpet_area_sqft: Mapped[float | None] = mapped_column(Numeric(12, 2))
    built_up_area_sqft: Mapped[float | None] = mapped_column(Numeric(12, 2))
    land_area_acres: Mapped[float | None] = mapped_column(Numeric(10, 4))

    # Ownership
    owner_name: Mapped[str] = mapped_column(String(200))
    co_owner_name: Mapped[str | None] = mapped_column(String(200))
    ownership_type: Mapped[str | None] = mapped_column(String(50))  # freehold, leasehold, co_operative
    title_deed_number: Mapped[str | None] = mapped_column(String(100))
    registration_number: Mapped[str | None] = mapped_column(String(100))
    registration_date: Mapped[Date | None] = mapped_column(Date)
    survey_number: Mapped[str | None] = mapped_column(String(100))
    cts_number: Mapped[str | None] = mapped_column(String(100))

    # Latest valuation snapshot (auto-updated from CollateralValuation)
    market_value: Mapped[float | None] = mapped_column(Numeric(18, 2))
    distress_value: Mapped[float | None] = mapped_column(Numeric(18, 2))
    realizable_value: Mapped[float | None] = mapped_column(Numeric(18, 2))
    ltv_ratio: Mapped[float | None] = mapped_column(Numeric(8, 4))
    valuation_date: Mapped[Date | None] = mapped_column(Date)
    valuer_name: Mapped[str | None] = mapped_column(String(200))

    # Legal
    legal_status: Mapped[str | None] = mapped_column(String(30))  # pending, clear, issue_found
    encumbrance_status: Mapped[str | None] = mapped_column(String(30))  # clear, encumbered, partial
    cersai_registration_number: Mapped[str | None] = mapped_column(String(100))
    cersai_registration_date: Mapped[Date | None] = mapped_column(Date)

    # Insurance snapshot (auto-updated from CollateralInsurance)
    insurance_policy_number: Mapped[str | None] = mapped_column(String(100))
    insurance_expiry_date: Mapped[Date | None] = mapped_column(Date)
    insured_value: Mapped[float | None] = mapped_column(Numeric(18, 2))

    # Charge / Lien
    charge_type: Mapped[str | None] = mapped_column(String(50))  # first_charge, second_charge, pari_passu
    charge_creation_date: Mapped[Date | None] = mapped_column(Date)
    charge_id: Mapped[str | None] = mapped_column(String(100))

    # Status
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending, verified, approved, released
    is_primary_security: Mapped[bool | None] = mapped_column(default=True)
    remarks: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    application = relationship("LoanApplication")
    loan_account = relationship("LoanAccount")
    valuations: Mapped[list["CollateralValuation"]] = relationship(
        "CollateralValuation",
        back_populates="collateral",
        cascade="all, delete-orphan",
    )
    insurance_records: Mapped[list["CollateralInsurance"]] = relationship(
        "CollateralInsurance",
        back_populates="collateral",
        cascade="all, delete-orphan",
    )
    legal_verifications: Mapped[list["CollateralLegalVerification"]] = relationship(
        "CollateralLegalVerification",
        back_populates="collateral",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="collateral",
    )


class CollateralValuation(Base):
    """Valuation history for a collateral."""
    __tablename__ = "collateral_valuations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collateral_id: Mapped[int] = mapped_column(
        ForeignKey("collaterals.id", ondelete="CASCADE"), index=True
    )
    valuation_date: Mapped[Date] = mapped_column(Date)
    valuer_name: Mapped[str] = mapped_column(String(200))
    valuer_agency: Mapped[str | None] = mapped_column(String(200))
    valuation_type: Mapped[str] = mapped_column(String(30))  # initial, periodic, re_valuation, distress
    market_value: Mapped[float] = mapped_column(Numeric(18, 2))
    realizable_value: Mapped[float | None] = mapped_column(Numeric(18, 2))
    distress_value: Mapped[float | None] = mapped_column(Numeric(18, 2))
    forced_sale_value: Mapped[float | None] = mapped_column(Numeric(18, 2))
    ltv_at_valuation: Mapped[float | None] = mapped_column(Numeric(8, 4))
    report_reference: Mapped[str | None] = mapped_column(String(200))
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    collateral: Mapped["Collateral"] = relationship(
        "Collateral", back_populates="valuations"
    )


class CollateralInsurance(Base):
    """Insurance records for a collateral."""
    __tablename__ = "collateral_insurance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collateral_id: Mapped[int] = mapped_column(
        ForeignKey("collaterals.id", ondelete="CASCADE"), index=True
    )
    policy_number: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(200))
    insured_value: Mapped[float] = mapped_column(Numeric(18, 2))
    premium_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    start_date: Mapped[Date] = mapped_column(Date)
    expiry_date: Mapped[Date] = mapped_column(Date)
    renewal_date: Mapped[Date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, expired, cancelled
    is_assigned_to_lender: Mapped[bool | None] = mapped_column(default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    collateral: Mapped["Collateral"] = relationship(
        "Collateral", back_populates="insurance_records"
    )


class CollateralLegalVerification(Base):
    """Legal verification records for a collateral."""
    __tablename__ = "collateral_legal_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collateral_id: Mapped[int] = mapped_column(
        ForeignKey("collaterals.id", ondelete="CASCADE"), index=True
    )
    verification_type: Mapped[str] = mapped_column(String(50))  # title_search, encumbrance_check, cersai_search, revenue_record, mutation_check
    verification_date: Mapped[Date] = mapped_column(Date)
    verified_by: Mapped[str] = mapped_column(String(200))
    verification_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, clear, issue_found, waived
    report_reference: Mapped[str | None] = mapped_column(String(200))
    findings: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    collateral: Mapped["Collateral"] = relationship(
        "Collateral", back_populates="legal_verifications"
    )
