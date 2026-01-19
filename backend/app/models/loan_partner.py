from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoanPartner(Base):
    """
    Loan partner - can be originator, lender, or servicer.

    Partner types:
    - originator: Originates loans (provides FLDG, earns excess spread)
    - lender: Provides funding (receives yield, protected by FLDG)
    - servicer: Services loans (earns servicing fee)
    - investor: Invests in securitization pools
    """
    __tablename__ = "loan_partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))

    # Partner type: originator, lender, servicer, investor
    partner_type: Mapped[str] = mapped_column(String(50), default="lender")
    external_code: Mapped[str | None] = mapped_column(String(100), unique=True)

    # Registration details
    registration_number: Mapped[str | None] = mapped_column(String(100))
    registration_type: Mapped[str | None] = mapped_column(String(50))  # bank, nbfc, hfc, company

    # RBI license details (for regulated entities)
    rbi_license_number: Mapped[str | None] = mapped_column(String(100))
    rbi_license_category: Mapped[str | None] = mapped_column(String(50))

    # Default co-lending terms
    default_share_percent: Mapped[float | None] = mapped_column(Numeric(7, 4))  # e.g., 80 for 80:20
    default_yield_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))

    # FLDG terms
    provides_fldg: Mapped[bool] = mapped_column(Boolean, default=False)
    default_fldg_percent: Mapped[float | None] = mapped_column(Numeric(8, 4))
    fldg_guarantee_form: Mapped[str | None] = mapped_column(String(30))  # cash_deposit, bank_guarantee

    # Servicer capabilities
    is_servicer: Mapped[bool] = mapped_column(Boolean, default=False)
    default_servicer_fee_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))

    # Financial limits
    total_exposure_limit: Mapped[float | None] = mapped_column(Numeric(18, 2))
    current_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    available_exposure: Mapped[float | None] = mapped_column(Numeric(18, 2))

    # Contact details
    contact_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)

    # Bank details for settlements
    bank_name: Mapped[str | None] = mapped_column(String(100))
    bank_account_number: Mapped[str | None] = mapped_column(String(50))
    bank_ifsc: Mapped[str | None] = mapped_column(String(20))

    # Tax details
    pan: Mapped[str | None] = mapped_column(String(20))
    gst_number: Mapped[str | None] = mapped_column(String(20))
    tds_rate: Mapped[float | None] = mapped_column(Numeric(8, 4))  # TDS rate for income

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())
