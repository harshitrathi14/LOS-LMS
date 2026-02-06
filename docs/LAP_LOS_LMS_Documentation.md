# Enterprise Lending System — LOS/LMS Complete Documentation

> **Version 3.0** | February 2026
> 82 ORM Models | 31 Services | 14 Routers | 453 Tests | 21,300+ Lines of Code

---

## Table of Contents

1. [Quick Start Guide](#1-quick-start-guide)
2. [System Overview & Architecture](#2-system-overview--architecture)
3. [Project Structure](#3-project-structure)
4. [Configuration & Environment](#4-configuration--environment)
5. [Database Setup & Seeding](#5-database-setup--seeding)
6. [Foundation Services — Interest, Frequency, Calendar](#6-foundation-services)
7. [Floating Rate & Benchmark Management](#7-floating-rate--benchmark-management)
8. [Schedule Generation — EMI, Bullet, Advanced](#8-schedule-generation)
9. [Fee Management](#9-fee-management)
10. [Payment Processing & Waterfall](#10-payment-processing--waterfall)
11. [Daily Interest Accrual](#11-daily-interest-accrual)
12. [Delinquency & NPA Classification](#12-delinquency--npa-classification)
13. [Loan Restructuring](#13-loan-restructuring)
14. [Prepayment & Foreclosure](#14-prepayment--foreclosure)
15. [Loan Closure & Write-Off](#15-loan-closure--write-off)
16. [LAP Collateral Management](#16-lap-collateral-management)
17. [Document & Media Management](#17-document--media-management)
18. [5-Level LAP Approval Workflow](#18-5-level-lap-approval-workflow)
19. [Workflow Engine](#19-workflow-engine)
20. [Co-Lending & Partner Management](#20-co-lending--partner-management)
21. [FLDG — First Loss Default Guarantee](#21-fldg--first-loss-default-guarantee)
22. [Settlement & Partner Ledger](#22-settlement--partner-ledger)
23. [Selldown & Loan Transfers](#23-selldown--loan-transfers)
24. [Investment Portfolio — NCD, CP, Bond, G-Sec](#24-investment-portfolio)
25. [Securitization](#25-securitization)
26. [Servicer Income & Withholding](#26-servicer-income--withholding)
27. [IFRS 9 ECL — Expected Credit Loss](#27-ifrs-9-ecl--expected-credit-loss)
28. [PAR Reporting](#28-par-reporting)
29. [End-of-Day Batch Processing](#29-end-of-day-batch-processing)
30. [Collection Management](#30-collection-management)
31. [Rules Engine](#31-rules-engine)
32. [KYC & Compliance](#32-kyc--compliance)
33. [Supply Chain Finance](#33-supply-chain-finance)
34. [Complete API Reference](#34-complete-api-reference)
35. [Complete Data Model Reference](#35-complete-data-model-reference)
36. [Domain Rules Reference](#36-domain-rules-reference)
37. [Testing](#37-testing)
38. [Demo Seed Data](#38-demo-seed-data)
39. [Deployment](#39-deployment)

---

## 1. Quick Start Guide

### Prerequisites

- Python 3.10+ (tested on 3.12)
- pip (Python package manager)
- Git
- PostgreSQL 14+ (optional — SQLite works out of the box)

### Installation (5 minutes)

```bash
# 1. Clone the repository
git clone <repo-url>
cd "LOS LMS"

# 2. Create virtual environment
cd backend
python3 -m venv .venv

# 3. Activate virtual environment
source .venv/bin/activate          # Linux / macOS / WSL
# .venv\Scripts\Activate.ps1      # Windows PowerShell
# .venv\Scripts\activate.bat      # Windows CMD

# 4. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. Configure environment (optional — defaults work for SQLite)
cp .env.example .env
# Edit .env if you want PostgreSQL:
#   DATABASE_URL=postgresql+psycopg2://los:los@localhost:5432/los_lms

# 6. Create database schema (creates all 82 tables)
python3 -m app.db.init_db

# 7. Seed demo data (10 borrowers, 6 products, 9 applications, etc.)
python3 -m app.db.seed_data

# 8. Start the development server
uvicorn app.main:app --reload
```

### Verify Installation

```bash
# Server running at http://localhost:8000
curl http://localhost:8000/
# → {"name": "LOS/LMS API", "status": "running"}

# Interactive API docs (Swagger UI)
open http://localhost:8000/docs

# Alternative API docs (ReDoc)
open http://localhost:8000/redoc

# Health check
curl http://localhost:8000/health
```

### Run Tests

```bash
# IMPORTANT: Run from project root, NOT from backend/
cd "LOS LMS"    # project root

# Run all 453 tests
python3 -m pytest

# Run with verbose output
python3 -m pytest -v

# Run specific test file
python3 -m pytest tests/test_schedule.py

# Run specific test
python3 -m pytest tests/test_schedule.py::test_generate_emi_schedule

# Run with coverage
python3 -m pytest --tb=short -q
```

> **Note**: `pytest.ini` sets `pythonpath = backend`, so all imports resolve from `backend/`. Tests must be run from the project root directory.

### Using with PostgreSQL

```bash
# Start PostgreSQL via Docker
docker compose up -d

# Update .env
DATABASE_URL=postgresql+psycopg2://los:los@localhost:5432/los_lms

# Initialize and seed
cd backend
python3 -m app.db.init_db
python3 -m app.db.seed_data
```

---

## 2. System Overview & Architecture

### What This System Does

A comprehensive, enterprise-grade **Loan Origination System (LOS)** and **Loan Management System (LMS)** covering the full lending lifecycle:

| Area | Capabilities |
|---|---|
| **Origination (LOS)** | Borrower onboarding, KYC, loan application, product selection, credit assessment, 5-level approval workflow |
| **Loan Management (LMS)** | Schedule generation, payment processing, accrual, delinquency tracking, NPA classification |
| **Collateral (LAP)** | Property registration, valuation lifecycle, LTV calculation, insurance tracking, legal verification |
| **Collections** | Case management, action logging, PTP tracking, escalation rules, dashboard |
| **Co-Lending** | Partner share management, disbursement/payment splits, partner ledger, settlement |
| **Risk & Compliance** | IFRS 9 ECL staging, NPA classification, PAR reporting, FLDG guarantee |
| **Institutional** | Securitization pools, selldown transactions, investment portfolio (NCD/CP/Bond/G-Sec), servicer income |
| **Platform** | Workflow engine, rules engine, KYC verification, supply chain finance |

### Technology Stack

| Component | Technology | Version |
|---|---|---|
| **API Framework** | FastAPI | ≥ 0.110 |
| **ORM** | SQLAlchemy 2.0 | ≥ 2.0 (Mapped types) |
| **Validation** | Pydantic v2 | ≥ 2.6 |
| **Database** | SQLite (dev) / PostgreSQL (prod) | 14+ |
| **Configuration** | pydantic-settings | ≥ 2.2 |
| **Migrations** | Alembic | ≥ 1.13 |
| **Server** | Uvicorn | ≥ 0.29 |
| **Testing** | pytest + httpx | ≥ 8.0 |

### Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                                 │
│     Mobile App  │  Web App  │  External API  │  Swagger UI     │
└───────────────────────┬────────────────────────────────────────┘
                        │ HTTP/REST
┌───────────────────────▼────────────────────────────────────────┐
│                  API LAYER (FastAPI Routers)                    │
│  health │ borrowers │ loan_products │ loan_applications        │
│  loan_accounts │ loan_partners │ loan_participations           │
│  documents │ holiday_calendars │ benchmark_rates                │
│  loan_lifecycle │ collaterals │ collections                     │
└───────────────────────┬────────────────────────────────────────┘
                        │ Function calls
┌───────────────────────▼────────────────────────────────────────┐
│                  SERVICE LAYER (31 modules)                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Foundation: interest, frequency, calendar, floating_rate│   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Schedule: schedule, advanced_schedule, fees             │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Lifecycle: payments, accrual, delinquency, restructure  │   │
│  │            prepayment, closure, lifecycle               │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Partners: co_lending, settlement, fldg                  │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Institutional: securitization, investment, selldown,    │   │
│  │                servicer_income                          │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Risk: ecl, par_report, eod, delinquency                │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Platform: workflow, lap_workflow, rules_engine, kyc,    │   │
│  │           supply_chain, collection, collateral          │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────────────┬────────────────────────────────────────┘
                        │ SQLAlchemy ORM
┌───────────────────────▼────────────────────────────────────────┐
│                  DATA LAYER (82 ORM Models)                    │
│  34 model files across 82 tables                               │
│  SQLAlchemy 2.0 Mapped types │ Numeric(18,2) for money         │
└───────────────────────┬────────────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────────────┐
│                  DATABASE                                       │
│       SQLite (development) │ PostgreSQL (production)            │
└────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Financial Precision**: All monetary calculations use `Decimal` with `ROUND_HALF_UP`. Constants: `CENT = Decimal("0.01")`, `RATE_PRECISION = Decimal("0.0000000001")`. Model fields use `Numeric(18, 2)` but map as `float` — Decimal conversion happens in services.

2. **Stateless Services**: Services receive `db: Session` explicitly. No global state, no ORM side effects outside the function. This enables testability and composability.

3. **Layered Architecture**: Foundation (pure calculation, no DB) → Schedule Generation → Loan Lifecycle → Co-Lending/Institutional → Risk/Compliance.

4. **Router Pattern**: Routers do simple CRUD directly (no service layer for basic operations). Complex operations call services. All use `Depends(get_db)` for session injection.

---

## 3. Project Structure

```
LOS LMS/
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app, 13 router registrations
│   │   ├── core/
│   │   │   └── config.py                # pydantic-settings (DATABASE_URL, APP_NAME, ENV, LOG_LEVEL)
│   │   ├── db/
│   │   │   ├── base.py                  # SQLAlchemy DeclarativeBase
│   │   │   ├── session.py               # Engine + SessionLocal factory (pool_pre_ping=True)
│   │   │   ├── init_db.py              # Base.metadata.create_all — creates all 82 tables
│   │   │   └── seed_data.py            # Comprehensive demo data seeding (20+ seed functions)
│   │   ├── models/                      # 34 ORM model files, 82 model classes
│   │   │   ├── __init__.py             # Exports all 82 models
│   │   │   ├── borrower.py             # Borrower
│   │   │   ├── loan_product.py         # LoanProduct
│   │   │   ├── loan_application.py     # LoanApplication
│   │   │   ├── loan_account.py         # LoanAccount (50+ fields)
│   │   │   ├── repayment_schedule.py   # RepaymentSchedule
│   │   │   ├── payment.py              # Payment
│   │   │   ├── payment_allocation.py   # PaymentAllocation
│   │   │   ├── fee.py                  # FeeType, ProductFee, FeeCharge
│   │   │   ├── holiday_calendar.py     # HolidayCalendar, Holiday
│   │   │   ├── benchmark_rate.py       # BenchmarkRate, BenchmarkRateHistory
│   │   │   ├── interest_accrual.py     # InterestAccrual
│   │   │   ├── schedule_config.py      # ScheduleConfiguration
│   │   │   ├── delinquency.py          # DelinquencySnapshot
│   │   │   ├── restructure.py          # LoanRestructure
│   │   │   ├── prepayment.py           # Prepayment
│   │   │   ├── write_off.py            # WriteOff, WriteOffRecovery
│   │   │   ├── collateral.py           # Collateral, CollateralValuation, CollateralInsurance, CollateralLegalVerification
│   │   │   ├── collection.py           # CollectionCase, CollectionAction, PromiseToPay, EscalationRule
│   │   │   ├── document.py             # Document (with media & geo-tagging)
│   │   │   ├── loan_partner.py         # LoanPartner
│   │   │   ├── loan_participation.py   # LoanParticipation
│   │   │   ├── partner_ledger.py       # PartnerLedgerEntry, PartnerSettlement, PartnerSettlementDetail
│   │   │   ├── fldg.py                 # FLDGArrangement, FLDGUtilization, FLDGRecovery
│   │   │   ├── ecl.py                  # ECLConfiguration, ECLProvision, ECLStaging, ECLMovement, ECLPortfolioSummary, ECLUpload
│   │   │   ├── servicer_income.py      # ServicerArrangement, ServicerIncomeAccrual, ServicerIncomeDistribution, ExcessSpreadTracking, WithholdingTracker
│   │   │   ├── investment.py           # InvestmentIssuer, InvestmentProduct, Investment, + 5 sub-models
│   │   │   ├── securitization.py       # SecuritizationPool, PoolLoan, PoolInvestment, Investor, InvestorCashFlow
│   │   │   ├── selldown.py             # SelldownTransaction, SelldownBuyer, SelldownSettlement, SelldownCollectionSplit, SelldownPortfolioSummary
│   │   │   ├── supply_chain.py         # Counterparty, CreditLimit, Invoice
│   │   │   ├── user.py                 # User, RolePermission
│   │   │   ├── rules.py                # RuleSet, DecisionRule, RuleExecutionLog
│   │   │   ├── workflow.py             # WorkflowDefinition, WorkflowInstance, WorkflowTask, WorkflowTransition
│   │   │   └── kyc.py                  # KYCVerification, KYCRequirement, CreditBureauReport
│   │   ├── schemas/                     # 15 Pydantic v2 schema files
│   │   │   ├── borrower.py, loan_product.py, loan_application.py, loan_account.py
│   │   │   ├── repayment_schedule.py, payment.py, holiday_calendar.py, benchmark_rate.py
│   │   │   ├── interest_accrual.py, loan_partner.py, loan_participation.py
│   │   │   ├── collateral.py, collection.py, document.py
│   │   │   └── __init__.py
│   │   ├── api/
│   │   │   ├── deps.py                 # get_db() yields SessionLocal with try/finally close
│   │   │   └── routers/                # 14 router files (13 active + __init__.py)
│   │   │       ├── health.py, borrowers.py, loan_products.py, loan_applications.py
│   │   │       ├── loan_accounts.py, loan_partners.py, loan_participations.py
│   │   │       ├── documents.py, holiday_calendars.py, benchmark_rates.py
│   │   │       ├── loan_lifecycle.py, collaterals.py, collections.py
│   │   │       └── __init__.py
│   │   └── services/                    # 31 business logic modules
│   │       ├── interest.py, frequency.py, calendar.py, floating_rate.py    # Foundation
│   │       ├── schedule.py, advanced_schedule.py, fees.py                  # Schedule
│   │       ├── payments.py, accrual.py, delinquency.py                    # Daily operations
│   │       ├── restructure.py, prepayment.py, closure.py, lifecycle.py    # Lifecycle
│   │       ├── co_lending.py, settlement.py, fldg.py                      # Partners
│   │       ├── securitization.py, investment.py, selldown.py              # Institutional
│   │       ├── servicer_income.py, ecl.py, par_report.py, eod.py         # Risk/Income
│   │       ├── workflow.py, lap_workflow.py, rules_engine.py              # Platform
│   │       ├── kyc.py, supply_chain.py                                    # Compliance
│   │       └── collateral.py, collection.py                               # LAP/Collections
│   ├── tests/                           # 9 backend test files
│   ├── requirements.txt                 # Production dependencies
│   ├── requirements-dev.txt            # Test dependencies (pytest, httpx)
│   ├── .env.example                    # Environment template
│   ├── alembic.ini                     # Migration config
│   └── migrations/                     # Alembic migrations
├── tests/                               # 13 root-level test files
├── docs/                                # Documentation & presentation
│   ├── LAP_LOS_LMS_Documentation.md   # This file
│   ├── LOS_LMS_System_Presentation.pptx
│   └── generate_presentation.py        # PPTX generator script
├── pytest.ini                           # pythonpath = backend
├── docker-compose.yml                  # PostgreSQL container
└── CLAUDE.md                           # AI assistant instructions
```

---

## 4. Configuration & Environment

### Environment Variables

Create `.env` in `backend/` (or copy from `.env.example`):

```bash
# Application
APP_NAME=LOS/LMS API
ENV=local                    # local, development, staging, production
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR

# Database
DATABASE_URL=sqlite:///./los_lms.db                                    # SQLite (default)
# DATABASE_URL=postgresql+psycopg2://los:los@localhost:5432/los_lms   # PostgreSQL
```

### Settings Class (`backend/app/core/config.py`)

```python
class Settings(BaseSettings):
    app_name: str = "LOS/LMS API"
    env: str = "local"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./los_lms.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

Settings are loaded via `pydantic-settings` with automatic `.env` file parsing. Access via `get_settings()` which uses `@lru_cache` for singleton behavior.

### Dependencies

**Production** (`requirements.txt`):
```
fastapi>=0.110          # REST API framework
uvicorn[standard]>=0.29 # ASGI server
sqlalchemy>=2.0         # ORM with Mapped types
pydantic>=2.6           # Request/response validation
pydantic-settings>=2.2  # Environment configuration
psycopg2-binary>=2.9    # PostgreSQL driver
python-dotenv>=1.0      # .env file loading
alembic>=1.13           # Database migrations
```

**Development** (`requirements-dev.txt`):
```
pytest>=8.0             # Test framework
httpx>=0.27             # HTTP client for API tests
```

---

## 5. Database Setup & Seeding

### Schema Creation

```bash
cd backend
python3 -m app.db.init_db
```

This runs `Base.metadata.create_all()` which creates all 82 tables defined in the ORM models. Safe to run multiple times (no-op if tables exist).

### Database Seeding

```bash
cd backend
python3 -m app.db.seed_data
```

Seeds comprehensive demo data covering all modules. Skips if data already exists (checks for Borrower records). To re-seed, delete the database first:

```bash
rm backend/los_lms.db                # Delete SQLite DB
cd backend
python3 -m app.db.init_db            # Recreate schema
python3 -m app.db.seed_data          # Seed fresh data
```

**Seed Data Summary**:

| Entity | Count | Details |
|---|---|---|
| Borrowers | 10 | 5 base + 5 LAP-specific borrowers |
| Loan Products | 6 | Home loan, personal, business, vehicle, gold, LAP |
| Loan Applications | 9 | 5 general + 4 LAP (various workflow stages) |
| Loan Accounts | 6 | 3 general + 3 LAP (current, SMA-1, NPA) |
| Repayment Schedules | — | Full EMI schedules for all accounts |
| Payments | — | Payment records for existing accounts |
| Collaterals | 4 | Mumbai flat, Gurgaon office, Pune bungalow, Chennai shop |
| Collateral Valuations | — | Initial + periodic valuations |
| Collateral Insurance | — | Active insurance policies |
| Legal Verifications | — | Title search, encumbrance checks |
| Documents | 8 | KYC, property photos, site visit video, legal docs |
| Loan Partners | 3 | SBI, Bajaj Finance, HDFC |
| Loan Participations | — | Co-lending shares |
| FLDG Arrangement | 1 | SBI-Bajaj first loss guarantee |
| Delinquency Snapshots | — | For SMA-1 and NPA accounts |
| Collection Cases | 2 | With actions, PTPs |
| Escalation Rules | 5 | SMA-0 through NPA + high amount |
| Holiday Calendar | 1 | India calendar with 11 holidays |
| Benchmark Rates | 3 | REPO, MCLR_1Y, TBILL_91 with history |
| ECL Configurations | 2 | General + LAP-specific |
| Investment Issuers | 4 | REC, HDFC, SBI, Infosys |
| Investment Products | 4 | NCD, CP, Bond, G-Sec |
| Investments | 4 | One per product type |
| Selldown Buyers | 3 | Asset reconstruction companies |

---

## 6. Foundation Services

### 6.1 Interest Calculation (`services/interest.py`)

Pure mathematical functions — no database dependency.

**Day-Count Conventions**:

| Convention | Formula | Use Case |
|---|---|---|
| `30/360` | Assumes 30-day months, 360-day year | US corporate bonds |
| `ACT/365` | Actual days / 365 | Indian lending standard |
| `ACT/360` | Actual days / 360 | Money market instruments |
| `ACT/ACT` | Actual days / actual year (365 or 366) | Government bonds (ISDA) |

**Key Functions**:

| Function | Description |
|---|---|
| `year_fraction(start, end, convention)` | Calculate year fraction between two dates |
| `calculate_interest(principal, rate, start, end, convention)` | Interest for a period |
| `calculate_daily_rate(annual_rate, convention)` | Convert annual to daily rate |
| `calculate_periodic_rate(annual_rate, periods_per_year)` | Convert annual to periodic rate |
| `calculate_effective_annual_rate(nominal_rate, compounding_frequency)` | Nominal to effective rate |
| `calculate_emi(principal, annual_rate, tenure_months)` | EMI: `P * r * (1+r)^n / ((1+r)^n - 1)` |
| `is_leap_year(year)` | Leap year check for ACT/ACT |
| `actual_days_between(start, end)` | Actual calendar days |
| `days_30_360(start, end)` | Days using 30/360 convention |

### 6.2 Payment Frequency (`services/frequency.py`)

**Supported Frequencies**: weekly, biweekly, monthly, quarterly, semiannual, annual

**Key Functions**:

| Function | Description |
|---|---|
| `periods_per_year(frequency)` | weekly=52, biweekly=26, monthly=12, quarterly=4, etc. |
| `generate_due_dates(start, frequency, num_periods)` | Generate list of due dates |
| `calculate_tenure_periods(tenure_months, frequency)` | Convert months to period count |
| `add_period(date, frequency)` | Add one period to a date |
| `get_period_start_end(date, frequency)` | Get period boundaries |
| `annualize_rate(periodic_rate, frequency)` | Convert periodic rate to annual |

### 6.3 Business Day Calendar (`services/calendar.py`)

**Adjustment Modes**:

| Mode | Behavior |
|---|---|
| `following` | Move to next business day |
| `preceding` | Move to previous business day |
| `modified_following` | Next business day, unless it crosses month-end, then preceding |
| `modified_preceding` | Previous business day, unless it crosses month-start, then following |

**Key Functions**:

| Function | Description |
|---|---|
| `is_business_day(date, calendar_id, db)` | Check if date is a business day |
| `adjust_for_business_day(date, mode, calendar_id, db)` | Adjust date per mode |
| `adjust_due_dates(dates, mode, calendar_id, db)` | Bulk adjust schedule dates |
| `business_days_between(start, end, calendar_id, db)` | Count business days |
| `add_business_days(date, days, calendar_id, db)` | Add N business days |
| `get_holidays_for_calendar(calendar_id, year, db)` | Get holidays for a year |

---

## 7. Floating Rate & Benchmark Management

### Service: `services/floating_rate.py`

**Benchmark Types**: REPO, MCLR, SOFR, LIBOR, T-Bill, Prime Rate

**Effective Rate Calculation**:
```
effective_rate = benchmark_rate + spread
effective_rate = max(floor_rate, min(cap_rate, effective_rate))
```

**Key Functions**:

| Function | Description |
|---|---|
| `get_benchmark_rate(benchmark_id, as_of_date, db)` | Get rate effective on a date |
| `get_current_benchmark_rate(benchmark_id, db)` | Latest rate value |
| `calculate_effective_rate(benchmark_rate, spread, floor, cap)` | Apply spread with floor/cap |
| `check_rate_reset_due(account, as_of_date)` | Check if reset is needed |
| `calculate_next_reset_date(last_reset, frequency)` | Next reset date |
| `apply_rate_reset(account_id, as_of_date, db)` | Execute rate reset |
| `get_rate_reset_schedule(account_id, db)` | Full reset schedule |
| `add_benchmark_rate_value(benchmark_id, date, value, db)` | Add new rate history |

### Models

**BenchmarkRate**: `id`, `rate_code` (unique), `name`, `currency`, `source`, `is_active`

**BenchmarkRateHistory**: `benchmark_rate_id` (FK), `effective_date`, `rate_value`, `published_date`, `source_reference`

---

## 8. Schedule Generation

### 8.1 Core Schedules (`services/schedule.py`)

**Schedule Types**:

| Type | Description | Formula |
|---|---|---|
| **EMI** | Equal monthly installments | `P * r * (1+r)^n / ((1+r)^n - 1)` |
| **Interest-Only** | Pay interest each period, principal at maturity | `interest = P * r` per period |
| **Bullet** | No periodic payments, all at maturity | Single payment at end |

**ScheduleItem (TypedDict)**:
```python
{
    "installment_number": int,
    "due_date": date,
    "opening_balance": float,
    "principal_due": float,
    "interest_due": float,
    "fees_due": float,
    "total_due": float,
    "closing_balance": float,
}
```

**Key Functions**:

| Function | Description |
|---|---|
| `generate_amortization_schedule(principal, rate, tenure, start_date, frequency, day_count, calendar_id, db)` | Full amortization schedule |
| `generate_schedule_simple(principal, rate, tenure, start_date)` | Quick schedule without calendar |
| `recalculate_schedule_from_installment(schedule, from_installment, new_rate, new_tenure)` | Recalculate after restructure |
| `calculate_total_interest(schedule)` | Sum of all interest |
| `calculate_total_payment(schedule)` | Sum of all payments |

### 8.2 Advanced Schedules (`services/advanced_schedule.py`)

| Type | Description |
|---|---|
| **Step-Up EMI** | Increasing payments (configurable step %, frequency) |
| **Step-Down EMI** | Decreasing payments over time |
| **Balloon** | Regular EMI with final lump-sum payment |
| **Moratorium** | Full, principal-only, or interest-only deferral periods |

**Moratorium Interest Treatment**:
- `capitalize` — Add interest to principal (increases future EMI)
- `accrue` — Track separately, collect after moratorium
- `waive` — No interest charged during moratorium

---

## 9. Fee Management

### Service: `services/fees.py`

**Fee Types**: processing, late_payment, prepayment_penalty, insurance, documentation, stamp_duty, legal, valuation

**Calculation Methods**:
- Flat amount
- Percentage of principal/outstanding/disbursed
- Min/max limits on calculated amounts

**Key Functions**:

| Function | Description |
|---|---|
| `calculate_fee(fee_type, base_amount)` | Calculate fee amount |
| `charge_fee(account_id, fee_type, db)` | Create fee charge record |
| `waive_fee(charge_id, waive_amount, reason, approver, db)` | Full or partial waiver |
| `get_outstanding_fees(account_id, db)` | Sum of unpaid fees |

### Models

**FeeType**: `code`, `name`, `calculation_type` (flat/percentage), `applies_to`, `charge_timing`, `is_taxable`, `tax_rate`, `waterfall_priority`

**ProductFee**: `product_id`, `fee_type_id`, `flat_amount`, `percentage_value`, `min_amount`, `max_amount`, `grace_days`, `is_mandatory`, `is_waivable`

**FeeCharge**: `loan_account_id`, `fee_type_id`, `charge_date`, `due_date`, `amount`, `tax_amount`, `paid_amount`, `waived_amount`, `status` (pending/paid/waived/partially_paid)

---

## 10. Payment Processing & Waterfall

### Service: `services/payments.py`

**Payment Waterfall** (strict allocation order per installment due date):

```
For each unpaid installment (oldest first):
  1. Fees outstanding    → Allocate from payment
  2. Interest outstanding → Allocate from payment
  3. Principal outstanding → Allocate from payment
```

**Key Functions**:

| Function | Description |
|---|---|
| `apply_payment(account_id, amount, paid_at, channel, reference, db)` | Full payment processing with waterfall |
| `_refresh_account_balances(account_id, db)` | Recalculate account outstanding balances |
| `compute_dpd(account_id, as_of_date, db)` | Calculate days past due |
| `apply_payment_and_update_dpd(account_id, amount, paid_at, db)` | Payment + DPD update in one call |

**Payment Allocation**:
- Creates `PaymentAllocation` records per installment touched
- Tracks `principal_allocated`, `interest_allocated`, `fees_allocated`
- Updates `RepaymentSchedule.principal_paid`, `interest_paid`, `fees_paid`
- Marks installment as `paid` when fully covered
- Tracks `unallocated_amount` on Payment for overpayments

### Models

**Payment**: `loan_account_id`, `amount`, `unallocated_amount`, `currency`, `channel` (cash/bank_transfer/cheque/upi/auto_debit), `reference`, `paid_at`

**PaymentAllocation**: `payment_id`, `schedule_id`, `principal_allocated`, `interest_allocated`, `fees_allocated`

---

## 11. Daily Interest Accrual

### Service: `services/accrual.py`

**Key Functions**:

| Function | Description |
|---|---|
| `accrue_interest_daily(account_id, accrual_date, db)` | Accrue one day's interest |
| `run_daily_accrual_batch(as_of_date, db)` | Batch accrual for all active accounts |
| `run_accrual_for_date_range(account_id, start, end, db)` | Catch-up accruals |
| `get_latest_accrual(account_id, db)` | Latest accrual record |
| `get_cumulative_accrual(account_id, db)` | Total accrued interest |
| `reset_cumulative_on_payment(account_id, reset_date, db)` | Reset after payment |
| `get_accrual_summary(account_id, db)` | Summary with opening/closing |

**Accrual Logic**:
```
daily_interest = principal_outstanding * (annual_rate / days_in_year)
cumulative = previous_cumulative + daily_interest
```

For floating rate loans: `effective_rate = benchmark_rate + spread`

### Model: InterestAccrual

Fields: `loan_account_id`, `accrual_date`, `opening_balance`, `principal_outstanding`, `interest_rate`, `benchmark_rate`, `spread`, `day_count_convention`, `accrued_amount`, `cumulative_accrued`, `opening_cumulative`, `status` (accrued/posted/reversed)

---

## 12. Delinquency & NPA Classification

### Service: `services/delinquency.py`

**DPD Calculation**:
```
days_past_due = (as_of_date - oldest_unpaid_due_date).days
```

**Delinquency Buckets & NPA Classification**:

| Classification | DPD Range | ECL Stage | Action |
|---|---|---|---|
| Standard | 0 | Stage 1 | Current |
| SMA-0 | 1–30 | Stage 1 | Early warning, SMS reminder |
| SMA-1 | 31–60 | Stage 2 | Watch list, phone calls |
| SMA-2 | 61–90 | Stage 2 | Close monitoring, field visit |
| NPA — Substandard | 91–365 | Stage 3 | Non-performing, legal notice |
| NPA — Doubtful | 366–1095 | Stage 3 | Recovery action |
| NPA — Loss | 1096+ | Stage 3 | Write-off candidate |

**RBI Sticky NPA Rule**: Once classified NPA, stays NPA until DPD returns to **0** (full cure required — partial payments don't remove NPA status).

**Key Functions**:

| Function | Description |
|---|---|
| `get_bucket_for_dpd(dpd)` | Map DPD to bucket name |
| `get_dpd_classification(dpd)` | Full classification (bucket + NPA aging) |
| `is_npa(dpd)` | Check if DPD ≥ 90 |
| `evaluate_npa_state(account, dpd)` | Apply sticky NPA rule |
| `apply_delinquency_state(account_id, as_of_date, db)` | Update account with DPD/NPA state |
| `calculate_delinquency_metrics(account_id, as_of_date, db)` | Full breakdown |
| `create_delinquency_snapshot(account_id, as_of_date, db)` | Daily snapshot |
| `run_daily_delinquency_batch(as_of_date, db)` | Batch for all accounts |
| `get_bucket_distribution(db)` | Portfolio-wide distribution |
| `get_delinquency_trend(account_id, days, db)` | Historical trend |

### Model: DelinquencySnapshot

Fields: `loan_account_id`, `snapshot_date`, `dpd`, `bucket`, `is_npa`, `npa_date`, `npa_category`, `overdue_principal`, `overdue_interest`, `overdue_fees`, `total_overdue`, `principal_outstanding`, `missed_installments`, `oldest_due_date`

---

## 13. Loan Restructuring

### Service: `services/restructure.py`

**Restructure Types**:

| Type | Description | Impact |
|---|---|---|
| `rate_reduction` | Lower interest rate | New EMI, same tenure |
| `tenure_extension` | Extend repayment period | New (lower) EMI |
| `principal_haircut` | Waive portion of principal | Reduced outstanding |
| `emi_rescheduling` | Custom EMI adjustment | Flexible |
| `combination` | Multiple restructure actions | Combined impact |

**Impact Analysis**: Before applying restructure, calculates new EMI, new tenure, total interest change, monthly savings.

**ECL Impact**: Restructured loans auto-transition to ECL Stage 2 (Significant Increase in Credit Risk).

### Model: LoanRestructure

Fields: `loan_account_id`, `restructure_date`, `restructure_type`, `original_principal/rate/tenure/emi`, `new_principal/rate/tenure/emi`, `principal_waived`, `interest_waived`, `fees_waived`, `requested_by`, `approved_by`, `approval_date`, `reason`, `status` (pending/approved/rejected/applied)

---

## 14. Prepayment & Foreclosure

### Service: `services/prepayment.py`

**Prepayment Options**:

| Option | Description | Result |
|---|---|---|
| `reduce_emi` | Keep original tenure | Lower monthly payment |
| `reduce_tenure` | Keep original EMI | Faster loan payoff |
| `full_foreclosure` | Pay everything | Loan closed |

**Payoff Amount Calculation**:
```
payoff = principal_outstanding + accrued_interest + outstanding_fees + overdue_amount + prepayment_penalty
```

**Prepayment Penalty**: Configurable rate (e.g., 2% of prepaid amount), with optional waiver.

### Model: Prepayment

Fields: `loan_account_id`, `prepayment_date`, `prepayment_amount`, `penalty_rate`, `penalty_amount`, `penalty_waived`, `action_type` (reduce_emi/reduce_tenure/foreclosure), `old_outstanding`, `new_outstanding`, `old_emi`, `new_emi`, `old_tenure`, `new_tenure`, `is_foreclosure`, `status`

---

## 15. Loan Closure & Write-Off

### Service: `services/closure.py`

**Closure Types**:

| Type | Description |
|---|---|
| `normal` | Fully paid, no outstanding |
| `settlement` | OTS — One-Time Settlement at negotiated amount |
| `write_off` | Full, partial, or technical write-off |

### Write-Off Model: WriteOff

Fields: `loan_account_id`, `write_off_date`, `write_off_type` (full/partial/technical), `principal_written_off`, `interest_written_off`, `fees_written_off`, `penalties_written_off`, `total_written_off`, `dpd_at_write_off`, `npa_category_at_write_off`, `write_off_reason`, `approved_by`, `approval_date`, `recovery_status`, `assigned_to_agency`, `expected_recovery_rate`

### Write-Off Recovery Model: WriteOffRecovery

Fields: `write_off_id`, `recovery_date`, `principal_recovered`, `interest_recovered`, `fees_recovered`, `total_recovered`, `recovery_source` (borrower/guarantor/collateral/legal/agency), `agency_commission`, `net_recovery`, `recovery_reference`, `status`

**Lifecycle Orchestrator** (`services/lifecycle.py`): Coordinates restructure, prepayment, closure, and write-off operations with impact analysis using Python dataclasses.

---

## 16. LAP Collateral Management

### Service: `services/collateral.py`

**4 ORM Models** in `models/collateral.py`:

#### Collateral (Primary Model)

Links to `loan_applications` (required) and `loan_accounts` (optional, linked post-disbursement).

| Field Group | Fields |
|---|---|
| **Property** | `property_type` (residential/commercial/industrial/land/mixed_use), `property_sub_type` |
| **Address** | `address_line1`, `address_line2`, `city`, `state`, `pincode`, `district`, `taluka`, `village` |
| **Area** | `area_sqft`, `carpet_area_sqft`, `built_up_area_sqft`, `land_area_acres` |
| **Ownership** | `owner_name`, `co_owner`, `ownership_type` (freehold/leasehold/co_operative), `title_deed_number`, `registration_number`, `registration_date`, `survey_number`, `cts_number` |
| **Valuation Snapshot** | `market_value`, `distress_value`, `realizable_value`, `ltv_ratio`, `valuation_date`, `valuer_name` |
| **Legal** | `legal_status`, `encumbrance_status`, `cersai_registration_number`, `cersai_registration_date` |
| **Insurance Snapshot** | `insurance_policy_number`, `insurance_expiry_date`, `insured_value` |
| **Charge/Lien** | `charge_type` (first_charge/second_charge/pari_passu), `charge_creation_date`, `charge_id` |
| **Status** | `status` (pending/verified/approved/released), `is_primary_security`, `remarks` |

#### CollateralValuation

Fields: `collateral_id`, `valuation_date`, `valuer_name`, `valuer_agency`, `valuation_type` (initial/periodic/re_valuation/distress), `market_value`, `realizable_value`, `distress_value`, `forced_sale_value`, `ltv_at_valuation`, `report_reference`, `remarks`

#### CollateralInsurance

Fields: `collateral_id`, `policy_number`, `provider`, `insured_value`, `premium_amount`, `start_date`, `expiry_date`, `renewal_date`, `status` (active/expired/cancelled), `is_assigned_to_lender`

#### CollateralLegalVerification

Fields: `collateral_id`, `verification_type` (title_search/encumbrance_check/cersai_search/revenue_record/mutation_check), `verification_date`, `verified_by`, `verification_status` (pending/clear/issue_found/waived), `report_reference`, `findings`, `remarks`

**Key Service Functions**:

| Function | Description |
|---|---|
| `create_collateral(data, db)` | Create with all property details |
| `update_collateral(id, data, db)` | Partial update (PATCH) |
| `add_valuation(id, data, db)` | Adds valuation + auto-updates parent snapshot + recalculates LTV |
| `add_insurance(id, data, db)` | Adds insurance + auto-updates parent snapshot |
| `add_legal_verification(id, data, db)` | Adds verification + auto-updates legal_status |
| `calculate_ltv(id, db)` | `loan_outstanding / market_value * 100` |
| `link_collateral_to_account(id, account_id, db)` | Link after disbursement |
| `get_collateral_summary(id, db)` | Full summary with sub-records |
| `get_collaterals_for_application(application_id, db)` | List by application |

**LTV Calculation Logic**:
```python
loan_outstanding = account.principal_outstanding if account else (
    application.approved_amount or application.requested_amount
)
ltv = (loan_outstanding / market_value) * 100
```

**Auto-Status Logic for Legal Verification**:
- All verifications `clear` → `legal_status = "clear"`
- Any verification `issue_found` → `legal_status = "issue_found"`
- Otherwise → `legal_status = "pending"`

---

## 17. Document & Media Management

### Model: Document (`models/document.py`)

Documents can be linked to: borrower, application, loan account, or collateral.

| Field | Type | Description |
|---|---|---|
| `borrower_id` | FK (nullable) | Link to borrower |
| `application_id` | FK (nullable) | Link to application |
| `loan_account_id` | FK (nullable) | Link to account |
| `collateral_id` | FK (nullable) | Link to collateral |
| `document_type` | String | e.g., kyc, income_proof, property_doc |
| `file_name` | String | Original filename |
| `storage_path` | String | File system path |
| `media_type` | String(20) | `photo`, `video`, `document` |
| `section` | String(50) | `collateral_exterior`, `collateral_interior`, `site_visit`, `due_diligence`, `title_deed`, `valuation_report`, `legal_opinion` |
| `file_size_bytes` | Integer | File size |
| `mime_type` | String(100) | e.g., image/jpeg, video/mp4, application/pdf |
| `thumbnail_path` | String(500) | Thumbnail for photos/videos |
| `capture_latitude` | Numeric(10,7) | GPS latitude (geo-tagging) |
| `capture_longitude` | Numeric(10,7) | GPS longitude (geo-tagging) |
| `captured_at` | DateTime | When photo/video was taken |
| `captured_by` | String(200) | Who took it |
| `description` | String(1000) | Free-text description |

---

## 18. 5-Level LAP Approval Workflow

### Service: `services/lap_workflow.py`

**Workflow Stages**:

```
draft → branch_data_entry → branch_manager_review → regional_credit_review
  → central_credit_review → sanctioning_authority → approved → disbursement

At each review stage: can → referred_back (→ branch_data_entry) or → rejected
Final stages: disbursement, rejected
```

**Stage-to-Application Status Mapping**:

| Workflow Stage | LoanApplication.status |
|---|---|
| `draft` | draft |
| `branch_data_entry` | data_entry |
| `branch_manager_review` | under_review |
| `regional_credit_review` | under_review |
| `central_credit_review` | under_review |
| `sanctioning_authority` | under_review |
| `approved` | approved |
| `disbursement` | disbursed |
| `rejected` | rejected |
| `referred_back` | referred_back |

**Stage Requirements**:

| Stage | Required Documents |
|---|---|
| branch_data_entry | KYC docs, income proof, property documents |
| branch_manager_review | Collateral photos, site visit report |
| regional_credit_review | Valuation report, legal opinion |
| central_credit_review | All docs verified, credit assessment complete |
| sanctioning_authority | All prior approvals obtained |

**Key Functions**:

| Function | Description |
|---|---|
| `seed_lap_workflow_definition(db)` | Idempotent — creates LAP workflow definition if not exists |
| `start_lap_workflow(application_id, started_by, priority, sla_hours, db)` | Start workflow, set status to `draft` |
| `transition_lap_workflow(application_id, to_stage, transitioned_by, action, comments, db)` | Transition + auto-sync application status + set `decision_at` on terminal |
| `assign_lap_workflow(application_id, assigned_to, assigned_role, db)` | Assign to user/role |
| `get_lap_workflow_status(application_id, db)` | Current stage, assignment, history |

---

## 19. Workflow Engine

### Service: `services/workflow.py`

Generic, reusable workflow engine that powers LAP and can power any approval process.

**4 ORM Models**:

| Model | Purpose |
|---|---|
| **WorkflowDefinition** | Template: `code`, `name`, `stages_json`, `transitions_json`, `initial_stage`, `final_stages` |
| **WorkflowInstance** | Active workflow: `definition_id`, `entity_type`, `entity_id`, `current_stage`, `assigned_to`, `assigned_role`, `priority`, `is_active`, `sla_due_date` |
| **WorkflowTransition** | Audit trail: `instance_id`, `from_stage`, `to_stage`, `transitioned_by`, `action`, `comments`, `transitioned_at` |
| **WorkflowTask** | Tasks within stages: `instance_id`, `task_type`, `assigned_to`, `status`, `due_date` |

**Key Functions**:

| Function | Description |
|---|---|
| `create_workflow_definition(code, name, stages, transitions, initial, finals, db)` | Create definition |
| `start_workflow(definition_id, entity_type, entity_id, started_by, priority, sla_hours, db)` | Start instance |
| `transition_workflow(instance_id, to_stage, by, action, comments, db)` | Validate + transition |
| `assign_workflow(instance_id, assigned_to, assigned_role, db)` | Assign |
| `get_workflow_status(entity_type, entity_id, db)` | Get current status |

Features: SLA tracking, time-in-stage metrics, SLA breach detection batch.

---

## 20. Co-Lending & Partner Management

### Service: `services/co_lending.py`

**Partnership Types**:

| Type | Ratio | Description |
|---|---|---|
| Co-Lending | 80:20 | Standard NBFC-Bank arrangement |
| Co-Lending | 90:10 | Low capital NBFC |
| Direct Assignment | 100:0 | Lender funds 100%, originator services |
| Participation | Variable | Sale of existing loan participation |

**Key Functions**:

| Function | Description |
|---|---|
| `calculate_disbursement_split(principal, participations)` | Split principal by share_percent |
| `calculate_payment_split(payment, participations)` | Split collections by share_percent |
| `create_partner_ledger_entries(account_id, amount, type, db)` | Record in partner ledger |
| `get_partner_exposure(partner_id, db)` | Total exposure for a partner |

**Collection Split Example (80:20)**:
```
EMI Received: ₹22,000
  Servicer Fee Withheld: ₹85 (fee + GST)
  Excess Spread Withheld: ₹1,143
  Lender Principal (80%): ₹13,600
  Lender Interest (after excess): ₹2,857
  Net to Lender: ₹16,372
  Net to Originator: ₹5,628 (share + fee + spread)
```

### Models

**LoanPartner**: `partner_code`, `name`, `partner_type` (bank/nbfc/hfc/other), `registration_number`, `rbi_license_number`, `default_share_percent`, `default_yield_rate`, `provides_fldg`, `is_servicer`, `total_exposure_limit`, `bank_account_number`, `bank_ifsc`, `gst_number`, `pan_number`

**LoanParticipation**: `loan_account_id`, `partner_id`, `participation_type`, `share_percent`, `interest_rate`, `fee_share_percent`, `fldg_arrangement_id`, `servicer_arrangement_id`, `principal_disbursed`, `principal_outstanding`, `principal_collected`, `interest_collected`, `excess_spread_collected`, `write_off_amount`, `ecl_stage`, `ecl_provision`

---

## 21. FLDG — First Loss Default Guarantee

### Service: `services/fldg.py`

**FLDG Types**:

| Type | Description |
|---|---|
| `first_loss` | Originator's guarantee absorbs losses first |
| `second_loss` | Kicks in after lender's first loss threshold breached |

**FLDG Limit**: `effective_limit = min(percent_calculation, absolute_amount)`

**Utilization Triggers**: DPD threshold (default 90+), NPA classification, write-off

**Claim Calculation**: `principal * partner_share_percent + interest (if covered) + fees (if covered)`

**Key Functions**:

| Function | Description |
|---|---|
| `create_fldg_arrangement(data, db)` | Create arrangement between parties |
| `calculate_fldg_claim(loan_account_id, arrangement_id, db)` | Calculate claim amount |
| `submit_fldg_utilization(arrangement_id, loan_account_id, amounts, db)` | Submit utilization |
| `approve_fldg_utilization(utilization_id, approver, db)` | Approve claim |
| `record_fldg_recovery(utilization_id, amounts, source, db)` | Record recovery to pool |
| `check_top_up_required(arrangement_id, db)` | Check if balance < threshold |
| `get_fldg_summary(arrangement_id, db)` | Balance, utilized, recovered |

### Models

**FLDGArrangement**: `arrangement_code`, `originator_id`, `lender_id`, `fldg_type`, `fldg_percent`, `fldg_absolute_amount`, `effective_fldg_limit`, `first_loss_threshold`, `covers_principal/interest/fees`, `guarantee_form`, `cash_deposit_account/bank`, `bank_guarantee_number/expiry`, `current_fldg_balance`, `total_utilized`, `total_recovered`, `trigger_dpd`, `top_up_threshold_percent`, `status`

**FLDGUtilization**: `arrangement_id`, `loan_account_id`, `utilization_date`, `trigger_reason`, `principal/interest/fees_claimed`, `total_claimed`, `principal/interest/fees_approved`, `total_approved`, `dpd_at_utilization`, `fldg_balance_before/after`, `status` (pending/approved/rejected/settled/recovered)

**FLDGRecovery**: `utilization_id`, `recovery_date`, `principal/interest/total_recovered`, `amount_returned_to_fldg`, `recovery_source`

---

## 22. Settlement & Partner Ledger

### Service: `services/settlement.py`

### Models

**PartnerLedgerEntry**: `loan_account_id`, `partner_id`, `participation_id`, `entry_type` (disbursement/principal_collection/interest_collection/fee_collection/settlement/adjustment), `amount`, `running_balance`, `entry_date`, `reference`

**PartnerSettlement**: `partner_id`, `settlement_date`, `period_from`, `period_to`, `total_principal_collected`, `total_interest_collected`, `total_fees_collected`, `servicer_fee_deducted`, `excess_spread_deducted`, `tds_deducted`, `gst_collected`, `net_settlement_amount`, `status` (pending/in_process/completed), `settlement_reference`, `bank_reference`

**PartnerSettlementDetail**: `settlement_id`, `loan_account_id`, `principal_amount`, `interest_amount`, `fee_amount`

---

## 23. Selldown & Loan Transfers

### Service: `services/selldown.py`

**Key Functions**:

| Function | Description |
|---|---|
| `create_selldown_transaction(data, db)` | Full or partial loan transfer |
| `settle_selldown(transaction_id, db)` | Process settlement |
| `calculate_sale_yield(sale_price, remaining_cashflows)` | Implied YTM at sale price |
| `calculate_gain_loss(book_value, sale_price)` | Gain/Loss = sale_price - book_value |
| `create_collection_split(transaction_id, db)` | Post-selldown collection allocation |
| `get_portfolio_summary(buyer_id, db)` | Portfolio summary for buyer |

### Models

**SelldownBuyer**: `buyer_code`, `name`, `buyer_type` (arc/bank/nbfc/fund), `registration_number`, `contact_person`, `email`, `phone`

**SelldownTransaction**: `loan_account_id`, `buyer_id`, `transaction_date`, `settlement_date`, `transfer_type` (full/partial), `book_value`, `sale_price`, `gain_loss`, `sale_yield`, `buyer_share_percent`, `status`

**SelldownSettlement**: `transaction_id`, `settlement_date`, `amount`, `reference`, `status`

**SelldownCollectionSplit**: `transaction_id`, `loan_account_id`, `collection_date`, `total_collected`, `seller_share`, `buyer_share`

---

## 24. Investment Portfolio

### Service: `services/investment.py`

**Investment Types**:

| Type | Description | Coupon |
|---|---|---|
| NCD | Non-Convertible Debenture | Fixed/Floating, periodic |
| CP | Commercial Paper | Discount instrument, zero coupon |
| Bond | Corporate/Government Bond | Fixed, semi-annual/annual |
| G-Sec | Government Security | Fixed, semi-annual |

**Key Functions**:

| Function | Description |
|---|---|
| `create_investment(data, db)` | Purchase investment |
| `generate_coupon_schedule(investment_id, db)` | Generate coupon payment dates |
| `calculate_ytm(face_value, price, coupons, maturity)` | YTM via Newton-Raphson method |
| `mark_to_market(investment_id, market_price, date, db)` | MTM valuation |
| `accrue_investment_interest(investment_id, date, db)` | Daily coupon accrual |
| `record_transaction(investment_id, type, amount, db)` | Purchase/sale/redemption |
| `get_portfolio_summary(db)` | Portfolio-level aggregates |

### Models

**InvestmentIssuer**: `issuer_code`, `name`, `issuer_type` (corporate/government/psu/bank), `credit_rating`, `sector`, `country`

**InvestmentProduct**: `product_code`, `name`, `instrument_type` (ncd/cp/bond/gsec), `coupon_type` (fixed/floating/zero), `coupon_frequency`, `day_count_convention`, `listing_exchange`

**Investment**: `investment_code`, `product_id`, `issuer_id`, `face_value`, `purchase_price`, `purchase_date`, `maturity_date`, `coupon_rate`, `ytm_at_purchase`, `current_ytm`, `market_value`, `accrued_interest`, `status` (active/matured/sold/defaulted)

**InvestmentCouponSchedule**: `investment_id`, `coupon_number`, `coupon_date`, `coupon_amount`, `status`

**InvestmentAccrual**: `investment_id`, `accrual_date`, `accrued_amount`, `cumulative`

**InvestmentValuation**: `investment_id`, `valuation_date`, `market_price`, `market_value`, `unrealized_gain_loss`, `ytm_at_valuation`

**InvestmentTransaction**: `investment_id`, `transaction_type` (purchase/sale/redemption/coupon), `transaction_date`, `quantity`, `price`, `amount`, `yield_at_transaction`

---

## 25. Securitization

### Service: `services/securitization.py`

**Key Functions**:

| Function | Description |
|---|---|
| `create_pool(name, pool_type, cutoff_date, db)` | Create securitization pool |
| `add_loan_to_pool(pool_id, loan_account_id, participation_percent, db)` | Add loan to pool |
| `add_investment_to_pool(pool_id, investment_id, participation_percent, db)` | Add investment |
| `create_tranche(pool_id, name, tranche_class, coupon_rate, priority, db)` | Create tranche |
| `execute_waterfall(pool_id, cash_available, db)` | Cash flow priority: senior → mezzanine → equity |
| `add_investor(name, type, db)` | Register investor |
| `record_investor_cash_flow(investor_id, pool_id, flow_type, amount, db)` | Coupon, principal, prepayment |
| `get_pool_statistics(pool_id, db)` | Pool performance summary |

### Models

**SecuritizationPool**: `pool_code`, `name`, `pool_type` (abs/mbs/clo), `cutoff_date`, `total_principal`, `total_loans`, `weighted_avg_rate`, `weighted_avg_tenure`, `status`

**PoolLoan**: `pool_id`, `loan_account_id`, `participation_percent`, `original_balance`, `current_balance`

**PoolInvestment**: `pool_id`, `investment_id`, `participation_percent`

**Investor**: `investor_code`, `name`, `investor_type` (institutional/retail/fund/bank), `contact_email`

**InvestorCashFlow**: `investor_id`, `pool_id`, `flow_type` (coupon/principal/prepayment/loss), `flow_date`, `amount`, `status`

---

## 26. Servicer Income & Withholding

### Service: `services/servicer_income.py`

**Income Components**:

| Component | Calculation |
|---|---|
| Servicer Fee | `outstanding * rate * days / 365` |
| Excess Spread | `borrower_rate - lender_yield` (retained by originator) |
| Performance Fee | Bonus at >95% collection efficiency |
| GST | 18% on servicer fee |
| TDS | 10% on lender interest (withheld) |

### Models

**ServicerArrangement**: `partner_id`, `participation_id`, `servicer_fee_rate`, `excess_spread_rate`, `performance_fee_rate`, `performance_threshold`, `gst_rate`, `tds_rate`

**ServicerIncomeAccrual**: `arrangement_id`, `accrual_date`, `servicer_fee`, `excess_spread`, `performance_fee`, `gst_on_fee`

**ServicerIncomeDistribution**: `arrangement_id`, `period_from`, `period_to`, `total_servicer_fee`, `total_excess_spread`, `total_performance_fee`, `total_gst`, `net_distributable`

**ExcessSpreadTracking**: `arrangement_id`, `loan_account_id`, `period_date`, `borrower_rate`, `lender_yield`, `spread`, `principal_outstanding`, `spread_amount`

**WithholdingTracker**: `arrangement_id`, `period_date`, `interest_collected`, `tds_rate`, `tds_amount`, `gst_on_servicer_fee`, `net_to_lender`

---

## 27. IFRS 9 ECL — Expected Credit Loss

### Service: `services/ecl.py`

**ECL Staging**:

| Stage | Description | ECL Measurement | Typical DPD |
|---|---|---|---|
| Stage 1 | Performing | 12-month ECL | 0–30 |
| Stage 2 | Underperforming / SICR | Lifetime ECL | 31–90 |
| Stage 3 | Non-performing / NPA / Write-off | Lifetime ECL (100% PD) | 90+ |

**Stage Assignment Priority**: Write-off → NPA → DPD>90 → Restructure → DPD>30 → SICR flag → Stage 1

**ECL Formula**: `ECL = EAD * PD * LGD`

**Example**:
```
Stage 1: EAD=₹1,00,000 × PD=0.5% × LGD=65% = ₹325
Stage 3: EAD=₹1,00,000 × PD=100% × LGD=65% = ₹65,000
```

**Key Functions**:

| Function | Description |
|---|---|
| `assign_ecl_stage(account, dpd, db)` | Determine ECL stage |
| `calculate_ecl_provision(account, stage, config, db)` | Calculate provision amount |
| `run_monthly_ecl_batch(as_of_date, db)` | Month-end batch for all accounts |
| `create_ecl_configuration(product_type, pd_stage1/2/3, lgd, db)` | PD/LGD config |
| `get_stage_movement(from_date, to_date, db)` | Stage transitions (1→2, 2→3, 2→1, 3→2) |
| `get_portfolio_summary(as_of_date, db)` | Stage-wise exposure, provision, coverage |
| `process_ecl_upload(file_data, db)` | Bulk ECL data upload |

### Models

**ECLConfiguration**: `product_type`, `pd_stage_1` (12-month), `pd_stage_2` (lifetime), `pd_stage_3` (100%), `lgd`, `ead_method`, `is_active`

**ECLStaging**: `loan_account_id`, `staging_date`, `ecl_stage`, `previous_stage`, `dpd`, `is_npa`, `is_restructured`, `sicr_flag`, `reason`

**ECLProvision**: `loan_account_id`, `provision_date`, `ecl_stage`, `exposure_at_default`, `pd`, `lgd`, `ecl_amount`, `previous_provision`, `provision_charge`, `coverage_ratio`

**ECLMovement**: `from_stage`, `to_stage`, `movement_date`, `loan_count`, `exposure_amount`

**ECLPortfolioSummary**: `summary_date`, `stage`, `loan_count`, `total_exposure`, `total_provision`, `coverage_ratio`, `weighted_avg_pd`, `weighted_avg_lgd`

---

## 28. PAR Reporting

### Service: `services/par_report.py`

**Portfolio at Risk** reporting with 60+ variables per loan covering:
- **LOS PAR** (pre-disbursement): Application-level metrics, borrower details, product info
- **LMS PAR** (post-disbursement): Account performance, DPD, NPA, outstanding breakdown
- Co-lending split details, collateral information
- DPD bucket classification, missed installment counts

---

## 29. End-of-Day Batch Processing

### Service: `services/eod.py`

**Daily EOD Orchestration**:

```
Step 1: Daily Interest Accrual Batch
  → Accrue interest for all active loan accounts

Step 2: Daily Delinquency Snapshot
  → Calculate DPD for all accounts
  → Create delinquency snapshots
  → Apply NPA state transitions (sticky NPA rule)

Step 3: Generate Statistics
  → Accounts processed count
  → Delinquent account count
  → New NPA count
  → Error count and details
```

**Run**:
```bash
# From Python code:
from app.services.eod import run_eod_batch
stats = run_eod_batch(as_of_date=date.today(), db=session)
```

---

## 30. Collection Management

### Service: `services/collection.py`

**Case Lifecycle**:
```
open → in_progress → resolved → closed
                   → written_off
```

Cases auto-transition from `open` to `in_progress` on first action logged.

**Key Functions**:

| Function | Description |
|---|---|
| `open_collection_case(loan_account_id, assigned_to, assigned_queue, priority, db)` | Auto-generates COL-NNNNNN, captures DPD/overdue |
| `update_case_status(case_id, status, resolution_type, db)` | Validated transitions |
| `log_collection_action(case_id, action_type, performed_by, outcome, notes, next_action_date, db)` | Log action + update case dates |
| `record_promise_to_pay(case_id, promise_date, payment_due_date, promised_amount, db)` | Create PTP record |
| `update_promise_status(promise_id, actual_date, actual_amount, status, notes, db)` | Mark PTP kept/broken/partial |
| `get_case_details(case_id, db)` | Full case with actions, PTPs |
| `get_overdue_accounts(min_dpd, max_dpd, db)` | Query delinquent accounts |
| `get_collection_dashboard(db)` | Summary stats |
| `evaluate_escalation_rules(loan_account_id, db)` | Check triggers against account |

**Action Types**: call, sms, email, letter, visit, legal_notice
**Outcomes**: contacted, no_answer, promise_to_pay, refused, wrong_number

**PTP Lifecycle**: `pending → kept / broken / partial`

**Escalation Rule Triggers**:

| Trigger | Example |
|---|---|
| DPD threshold | Account DPD ≥ 90 |
| Bucket match | SMA-1, SMA-2, NPA |
| Amount threshold | Overdue ≥ ₹50,000 |

Actions: `assign_queue`, `send_sms`, `send_email`, `legal_notice`. Rules can be product-specific.

### Models

**CollectionCase**: `case_number` (COL-NNNNNN), `loan_account_id`, `status`, `priority`, `assigned_to`, `assigned_queue`, `dpd_at_open`, `overdue_amount_at_open`, `opened_date`, `last_action_date`, `next_action_date`, `resolution_date`, `resolution_type`

**CollectionAction**: `case_id`, `action_type`, `action_date`, `performed_by`, `outcome`, `notes`, `next_action_date`, `follow_up_required`

**PromiseToPay**: `case_id`, `promise_date`, `payment_due_date`, `promised_amount`, `actual_payment_date`, `actual_amount`, `status`, `notes`

**EscalationRule**: `name`, `trigger_dpd`, `trigger_bucket`, `trigger_amount`, `action_type`, `action_config` (JSON), `applies_to_product_id`, `is_active`, `priority`

---

## 31. Rules Engine

### Service: `services/rules_engine.py`

**Rule Types**:
- Eligibility rules (pre-approval)
- Approval rules (auto vs manual)
- Delinquency escalation rules

**Rule Execution**:
- Evaluate condition JSON against entity attributes
- Execute action (approve, reject, escalate, assign)
- Track execution results in `RuleExecutionLog`

### Models

**RuleSet**: `code`, `name`, `entity_type`, `is_active`, `version`

**DecisionRule**: `rule_set_id`, `name`, `condition_json`, `action_type`, `action_params`, `rule_order`, `stop_on_match`, `is_active`

**RuleExecutionLog**: `rule_id`, `entity_type`, `entity_id`, `result` (match/no_match/error), `action_taken`, `execution_time`, `executed_at`

---

## 32. KYC & Compliance

### Service: `services/kyc.py`

**KYC Document Types**: Aadhaar, PAN, passport, voter_id, driving_license, address_proof

**Verification Status**: pending → in_review → approved / rejected

### Models

**KYCVerification**: `borrower_id`, `verification_type`, `document_id`, `document_number`, `verification_status`, `verified_at`, `verified_by`, `match_score`, `external_reference`, `risk_flags`

**KYCRequirement**: `product_id`, `verification_type`, `is_mandatory`, `min_match_score`

**CreditBureauReport**: `borrower_id`, `bureau_name`, `report_date`, `credit_score`, `report_data` (JSON), `enquiry_count`, `active_accounts`, `overdue_accounts`

---

## 33. Supply Chain Finance

### Service: `services/supply_chain.py`

**Key Features**:
- Bill discounting workflows
- Supplier/buyer authentication
- Invoice factoring
- Invoice-linked financing
- Credit limit management

### Models

**Counterparty**: `counterparty_code`, `name`, `counterparty_type` (buyer/supplier/both), `gst_number`, `pan_number`, `credit_rating`, `credit_limit`, `is_verified`, `is_active`

**CreditLimit**: `counterparty_id`, `limit_type` (overall/product_specific), `sanctioned_limit`, `utilized_amount`, `available_amount`, `effective_date`, `expiry_date`, `status`

**Invoice**: `invoice_number`, `counterparty_id`, `invoice_date`, `due_date`, `amount`, `currency`, `discount_rate`, `discounted_amount`, `financing_status` (pending/approved/financed/settled/defaulted), `linked_loan_account_id`

---

## 34. Complete API Reference

### 34.1 System

| Method | Path | Description |
|---|---|---|
| GET | `/` | System info — `{"name": "LOS/LMS API", "status": "running"}` |
| GET | `/health` | Health check with DB connectivity |

### 34.2 Borrowers (`/borrowers`)

| Method | Path | Description |
|---|---|---|
| POST | `/borrowers` | Create borrower (first_name, last_name, email, phone, dob, kyc_status) |
| GET | `/borrowers` | List all borrowers (pagination: skip, limit) |
| GET | `/borrowers/{id}` | Get single borrower |
| PATCH | `/borrowers/{id}` | Update borrower fields |

### 34.3 Loan Products (`/loan-products`)

| Method | Path | Description |
|---|---|---|
| POST | `/loan-products` | Create product (code, name, rate_type, base_rate, schedule_type, etc.) |
| GET | `/loan-products` | List products |
| GET | `/loan-products/{id}` | Get single product |

### 34.4 Loan Applications (`/loan-applications`)

| Method | Path | Description |
|---|---|---|
| POST | `/loan-applications` | Create application |
| GET | `/loan-applications` | List applications (filter: status, borrower_id) |
| GET | `/loan-applications/{id}` | Get application detail |
| PATCH | `/loan-applications/{id}` | Update application |
| POST | `/{id}/workflow/start` | Start LAP 5-level approval workflow |
| POST | `/{id}/workflow/transition` | Transition to next workflow stage |
| GET | `/{id}/workflow/status` | Get current workflow stage and history |
| POST | `/{id}/workflow/assign` | Assign workflow to user/role |
| GET | `/{id}/lap-los-par` | Get LAP LOS PAR row (60+ variables) |
| POST | `/{id}/lap-los-par` | Get LAP LOS PAR with overrides |
| GET | `/lap-par/headers` | PAR report headers |
| GET | `/lap-par/demo-defaults` | PAR demo defaults |

### 34.5 Loan Accounts (`/loan-accounts`)

| Method | Path | Description |
|---|---|---|
| POST | `/loan-accounts` | Create account from approved application |
| GET | `/loan-accounts` | List accounts (filter: status, dpd range) |
| GET | `/loan-accounts/{id}` | Get account with schedule, payments |
| PATCH | `/loan-accounts/{id}` | Update account fields |

### 34.6 Loan Lifecycle (`/loan-lifecycle`)

| Method | Path | Description |
|---|---|---|
| POST | `/loan-lifecycle/restructure` | Submit restructure request |
| POST | `/loan-lifecycle/prepayment` | Process prepayment/foreclosure |
| POST | `/loan-lifecycle/closure` | Close loan (normal/OTS/write-off) |

### 34.7 Loan Partners (`/loan-partners`)

| Method | Path | Description |
|---|---|---|
| POST | `/loan-partners` | Create partner (bank/NBFC/HFC) |
| GET | `/loan-partners` | List partners |
| GET | `/loan-partners/{id}` | Get partner detail |

### 34.8 Loan Participations (`/loan-participations`)

| Method | Path | Description |
|---|---|---|
| POST | `/loan-participations` | Create co-lending participation |
| GET | `/loan-participations` | List participations |
| GET | `/loan-participations/{id}` | Get participation detail |

### 34.9 Collaterals (`/collaterals`)

| Method | Path | Description |
|---|---|---|
| POST | `/collaterals` | Create collateral with property details |
| GET | `/collaterals` | List (filter: application_id, loan_account_id) |
| GET | `/collaterals/{id}` | Get single collateral |
| PATCH | `/collaterals/{id}` | Update fields |
| POST | `/collaterals/{id}/valuations` | Add valuation (auto-updates parent + LTV) |
| GET | `/collaterals/{id}/valuations` | Valuation history |
| POST | `/collaterals/{id}/insurance` | Add insurance record |
| GET | `/collaterals/{id}/insurance` | Insurance records |
| POST | `/collaterals/{id}/legal-verifications` | Add legal verification |
| GET | `/collaterals/{id}/legal-verifications` | Verification list |
| GET | `/collaterals/{id}/ltv` | Calculate current LTV |
| POST | `/collaterals/{id}/link-account` | Link to loan account post-disbursement |
| GET | `/collaterals/{id}/summary` | Full summary with all sub-records |

### 34.10 Documents (`/documents`)

| Method | Path | Description |
|---|---|---|
| POST | `/documents` | Create document (supports collateral_id, media_type, section, geo-tags) |
| GET | `/documents` | List (filters: borrower_id, application_id, loan_account_id, collateral_id, media_type, section) |
| GET | `/documents/by-collateral/{collateral_id}` | All documents for a collateral |
| GET | `/documents/by-section/{section}` | Documents by section type |

### 34.11 Collections (`/collections`)

| Method | Path | Description |
|---|---|---|
| POST | `/collections/cases` | Open new collection case |
| GET | `/collections/cases` | List (filter: status, priority, assigned_to, loan_account_id) |
| GET | `/collections/cases/{id}` | Full case with actions, PTPs, loan & collateral info |
| PATCH | `/collections/cases/{id}` | Update status/assignment/resolution |
| POST | `/collections/cases/{id}/actions` | Log collection action |
| GET | `/collections/cases/{id}/actions` | List actions |
| POST | `/collections/cases/{id}/promise-to-pay` | Record PTP |
| GET | `/collections/cases/{id}/promise-to-pay` | List PTPs |
| PATCH | `/collections/promise-to-pay/{id}` | Update PTP status (kept/broken/partial) |
| GET | `/collections/overdue-accounts` | Query delinquent accounts for case allocation |
| GET | `/collections/dashboard` | Collection summary/stats |
| POST | `/collections/escalation-rules` | Create escalation rule |
| GET | `/collections/escalation-rules` | List rules |
| POST | `/collections/cases/{id}/evaluate-escalation` | Evaluate rules for a case |

### 34.12 Holiday Calendars (`/holiday-calendars`)

| Method | Path | Description |
|---|---|---|
| POST | `/holiday-calendars` | Create calendar (name, country, year) |
| GET | `/holiday-calendars` | List calendars |
| GET | `/holiday-calendars/{id}` | Get calendar with holidays |
| POST | `/holiday-calendars/{id}/holidays` | Add holiday (one_time or recurring) |
| GET | `/holiday-calendars/{id}/holidays` | List holidays |

### 34.13 Benchmark Rates (`/benchmark-rates`)

| Method | Path | Description |
|---|---|---|
| POST | `/benchmark-rates` | Create benchmark (rate_code, name, currency) |
| GET | `/benchmark-rates` | List benchmarks |
| GET | `/benchmark-rates/{id}` | Get benchmark with latest rate |
| POST | `/benchmark-rates/{id}/history` | Add rate history entry |
| GET | `/benchmark-rates/{id}/history` | Rate history |

---

## 35. Complete Data Model Reference

### Entity Relationship Diagram

```
Borrower
  └── LoanApplication (branch_id, branch_name, product_id → LoanProduct)
        ├── LoanAccount (50+ fields)
        │     ├── RepaymentSchedule (1:N — installment-level)
        │     ├── Payment → PaymentAllocation (per installment waterfall)
        │     ├── InterestAccrual (daily accrual records)
        │     ├── DelinquencySnapshot (daily DPD/NPA snapshots)
        │     ├── LoanRestructure, Prepayment, WriteOff → WriteOffRecovery
        │     ├── LoanParticipation → LoanPartner → PartnerLedgerEntry
        │     │     └── PartnerSettlement → PartnerSettlementDetail
        │     ├── FLDGArrangement → FLDGUtilization → FLDGRecovery
        │     ├── ServicerArrangement → ServicerIncomeAccrual, WithholdingTracker
        │     │     └── ServicerIncomeDistribution, ExcessSpreadTracking
        │     ├── SelldownTransaction → SelldownSettlement, SelldownCollectionSplit
        │     ├── ECLStaging → ECLProvision
        │     ├── CollectionCase → CollectionAction, PromiseToPay
        │     ├── Collateral (linked post-disbursement)
        │     └── Document (1:N)
        ├── Collateral (1:N — linked at application stage)
        │     ├── CollateralValuation (1:N)
        │     ├── CollateralInsurance (1:N)
        │     ├── CollateralLegalVerification (1:N)
        │     └── Document (1:N — photos, videos, reports)
        ├── Document (1:N — application-level docs)
        └── WorkflowInstance → WorkflowTransition, WorkflowTask

LoanProduct → ProductFee → FeeType
           → ScheduleConfiguration

SecuritizationPool
  ├── PoolLoan / PoolInvestment
  └── Investor → InvestorCashFlow

InvestmentIssuer → InvestmentProduct → Investment
                                        ├── InvestmentCouponSchedule
                                        ├── InvestmentAccrual
                                        ├── InvestmentValuation
                                        └── InvestmentTransaction

SelldownBuyer → SelldownTransaction → SelldownSettlement
                                     → SelldownCollectionSplit

ECLConfiguration (per product type)
ECLMovement (stage transitions)
ECLPortfolioSummary (month-end aggregates)
ECLUpload (bulk data processing)

EscalationRule (standalone, evaluated against LoanAccount)
HolidayCalendar → Holiday
BenchmarkRate → BenchmarkRateHistory
WorkflowDefinition → WorkflowInstance
RuleSet → DecisionRule → RuleExecutionLog
User, RolePermission
Counterparty → CreditLimit, Invoice
```

### Model Count by Category

| Category | Models | Count |
|---|---|---|
| Core Loan | Borrower, LoanProduct, LoanApplication, LoanAccount | 4 |
| Schedule & Payment | RepaymentSchedule, Payment, PaymentAllocation, ScheduleConfiguration | 4 |
| Fees | FeeType, ProductFee, FeeCharge | 3 |
| Calendar & Rates | HolidayCalendar, Holiday, BenchmarkRate, BenchmarkRateHistory, InterestAccrual | 5 |
| Delinquency & Collection | DelinquencySnapshot, CollectionCase, CollectionAction, PromiseToPay, EscalationRule | 5 |
| Lifecycle | LoanRestructure, Prepayment, WriteOff, WriteOffRecovery | 4 |
| Collateral | Collateral, CollateralValuation, CollateralInsurance, CollateralLegalVerification | 4 |
| Document | Document | 1 |
| Partners & Co-Lending | LoanPartner, LoanParticipation, PartnerLedgerEntry, PartnerSettlement, PartnerSettlementDetail | 5 |
| FLDG | FLDGArrangement, FLDGUtilization, FLDGRecovery | 3 |
| ECL | ECLConfiguration, ECLProvision, ECLStaging, ECLMovement, ECLPortfolioSummary, ECLUpload | 6 |
| Servicer Income | ServicerArrangement, ServicerIncomeAccrual, ServicerIncomeDistribution, ExcessSpreadTracking, WithholdingTracker | 5 |
| Investments | InvestmentIssuer, InvestmentProduct, Investment, InvestmentCouponSchedule, InvestmentAccrual, InvestmentValuation, InvestmentTransaction, InvestmentPortfolioSummary | 8 |
| Securitization | SecuritizationPool, PoolLoan, PoolInvestment, Investor, InvestorCashFlow | 5 |
| Selldown | SelldownBuyer, SelldownTransaction, SelldownSettlement, SelldownCollectionSplit, SelldownPortfolioSummary | 5 |
| Workflow | WorkflowDefinition, WorkflowInstance, WorkflowTask, WorkflowTransition | 4 |
| Rules | RuleSet, DecisionRule, RuleExecutionLog | 3 |
| User & KYC | User, RolePermission, KYCVerification, KYCRequirement, CreditBureauReport | 5 |
| Supply Chain | Counterparty, CreditLimit, Invoice | 3 |
| **Total** | | **82** |

---

## 36. Domain Rules Reference

| Rule | Formula / Definition |
|---|---|
| **EMI** | `P * r * (1+r)^n / ((1+r)^n - 1)` where r = monthly rate, n = months |
| **Payment Waterfall** | Fees → Interest → Principal (strict order, per installment due date, oldest first) |
| **DPD** | `(as_of_date - oldest_unpaid_due_date).days` |
| **NPA** | DPD ≥ 90 days; sticky until DPD = 0 (RBI rule) |
| **NPA Aging** | Substandard (<1 year), Doubtful (1–3 years), Loss (3+ years) |
| **ECL** | `EAD * PD * LGD`; Stage 1 = 12-month, Stage 2/3 = lifetime |
| **LTV** | `loan_outstanding / market_value * 100` |
| **Co-lending Split** | By `LoanParticipation.share_percent` |
| **Selldown Gain/Loss** | `sale_price - book_value` |
| **YTM** | Solved iteratively via Newton-Raphson method |
| **FLDG Claim** | `principal * partner_share + interest + fees` (if covered) |
| **Effective Rate** | `max(floor, min(cap, benchmark + spread))` |
| **30/360 Convention** | Assumes 30-day months, 360-day year |
| **ACT/365** | Actual calendar days / 365 (Indian standard) |
| **ACT/360** | Actual calendar days / 360 (money market) |
| **ACT/ACT** | Actual days / actual year (365 or 366) — ISDA |

---

## 37. Testing

### Test Structure

Tests are split across two directories:

| Directory | Test Files | Tests | Coverage Area |
|---|---|---|---|
| `tests/` (root) | 13 files | 269 | Foundation, schedules, fees, accrual, LAP features |
| `backend/tests/` | 9 files | 184 | Lifecycle, rules, workflow, institutional, risk |
| **Total** | **22 files** | **453** | **Full system coverage** |

### Test Breakdown by File

| File | Tests | Module |
|---|---|---|
| `tests/test_frequency.py` | 44 | Payment frequency calculations |
| `tests/test_day_count.py` | 41 | Day-count conventions (30/360, ACT/365, ACT/360, ACT/ACT) |
| `tests/test_calendar.py` | 38 | Business day adjustments, holidays |
| `tests/test_collection_api.py` | 22 | Collection case management, PTP, escalation |
| `tests/test_floating_rate.py` | 21 | Floating rate management, rate resets |
| `tests/test_schedule_enhanced.py` | 21 | Enhanced schedule generation |
| `tests/test_collateral.py` | 20 | Collateral CRUD, LTV, valuations, legal verification |
| `tests/test_lap_workflow.py` | 20 | LAP 5-level approval workflow |
| `tests/test_fees.py` | 17 | Fee calculations and waivers |
| `tests/test_advanced_schedule.py` | 14 | Step-up, balloon, moratorium schedules |
| `tests/test_accrual.py` | 9 | Daily interest accrual |
| `tests/test_schedule.py` | 1 | Basic EMI schedule |
| `tests/test_health.py` | 1 | API health endpoint |
| `backend/tests/test_ecl.py` | 29 | ECL staging, provisions, portfolio summary |
| `backend/tests/test_lifecycle.py` | 26 | Restructure, prepayment, closure, write-off |
| `backend/tests/test_servicer_income.py` | 25 | Servicer fees, excess spread, withholding |
| `backend/tests/test_rules_engine.py` | 24 | Rule evaluation, execution |
| `backend/tests/test_fldg.py` | 21 | FLDG arrangement, utilization, recovery |
| `backend/tests/test_securitization.py` | 20 | Pool management, waterfall, investor cash flows |
| `backend/tests/test_workflow.py` | 18 | Generic workflow engine |
| `backend/tests/test_supply_chain.py` | 16 | Supply chain finance |
| `backend/tests/test_delinquency_par.py` | 5 | Delinquency snapshots, PAR reporting |

### Running Tests

```bash
# From project root (NOT backend/)
cd "LOS LMS"

# Run all 453 tests
python3 -m pytest

# Verbose output
python3 -m pytest -v

# Short summary
python3 -m pytest --tb=short -q

# Single file
python3 -m pytest tests/test_schedule.py

# Single test
python3 -m pytest tests/test_schedule.py::test_generate_emi_schedule

# By keyword
python3 -m pytest -k "ecl"

# Specific backend tests
python3 -m pytest backend/tests/test_ecl.py -v
```

### Test Patterns

Tests use `MagicMock` for database sessions and `SimpleNamespace` for model objects — no real database or fixtures needed:

```python
from unittest.mock import MagicMock
from types import SimpleNamespace

def test_example():
    db = MagicMock()
    account = SimpleNamespace(id=1, dpd=45, principal_outstanding=500000.0)
    db.query.return_value.filter.return_value.first.return_value = account

    result = some_service_function(account_id=1, db=db)
    assert result == expected
```

---

## 38. Demo Seed Data

The seed data creates a realistic demo environment covering all modules.

### Running Seed Data

```bash
cd backend

# Fresh seed (delete existing DB first)
rm -f los_lms.db
python3 -m app.db.init_db
python3 -m app.db.seed_data
```

### Seed Data Details

**Borrowers** (10 total):
- Rajesh Sharma, Priya Patel, Amit Verma, Sunita Gupta, Vikram Singh (base)
- Meera Reddy, Arjun Nair, Kavita Deshmukh, Suresh Iyer, Anita Joshi (LAP)

**Loan Products** (6):
- HOME-001: Home Loan (fixed, 8.5%, 60–360 months)
- PL-001: Personal Loan (fixed, 12%, 6–60 months)
- BL-001: Business Loan (fixed, 10%, 12–120 months)
- VL-001: Vehicle Loan (fixed, 9%, 12–84 months)
- GL-001: Gold Loan (fixed, 7.5%, 3–36 months)
- LAP-001: Loan Against Property (floating, 9.75%, 36–180 months)

**LAP Applications** (4):
- Application 6: Meera Reddy — Disbursed, 0 DPD (current)
- Application 7: Arjun Nair — Under review (regional_credit_review stage)
- Application 8: Kavita Deshmukh — Disbursed, 45 DPD (SMA-1)
- Application 9: Suresh Iyer — Disbursed, 95 DPD (NPA)

**Collaterals** (4):
- Mumbai 3BHK Flat (residential, ₹1.85 Cr market value)
- Gurgaon Commercial Office (commercial, ₹3.5 Cr)
- Pune Row Bungalow (residential, ₹2.1 Cr)
- Chennai Commercial Shop (commercial, ₹95 Lakh)

**Collection Cases** (2):
- Case COL-000001: SMA-1 account, 3 actions, pending PTP
- Case COL-000002: NPA account, 4 actions (including SARFAESI notice), broken PTP

**Escalation Rules** (5):
- SMA-0 SMS Alert (DPD ≥ 1)
- SMA-1 Call Assignment (DPD ≥ 31)
- SMA-2 Manager Escalation (DPD ≥ 61)
- NPA Legal Escalation (DPD ≥ 90)
- High Amount Alert (overdue ≥ ₹1,00,000)

**Benchmark Rates** (3):
- REPO: 6.50% (with 3 historical values)
- MCLR_1Y: 8.50% (with 3 historical values)
- TBILL_91: 6.75% (with 3 historical values)

**Other Data**: Holiday calendar (India, 11 holidays), ECL configurations (general + LAP), FLDG arrangement (SBI-Bajaj), investment issuers/products/investments, selldown buyers, loan partners and participations.

---

## 39. Deployment

### Development (SQLite)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python3 -m app.db.init_db
python3 -m app.db.seed_data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production (PostgreSQL + Docker)

```bash
# Start PostgreSQL
docker compose up -d

# Configure
echo "DATABASE_URL=postgresql+psycopg2://los:los@localhost:5432/los_lms" > backend/.env

# Initialize
cd backend
python3 -m app.db.init_db
python3 -m app.db.seed_data    # Optional — demo data

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API Documentation

Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key URLs for Demo

| URL | What to Try |
|---|---|
| `/docs` | Interactive API documentation |
| `/borrowers` | List all 10 borrowers |
| `/loan-products` | List all 6 loan products |
| `/loan-applications` | List all 9 applications |
| `/loan-accounts` | List all 6 accounts |
| `/collaterals` | List all 4 collaterals |
| `/collaterals/1/summary` | Full collateral summary with valuations |
| `/collaterals/1/ltv` | Calculate LTV |
| `/collections/dashboard` | Collection summary stats |
| `/collections/cases` | List collection cases |
| `/health` | System health check |

---

*End of documentation. 82 models, 31 services, 14 routers, 453 tests, 21,300+ lines of code.*
