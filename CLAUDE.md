# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Start PostgreSQL (optional - defaults to SQLite)
docker compose up -d

# Setup (from project root)
cd backend
python -m venv .venv
.venv/Scripts/Activate.ps1  # Windows PowerShell
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env

# Initialize database schema
python -m app.db.init_db

# Run development server
uvicorn app.main:app --reload

# Run tests (from project root)
pytest

# Run a single test
pytest tests/test_schedule.py
pytest tests/test_schedule.py::test_generate_emi_schedule
```

## Project Overview

Unified Loan Origination and Loan Management System (LOS/LMS) - an integrated financial lending and investment platform handling:
- **Loans**: From application to repayment (retail, commercial, co-lending)
- **Investments**: Fixed income instruments (NCDs, CPs, Bonds, G-Secs)
- **Selldown**: Loan/investment transfers and sales (full/partial, mid-tenure)

## Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── core/config.py       # Settings via pydantic-settings (.env)
│   ├── db/
│   │   ├── base.py          # SQLAlchemy Base
│   │   ├── session.py       # Database session factory
│   │   └── init_db.py       # Schema initialization
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── api/
│   │   ├── deps.py          # Dependency injection (get_db)
│   │   └── routers/         # API endpoint modules
│   └── services/            # Business logic
│       ├── schedule.py      # Amortization schedule generation
│       └── payments.py      # Payment processing, DPD calculation
tests/                       # pytest tests
```

### Key Services

**`services/schedule.py`** - Amortization schedule generation
- `generate_amortization_schedule()`: Creates repayment schedules
- Supports: EMI, interest_only, bullet schedule types
- Uses `Decimal` for financial precision (ROUND_HALF_UP)

**`services/payments.py`** - Payment processing
- `apply_payment()`: Allocates payments using waterfall (fees → interest → principal)
- `compute_dpd()`: Calculates Days Past Due from oldest unpaid installment
- `_refresh_account_balances()`: Updates loan account outstanding amounts

**`services/selldown.py`** - Loan/Investment selldown
- `initiate_loan_selldown()`: Create loan selldown transaction
- `initiate_investment_selldown()`: Create investment selldown transaction
- `approve_selldown()` / `settle_selldown()`: Workflow processing
- `split_collection_for_selldown()`: Post-sale collection splitting

**`services/investment.py`** - Fixed income investment management
- `create_investment()`: Create NCD, CP, Bond, G-Sec investments
- `generate_coupon_schedule()`: Generate coupon payment schedule
- `accrue_interest()`: Daily interest accrual with premium/discount amortization
- `receive_coupon()`: Record coupon receipt
- `mature_investment()`: Process maturity/redemption
- `mark_to_market()`: MTM valuation
- `calculate_ytm()`: Yield to maturity calculation

### Data Model

Core entities in `models/`:
- `Borrower` → `LoanApplication` → `LoanAccount` → `RepaymentSchedule`
- `LoanProduct`: Configurable loan terms
- `LoanPartner` + `LoanParticipation`: Co-lending support with share percentages
- `Payment` + `PaymentAllocation`: Payment tracking per schedule item
- `Document`: File attachments linked to applications

**Selldown entities**:
- `SelldownBuyer`: Buyer/investor profiles (banks, NBFCs, AIFs)
- `SelldownTransaction`: Sale records with gain/loss, pricing
- `SelldownSettlement`: Settlement tracking
- `SelldownCollectionSplit`: Post-sale collection distribution

**Investment entities** (NCDs, CPs, Bonds):
- `InvestmentIssuer`: Issuer profiles with ratings
- `InvestmentProduct`: Product configuration (NCD, CP, Bond, G-Sec)
- `Investment`: Individual holdings with YTM, accrued interest
- `InvestmentCouponSchedule`: Coupon payment schedule
- `InvestmentAccrual`: Daily interest accrual records
- `InvestmentValuation`: MTM valuation history

### API Endpoints

All routers in `api/routers/` follow RESTful conventions:
- `/borrowers`, `/loan-products`, `/loan-applications`
- `/loan-accounts`, `/loan-accounts/{id}/schedule`, `/loan-accounts/{id}/payments`
- `/loan-partners`, `/loan-participations`, `/documents`
- `/selldown-buyers`, `/selldown-transactions` - Selldown management
- `/investments`, `/investment-issuers`, `/investment-products` - Investment management
- `/health` - Health check

## Domain-Specific Notes

### Financial Calculations
- All monetary calculations use `Decimal` with explicit rounding
- Day-count: Currently monthly periods; designed for extension to 30/360, ACT/365
- EMI formula: `P * r * (1+r)^n / ((1+r)^n - 1)`

### Payment Waterfall
Default allocation order: fees → interest → principal (configurable per product in future)

### Co-Lending
`LoanParticipation` links `LoanAccount` to `LoanPartner` with:
- `share_percent`: Principal/interest split ratio
- `interest_rate`: Optional differential rate per partner
- `fee_share_percent`: Fee allocation override

### Delinquency (DPD)
Computed from oldest unpaid installment's due date vs current date. Stored on `LoanAccount.dpd`.

### Selldown
Loan/investment transfers to third parties:
- **Full Selldown**: 100% of position sold
- **Partial Selldown**: Portion sold (e.g., 60%), seller retains rest
- **Gain/Loss**: `Sale Price - Book Value`
- **Post-sale servicing**: Optional servicing arrangement with fee

### Investments (NCDs, CPs, Bonds)
Fixed income instrument management:
- **Instrument types**: NCD, CP, Bond, G-Sec, T-Bill, CD
- **Coupon types**: Fixed, Floating, Zero Coupon, Step-Up/Down
- **Day-count**: ACT/365, ACT/360, 30/360, ACT/ACT
- **Valuation**: Amortized cost (HTM) or Mark-to-Market (AFS/HFT)
- **YTM**: Yield to Maturity calculation using Newton-Raphson

## Configuration

Environment variables (`.env`):
- `DATABASE_URL`: Default `sqlite:///./los_lms.db`, or PostgreSQL connection string
- `APP_NAME`, `ENV`, `LOG_LEVEL`

## Reference Documents

- `docs/requirements-summary.md` - Condensed requirements
- `*.pdf` files - Full system specifications
