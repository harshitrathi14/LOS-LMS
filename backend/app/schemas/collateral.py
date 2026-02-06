from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# --- Collateral ---

class CollateralBase(BaseModel):
    application_id: int
    loan_account_id: int | None = None
    property_type: str
    property_sub_type: str | None = None
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str
    pincode: str
    district: str | None = None
    taluka: str | None = None
    village: str | None = None
    area_sqft: float | None = None
    carpet_area_sqft: float | None = None
    built_up_area_sqft: float | None = None
    land_area_acres: float | None = None
    owner_name: str
    co_owner_name: str | None = None
    ownership_type: str | None = None
    title_deed_number: str | None = None
    registration_number: str | None = None
    registration_date: date | None = None
    survey_number: str | None = None
    cts_number: str | None = None
    charge_type: str | None = None
    charge_creation_date: date | None = None
    charge_id: str | None = None
    status: str = "pending"
    is_primary_security: bool | None = True
    remarks: str | None = None


class CollateralCreate(CollateralBase):
    pass


class CollateralUpdate(BaseModel):
    property_type: str | None = None
    property_sub_type: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    district: str | None = None
    taluka: str | None = None
    village: str | None = None
    area_sqft: float | None = None
    carpet_area_sqft: float | None = None
    built_up_area_sqft: float | None = None
    land_area_acres: float | None = None
    owner_name: str | None = None
    co_owner_name: str | None = None
    ownership_type: str | None = None
    title_deed_number: str | None = None
    registration_number: str | None = None
    registration_date: date | None = None
    survey_number: str | None = None
    cts_number: str | None = None
    charge_type: str | None = None
    charge_creation_date: date | None = None
    charge_id: str | None = None
    status: str | None = None
    is_primary_security: bool | None = None
    remarks: str | None = None


class CollateralRead(CollateralBase):
    id: int
    market_value: float | None = None
    distress_value: float | None = None
    realizable_value: float | None = None
    ltv_ratio: float | None = None
    valuation_date: date | None = None
    valuer_name: str | None = None
    legal_status: str | None = None
    encumbrance_status: str | None = None
    cersai_registration_number: str | None = None
    cersai_registration_date: date | None = None
    insurance_policy_number: str | None = None
    insurance_expiry_date: date | None = None
    insured_value: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --- CollateralValuation ---

class CollateralValuationBase(BaseModel):
    valuation_date: date
    valuer_name: str
    valuer_agency: str | None = None
    valuation_type: str
    market_value: float
    realizable_value: float | None = None
    distress_value: float | None = None
    forced_sale_value: float | None = None
    ltv_at_valuation: float | None = None
    report_reference: str | None = None
    remarks: str | None = None


class CollateralValuationCreate(CollateralValuationBase):
    pass


class CollateralValuationRead(CollateralValuationBase):
    id: int
    collateral_id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --- CollateralInsurance ---

class CollateralInsuranceBase(BaseModel):
    policy_number: str
    provider: str
    insured_value: float
    premium_amount: float | None = None
    start_date: date
    expiry_date: date
    renewal_date: date | None = None
    status: str = "active"
    is_assigned_to_lender: bool | None = False


class CollateralInsuranceCreate(CollateralInsuranceBase):
    pass


class CollateralInsuranceRead(CollateralInsuranceBase):
    id: int
    collateral_id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --- CollateralLegalVerification ---

class CollateralLegalVerificationBase(BaseModel):
    verification_type: str
    verification_date: date
    verified_by: str
    verification_status: str = "pending"
    report_reference: str | None = None
    findings: str | None = None
    remarks: str | None = None


class CollateralLegalVerificationCreate(CollateralLegalVerificationBase):
    pass


class CollateralLegalVerificationRead(CollateralLegalVerificationBase):
    id: int
    collateral_id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
