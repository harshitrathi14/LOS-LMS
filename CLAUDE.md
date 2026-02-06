# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Start PostgreSQL (optional - defaults to SQLite)
docker compose up -d

# Setup (from project root)
cd backend
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv/Scripts/Activate.ps1     # Windows PowerShell
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env

# Initialize database schema
python -m app.db.init_db

# Run development server
uvicorn app.main:app --reload

# Run tests (from project root, NOT from backend/)
pytest
pytest tests/test_schedule.py
pytest tests/test_schedule.py::test_generate_emi_schedule
```

**Important**: `pytest.ini` sets `pythonpath = backend`, so tests must be run from the project root, not from `backend/`.

## Architecture

Single FastAPI backend with SQLAlchemy ORM. No frontend.

```
backend/app/
├── main.py              # FastAPI app, router registration
├── core/config.py       # pydantic-settings from .env (DATABASE_URL, APP_NAME, ENV, LOG_LEVEL)
├── db/
│   ├── base.py          # SQLAlchemy DeclarativeBase
│   ├── session.py       # Engine + SessionLocal factory (pool_pre_ping=True)
│   ├── init_db.py       # Base.metadata.create_all (schema creation)
│   └── seed_data.py     # Database seeding
├── models/              # ~33 SQLAlchemy ORM model files (SQLAlchemy 2.0 Mapped types)
├── schemas/             # Pydantic v2 request/response schemas
├── api/
│   ├── deps.py          # get_db() yields SessionLocal with try/finally close
│   └── routers/         # 12 router modules
└── services/            # ~28 business logic modules (pure functions, Session passed explicitly)
```

### Service Layer Organization

Services are organized in layers. Lower-level services are used by higher-level ones:

**Foundation** (pure calculation, no DB):
- `interest.py` — Day-count conventions (30/360, ACT/365, ACT/360, ACT/ACT), year fractions
- `frequency.py` — Payment frequency calculations (weekly → annual)
- `calendar.py` — Business day adjustments (following, modified_following, preceding)
- `floating_rate.py` — Benchmark rate lookups, effective rate with floor/cap

**Schedule Generation**:
- `schedule.py` — Core amortization: EMI, interest_only, bullet. Returns `list[ScheduleItem]` (TypedDict)
- `advanced_schedule.py` — Step-up, balloon, amortizing bullet schedules
- `fees.py` — Fee types, charge calculations, waiver logic

**Loan Lifecycle**:
- `payments.py` — Payment waterfall allocation (fees → interest → principal), DPD computation
- `accrual.py` — Daily interest accrual, cumulative tracking
- `delinquency.py` — DPD buckets, NPA classification, delinquency snapshots
- `restructure.py` — Rate changes, tenure extension, EMI recalculation
- `prepayment.py` — EMI reduction vs tenure reduction, penalty calculation
- `closure.py` — Settlement amounts, post-closure accounting
- `lifecycle.py` — Orchestrates restructure/prepayment/closure/write-off with impact analysis (dataclasses)

**Co-Lending & Partners**:
- `co_lending.py` — Partner share calculations, income distribution
- `settlement.py` — Receivable/payable tracking between partners
- `fldg.py` — First Loss Default Guarantee tracking

**Institutional**:
- `selldown.py` — Loan/investment transfers (full/partial), settlement, collection splitting
- `investment.py` — Fixed income (NCD, CP, Bond, G-Sec): coupon schedules, YTM (Newton-Raphson), MTM, accrual
- `securitization.py` — Pool management, tranche waterfalls, investor cash flows
- `servicer_income.py` — Servicer fees, excess spread, withholding

**Risk & Compliance**:
- `ecl.py` — IFRS 9 Expected Credit Loss: staging, scenario analysis, provisions
- `par_report.py` — Portfolio at Risk reporting
- `eod.py` — End-of-day batch orchestration

**Platform**:
- `workflow.py`, `rules_engine.py`, `kyc.py`, `supply_chain.py`

### Data Model

Core loan lifecycle chain: `Borrower` → `LoanApplication` → `LoanAccount` → `RepaymentSchedule` → `Payment` + `PaymentAllocation`

Other key entity groups:
- **Products**: `LoanProduct`, `InvestmentProduct`, `Fee`/`FeeType`/`ProductFee`
- **Co-lending**: `LoanPartner` + `LoanParticipation` (share_percent, differential rates) + `PartnerLedger`
- **Selldown**: `SelldownBuyer` → `SelldownTransaction` → `SelldownSettlement` + `SelldownCollectionSplit`
- **Investments**: `InvestmentIssuer` → `Investment` → `InvestmentCouponSchedule` + `InvestmentAccrual` + `InvestmentValuation`
- **Securitization**: `SecuritizationPool` + `PoolLoan`/`PoolInvestment` → `Investor` + `InvestorCashFlow`
- **Risk**: `DelinquencySnapshot`, `ECLConfiguration`/`ECLProvision`/`ECLStaging`, `InterestAccrual`

## Key Patterns

### Financial Precision
All monetary calculations use `Decimal` with `ROUND_HALF_UP`. Constants: `CENT = Decimal("0.01")`, `RATE_PRECISION = Decimal("0.0000000001")`. Convert via `_to_decimal(value)` helper (present in multiple services). Model fields use `Numeric(18, 2)` but are mapped as `float` — Decimal conversion happens in services.

### Service Functions Are Stateless
Services receive `db: Session` explicitly. No global state, no ORM side effects outside the function. This is deliberate for testability and composability.

### Router Pattern
Routers do simple CRUD directly (no service layer for basic operations). Complex operations call services. All use `Depends(get_db)` for session injection.

### Tests
Tests call service functions directly with constructed inputs (no DB fixtures needed for calculation tests). API tests use `fastapi.testclient.TestClient`. Test files are at project root `tests/`, not `backend/tests/`.

## Domain Rules

- **Payment waterfall**: fees → interest → principal (strict order, per installment due date)
- **DPD**: Days past due = `(as_of_date - oldest_unpaid_due_date).days`
- **NPA classification**: Based on DPD buckets (SMA-0: 1-30, SMA-1: 31-60, SMA-2: 61-90, NPA: 90+)
- **EMI formula**: `P * r * (1+r)^n / ((1+r)^n - 1)` where r = monthly rate
- **Co-lending splits**: `LoanParticipation.share_percent` determines principal/interest allocation per partner
- **Selldown gain/loss**: `sale_price - book_value`
- **YTM**: Solved iteratively using Newton-Raphson method
- **Day-count conventions**: 30/360 (bond), ACT/365 (fixed), ACT/360 (money market), ACT/ACT (ISDA)

## Configuration

Environment variables via `.env` (loaded by pydantic-settings):
- `DATABASE_URL`: Default `sqlite:///./los_lms.db`. For PostgreSQL: `postgresql://los:los@localhost:5432/los_lms`
- `APP_NAME`, `ENV`, `LOG_LEVEL`

Alembic is configured (`alembic.ini`, `migrations/`) but schema is primarily managed via `init_db.py` create_all.
