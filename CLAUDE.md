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

Unified Loan Origination and Loan Management System (LOS/LMS) - an integrated financial lending platform handling loans from application to repayment.

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

### Data Model

Core entities in `models/`:
- `Borrower` → `LoanApplication` → `LoanAccount` → `RepaymentSchedule`
- `LoanProduct`: Configurable loan terms
- `LoanPartner` + `LoanParticipation`: Co-lending support with share percentages
- `Payment` + `PaymentAllocation`: Payment tracking per schedule item
- `Document`: File attachments linked to applications

### API Endpoints

All routers in `api/routers/` follow RESTful conventions:
- `/borrowers`, `/loan-products`, `/loan-applications`
- `/loan-accounts`, `/loan-accounts/{id}/schedule`, `/loan-accounts/{id}/payments`
- `/loan-partners`, `/loan-participations`, `/documents`
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

## Configuration

Environment variables (`.env`):
- `DATABASE_URL`: Default `sqlite:///./los_lms.db`, or PostgreSQL connection string
- `APP_NAME`, `ENV`, `LOG_LEVEL`

## Reference Documents

- `docs/requirements-summary.md` - Condensed requirements
- `*.pdf` files - Full system specifications
