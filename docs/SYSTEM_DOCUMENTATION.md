# Unified Loan Origination and Loan Management System (LOS/LMS)

## Complete Technical Documentation

**Version:** 2.0
**Date:** January 2026
**Status:** Production Ready

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Core Modules](#3-core-modules)
4. [Co-Lending & Partnership](#4-co-lending--partnership)
5. [FLDG (First Loss Default Guarantee)](#5-fldg-first-loss-default-guarantee)
6. [ECL Staging & Provisions](#6-ecl-staging--provisions)
7. [Servicer Fees & Income](#7-servicer-fees--income)
8. [Data Models](#8-data-models)
9. [Business Logic & Services](#9-business-logic--services)
10. [API Reference](#10-api-reference)
11. [Financial Calculations](#11-financial-calculations)
12. [Security & Compliance](#12-security--compliance)
13. [Deployment Guide](#13-deployment-guide)
14. [Testing Strategy](#14-testing-strategy)

---

## 1. Executive Summary

### 1.1 Overview

The Unified LOS/LMS is a comprehensive lending platform that handles the complete loan lifecycle from origination to closure. Built with modern Python technologies, it supports multiple loan products including retail loans, commercial loans, co-lending arrangements, supply chain finance, and securitization (PTC/DA).

### 1.2 Key Capabilities

| Capability | Description |
|------------|-------------|
| **Multi-Product Support** | Retail, commercial, co-lending, SCF, securitization |
| **Flexible Scheduling** | EMI, bullet, interest-only, step-up/down, balloon |
| **Day-Count Conventions** | 30/360, ACT/365, ACT/ACT, ACT/360 |
| **Payment Frequencies** | Weekly, biweekly, monthly, quarterly, semiannual, annual |
| **Floating Rates** | Benchmark tracking with spread, floor, and cap |
| **Co-Lending** | 80:20, 90:10, 100:0 ratios with FLDG coverage |
| **FLDG** | First/Second Loss Default Guarantee management |
| **ECL Staging** | IFRS 9 / Ind AS 109 Stage 1, 2, 3 provisioning |
| **Servicer Income** | Fee calculation, excess spread, withholding |
| **Collections** | DPD tracking, case management, escalation rules |
| **Lifecycle Management** | Restructuring, prepayment, write-off, recovery |

### 1.3 Technology Stack

```
Backend Framework:    FastAPI (Python 3.12+)
ORM:                  SQLAlchemy 2.0
Database:             PostgreSQL / SQLite
Validation:           Pydantic v2
Testing:              pytest (386 tests)
API Documentation:    OpenAPI/Swagger (auto-generated)
```

### 1.4 System Statistics

| Metric | Value |
|--------|-------|
| **Total Files** | 120+ |
| **Lines of Code** | 22,000+ |
| **Database Models** | 65+ |
| **Services** | 25+ |
| **API Endpoints** | 60+ |
| **Test Cases** | 386 |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
│                    (FastAPI Application)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Routers     │    │   Services    │    │   Models      │
│ (API Layer)   │    │(Business Logic)│   │ (Data Layer)  │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌───────────────┐
                    │   Database    │
                    │  (PostgreSQL) │
                    └───────────────┘
```

### 2.2 Directory Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry
│   ├── core/
│   │   └── config.py           # Configuration management
│   ├── db/
│   │   ├── base.py             # SQLAlchemy Base
│   │   ├── session.py          # Database session factory
│   │   └── init_db.py          # Schema initialization
│   ├── models/                 # SQLAlchemy ORM models (65+ models)
│   │   ├── loan_account.py     # Core loan account with write-off/ECL flags
│   │   ├── loan_participation.py # Co-lending with FLDG linkage
│   │   ├── fldg.py             # FLDG arrangement, utilization, recovery
│   │   ├── ecl.py              # ECL staging, provisions, uploads
│   │   ├── servicer_income.py  # Servicer fees, excess spread
│   │   └── ...
│   ├── schemas/                # Pydantic request/response schemas
│   ├── api/
│   │   ├── deps.py             # Dependency injection
│   │   └── routers/            # API endpoint modules
│   └── services/               # Business logic
│       ├── schedule.py         # Amortization schedules
│       ├── payments.py         # Payment processing
│       ├── fldg.py             # FLDG management
│       ├── ecl.py              # ECL calculations
│       ├── servicer_income.py  # Servicer income
│       └── ...
├── tests/                      # pytest test suites
│   ├── test_fldg.py            # FLDG tests (21)
│   ├── test_ecl.py             # ECL tests (29)
│   ├── test_servicer_income.py # Servicer income tests (25)
│   └── ...
└── docs/                       # Documentation
```

---

## 3. Core Modules

### 3.1 Loan Origination

```
Application Flow:
┌──────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐
│ Borrower │───►│Application│───►│Underwriting│───►│Approval  │
│ Creation │    │ Capture  │    │  & KYC    │    │          │
└──────────┘    └──────────┘    └───────────┘    └──────────┘
                                                       │
                                                       ▼
┌──────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐
│  Active  │◄───│Schedule  │◄───│Disbursement│◄───│Agreement │
│  Loan    │    │Generation│    │           │    │          │
└──────────┘    └──────────┘    └───────────┘    └──────────┘
```

### 3.2 Loan Management

| Function | Description |
|----------|-------------|
| Schedule Generation | EMI, bullet, interest-only, step-up/down, balloon |
| Payment Processing | Waterfall allocation (fees → interest → principal) |
| Delinquency Tracking | DPD calculation, bucket assignment |
| Collections | Case management, PTP tracking, escalation |
| Restructuring | Rate reduction, tenure extension, haircut |
| Prepayment | Reduce EMI, reduce tenure, foreclosure |
| Write-off | Full write-off with recovery tracking |
| Closure | Normal, foreclosure, settlement, write-off |

### 3.3 Schedule Types

| Type | Description |
|------|-------------|
| **EMI** | Equal Monthly Installment |
| **Bullet** | Interest periodic, principal at maturity |
| **Interest-Only** | Interest payments only |
| **Step-Up** | Gradually increasing EMI |
| **Step-Down** | Gradually decreasing EMI |
| **Balloon** | Regular EMI with large final payment |
| **Moratorium** | Deferred payments at start |

---

## 4. Co-Lending & Partnership

### 4.1 Partnership Types

| Type | Ratio | Description |
|------|-------|-------------|
| **Co-Lending** | 80:20, 90:10 | Both parties fund the loan |
| **Direct Assignment** | 100:0 | Lender funds 100%, originator services |
| **Participation** | Variable | Sale of existing loan participation |

### 4.2 Collection Split Example (80:20)

```
EMI Received: ₹22,000
├── Principal: ₹17,000
│   ├── Lender (80%): ₹13,600
│   └── Originator (20%): ₹3,400
│
├── Interest: ₹5,000
│   ├── Lender Yield Interest
│   └── Excess Spread to Originator
│
└── Waterfall: Servicer Fee → Excess Spread → Lender Yield → Principal
```

### 4.3 LoanParticipation Model

```python
class LoanParticipation:
    loan_account_id: int
    partner_id: int
    participation_type: str      # co_lending, assignment, participation
    share_percent: Decimal       # 80.00, 90.00, 100.00
    interest_rate: Decimal       # Lender's yield rate
    is_fully_backed: bool        # True for 100:0

    # FLDG linkage
    fldg_arrangement_id: int
    fldg_covered: bool
    fldg_coverage_percent: Decimal

    # Tracking
    principal_disbursed: Decimal
    principal_outstanding: Decimal
    principal_collected: Decimal
    interest_collected: Decimal

    # Excess spread
    excess_spread_rate: Decimal
    cumulative_excess_spread: Decimal

    # Write-off tracking
    is_written_off: bool
    write_off_amount: Decimal
    fldg_utilized: Decimal
    net_write_off: Decimal       # After FLDG

    # ECL
    ecl_stage: int
    ecl_provision: Decimal
```

---

## 5. FLDG (First Loss Default Guarantee)

### 5.1 FLDG Types

| Type | Description |
|------|-------------|
| **First Loss** | Originator's guarantee absorbs losses first |
| **Second Loss** | Kicks in after first loss threshold is breached |

### 5.2 FLDG Flow

```
Loan Defaults (90+ DPD or Write-off)
           │
           ▼
┌─────────────────────┐
│ Check FLDG Coverage │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│ Calculate Claim     │────►│ Principal × Share % │
│ - Principal share   │     │ Interest × Share %  │
│ - Interest share    │     │ (if covered)        │
└──────────┬──────────┘     └─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Approve & Settle    │
│ Update FLDG Balance │
│ Record Utilization  │
└─────────────────────┘
```

### 5.3 FLDG Example

```
Portfolio: ₹100 Cr
FLDG: 5% = ₹5 Cr

Default Scenario (₹7 Cr):
├── FLDG Absorbs: ₹5 Cr (Max)
└── Lender Loss: ₹2 Cr

Recovery (₹3 Cr later):
├── Return to FLDG: ₹3 Cr (replenish)
└── FLDG Balance: ₹3 Cr restored
```

### 5.4 FLDGArrangement Model

```python
class FLDGArrangement:
    arrangement_code: str
    originator_id: int           # Provides FLDG
    lender_id: int               # Protected by FLDG
    fldg_type: str               # first_loss, second_loss

    # Limits
    fldg_percent: Decimal        # % of portfolio
    fldg_absolute_amount: Decimal
    effective_fldg_limit: Decimal
    first_loss_threshold: Decimal  # For second loss

    # Coverage
    covers_principal: bool
    covers_interest: bool
    covers_fees: bool

    # Guarantee form
    guarantee_form: str          # cash_deposit, bank_guarantee
    bank_guarantee_number: str
    bank_guarantee_expiry: date

    # Status
    current_fldg_balance: Decimal
    total_utilized: Decimal
    total_recovered: Decimal

    # Triggers
    trigger_dpd: int             # Usually 90
    trigger_on_write_off: bool
    trigger_on_npa: bool

    # Top-up
    requires_top_up: bool
    top_up_threshold_percent: Decimal
```

---

## 6. ECL Staging & Provisions

### 6.1 IFRS 9 / Ind AS 109 Stages

| Stage | Description | ECL Measurement | Typical DPD |
|-------|-------------|-----------------|-------------|
| **Stage 1** | Performing | 12-month ECL | 0-30 days |
| **Stage 2** | Underperforming (SICR) | Lifetime ECL | 31-90 days |
| **Stage 3** | Non-performing | Lifetime ECL | 90+ days |

### 6.2 ECL Calculation

```
ECL = EAD × PD × LGD

Where:
  EAD = Exposure at Default (Outstanding + Off-balance)
  PD  = Probability of Default (12-month or Lifetime)
  LGD = Loss Given Default (35% secured, 65% unsecured)
```

### 6.3 Stage Assignment Logic

```
┌─────────────────────────────────────────┐
│         Stage Assignment                │
├─────────────────────────────────────────┤
│ Written Off? ──────Yes──────► STAGE 3   │
│ Is NPA? ───────────Yes──────► STAGE 3   │
│ DPD > 90? ─────────Yes──────► STAGE 3   │
│ Restructured? ─────Yes──────► STAGE 2   │
│ DPD > 30? ─────────Yes──────► STAGE 2   │
│ SICR Triggered? ───Yes──────► STAGE 2   │
│ Otherwise ──────────────────► STAGE 1   │
└─────────────────────────────────────────┘
```

### 6.4 ECL Example

```
Stage 1 Loan:
  EAD = ₹1,00,000
  PD (12-month) = 0.5%
  LGD = 65%
  ECL = ₹1,00,000 × 0.5% × 65% = ₹325

Stage 3 Loan:
  EAD = ₹1,00,000
  PD = 100%
  LGD = 65%
  ECL = ₹1,00,000 × 100% × 65% = ₹65,000
```

### 6.5 Month-End Provision Summary

```
ECL Portfolio Summary as on 31-Jan-2024

┌──────────┬────────┬────────────┬────────────┬──────────┐
│ Stage    │ Loans  │ Exposure   │ Provision  │ Coverage │
├──────────┼────────┼────────────┼────────────┼──────────┤
│ Stage 1  │ 9,500  │ ₹950 Cr    │ ₹3.09 Cr   │ 0.33%    │
│ Stage 2  │ 400    │ ₹40 Cr     │ ₹2.60 Cr   │ 6.50%    │
│ Stage 3  │ 100    │ ₹10 Cr     │ ₹6.50 Cr   │ 65.00%   │
├──────────┼────────┼────────────┼────────────┼──────────┤
│ Total    │ 10,000 │ ₹1000 Cr   │ ₹12.19 Cr  │ 1.22%    │
└──────────┴────────┴────────────┴────────────┴──────────┘
```

### 6.6 LoanAccount ECL Fields

```python
# ECL Staging (in LoanAccount)
ecl_stage: int                   # 1, 2, or 3
ecl_stage_date: date
ecl_provision: Decimal
ecl_provision_date: date

# SICR flag
sicr_flag: bool
sicr_date: date

# Write-off flags
is_written_off: bool
write_off_date: date
write_off_amount: Decimal
write_off_reason: str

# NPA flags
is_npa: bool
npa_date: date
npa_category: str                # substandard, doubtful, loss

# Restructure flag
is_restructured: bool
```

---

## 7. Servicer Fees & Income

### 7.1 Income Components

| Component | Description |
|-----------|-------------|
| **Servicer Fee** | Portfolio Outstanding × Rate × Days / 365 |
| **Excess Spread** | Borrower Rate - Lender Yield |
| **Performance Fee** | Bonus for exceeding collection targets |

### 7.2 Servicer Fee Calculation

```
Servicer Fee = Portfolio Outstanding × Rate × Days / 365

Example:
  Outstanding: ₹100 Cr
  Rate: 0.5% p.a.
  Period: 30 days
  Fee = ₹100 Cr × 0.5% × 30/365 = ₹41,096
```

### 7.3 Excess Spread Calculation

```
Excess Spread Rate = Borrower Rate - Lender Yield

Example:
  Borrower Rate: 14% p.a.
  Lender Yield: 10% p.a.
  Excess Spread: 4% p.a.

On ₹1 Lakh outstanding for 30 days:
  Excess = ₹1,00,000 × 4% × 30/365 = ₹329
```

### 7.4 Withholding from Collections

```
Collection Received: ₹22,000 (EMI)
           │
           ▼
┌─────────────────────────────────────────┐
│ Step 1: Lender Share (80%) = ₹17,600   │
├─────────────────────────────────────────┤
│ Step 2: Withhold Servicer Fee = ₹85    │
│         (₹72 + GST ₹13)                │
├─────────────────────────────────────────┤
│ Step 3: Withhold Excess Spread = ₹1,143│
│         (Interest × Excess/Borrower)   │
├─────────────────────────────────────────┤
│ Step 4: Net to Lender = ₹16,372        │
└─────────────────────────────────────────┘
```

### 7.5 Monthly Income Summary

```
Servicer Income (Jan-2024):
┌────────────────────────────┬────────────┐
│ Servicer Fee               │ ₹4,10,000  │
│ Excess Spread              │ ₹3,29,000  │
│ Performance Fee            │ ₹98,000    │
│ Less: SLA Penalty          │ (₹0)       │
├────────────────────────────┼────────────┤
│ Gross Income               │ ₹8,37,000  │
│ GST Collected (18%)        │ ₹73,800    │
├────────────────────────────┼────────────┤
│ Total Invoice              │ ₹9,10,800  │
└────────────────────────────┴────────────┘

Lender Income (Jan-2024):
┌────────────────────────────┬────────────┐
│ Interest Income            │ ₹82,19,000 │
│ Less: TDS (10%)            │ (₹8,21,900)│
├────────────────────────────┼────────────┤
│ Net Interest Income        │ ₹73,97,100 │
└────────────────────────────┴────────────┘
```

---

## 8. Data Models

### 8.1 Model Categories

| Category | Models |
|----------|--------|
| **Core** | Borrower, LoanApplication, LoanAccount, LoanProduct |
| **Schedule** | RepaymentSchedule, ScheduleConfiguration |
| **Payments** | Payment, PaymentAllocation |
| **Co-Lending** | LoanPartner, LoanParticipation, PartnerLedger, PartnerSettlement |
| **FLDG** | FLDGArrangement, FLDGUtilization, FLDGRecovery |
| **ECL** | ECLConfiguration, ECLStaging, ECLProvision, ECLMovement, ECLUpload |
| **Servicer Income** | ServicerArrangement, ServicerIncomeAccrual, ExcessSpreadTracking, WithholdingTracker |
| **Collections** | CollectionCase, CollectionAction, PromiseToPay, DelinquencySnapshot |
| **Lifecycle** | LoanRestructure, Prepayment, WriteOff, WriteOffRecovery |
| **Workflow** | WorkflowDefinition, WorkflowInstance, WorkflowTask |
| **Rules** | RuleSet, DecisionRule, RuleExecutionLog |
| **SCF** | Counterparty, Invoice, CreditLimit |
| **Securitization** | SecuritizationPool, PoolLoan, Investor, PoolInvestment |

### 8.2 Entity Relationships

```
Borrower ──► LoanApplication ──► LoanAccount ──► RepaymentSchedule
                                      │
                ┌─────────────────────┼─────────────────────┐
                │                     │                     │
                ▼                     ▼                     ▼
         LoanParticipation      ECLStaging            WriteOff
                │                     │                     │
                ▼                     ▼                     ▼
         FLDGArrangement        ECLProvision       WriteOffRecovery
                │
                ▼
         ServicerArrangement
```

---

## 9. Business Logic & Services

### 9.1 Core Services

| Service | Purpose |
|---------|---------|
| `schedule.py` | Amortization schedule generation |
| `payments.py` | Payment processing and allocation |
| `interest.py` | Day-count conventions and interest calculation |
| `frequency.py` | Payment frequency management |
| `calendar.py` | Business day adjustments |
| `fees.py` | Fee calculation and charging |

### 9.2 Co-Lending Services

| Service | Purpose |
|---------|---------|
| `co_lending.py` | Payment splitting between partners |
| `settlement.py` | Partner settlement generation |
| `fldg.py` | FLDG utilization and recovery |
| `servicer_income.py` | Servicer fee and excess spread |

### 9.3 Risk & Compliance Services

| Service | Purpose |
|---------|---------|
| `ecl.py` | ECL staging and provision calculation |
| `delinquency.py` | DPD tracking and bucket assignment |
| `collections.py` | Collection case management |
| `escalation.py` | Escalation rule execution |

### 9.4 Lifecycle Services

| Service | Purpose |
|---------|---------|
| `restructure.py` | Loan restructuring |
| `prepayment.py` | Prepayment processing |
| `closure.py` | Loan closure and write-off |

---

## 10. API Reference

### 10.1 Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/borrowers` | CRUD | Borrower management |
| `/loan-products` | CRUD | Product configuration |
| `/loan-applications` | CRUD | Application management |
| `/loan-accounts` | CRUD | Account management |
| `/loan-accounts/{id}/schedule` | GET | Get repayment schedule |
| `/loan-accounts/{id}/payments` | POST | Record payment |

### 10.2 Co-Lending Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/loan-participations` | CRUD | Participation management |
| `/partner-settlements` | POST | Generate settlement |
| `/partner-settlements/{id}/approve` | POST | Approve settlement |

### 10.3 FLDG Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/fldg-arrangements` | CRUD | FLDG arrangement management |
| `/fldg-arrangements/{id}/summary` | GET | Utilization summary |
| `/fldg-utilizations` | POST | Trigger utilization |
| `/fldg-utilizations/{id}/approve` | POST | Approve utilization |
| `/fldg-recoveries` | POST | Record recovery |

### 10.4 ECL Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ecl-configurations` | CRUD | ECL config management |
| `/ecl-staging/{loan_id}` | GET | Get loan ECL stage |
| `/ecl-provisions/batch` | POST | Month-end batch |
| `/ecl-uploads` | POST | Upload external ECL |
| `/ecl-portfolio-summary` | GET | Portfolio summary |

### 10.5 Lifecycle Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/loan-lifecycle/restructure` | POST | Create restructure |
| `/loan-lifecycle/prepayment/calculate` | POST | Calculate prepayment |
| `/loan-lifecycle/prepayment/process` | POST | Process prepayment |
| `/loan-lifecycle/close` | POST | Close loan |
| `/loan-lifecycle/write-off` | POST | Write-off loan |

---

## 11. Financial Calculations

### 11.1 EMI Formula

```
        P × r × (1+r)^n
EMI = ─────────────────
         (1+r)^n - 1

Where:
  P = Principal Amount
  r = Monthly Interest Rate (Annual Rate / 12 / 100)
  n = Tenure in Months
```

### 11.2 Day-Count Conventions

| Convention | Year Basis | Day Calculation |
|------------|------------|-----------------|
| 30/360 | 360 days | Each month = 30 days |
| ACT/365 | 365 days | Actual days |
| ACT/ACT | Actual | Actual days, actual year |
| ACT/360 | 360 days | Actual days |

### 11.3 Interest Calculation

```python
def calculate_interest(principal, rate, start_date, end_date, convention):
    year_fraction = get_year_fraction(start_date, end_date, convention)
    return principal * (rate / 100) * year_fraction
```

---

## 12. Security & Compliance

### 12.1 Access Control

- Role-based permissions (RBAC)
- User authentication support
- API key management

### 12.2 Data Protection

- Input validation (Pydantic)
- SQL injection prevention (ORM)
- Sensitive data encryption

### 12.3 Audit & Compliance

- Complete audit trail
- Rule execution logging
- Workflow transition history
- ECL provision history
- FLDG utilization records

### 12.4 Regulatory Compliance

- IFRS 9 / Ind AS 109 ECL staging
- RBI NPA classification
- Co-lending guidelines compliance
- FLDG disclosure requirements

---

## 13. Deployment Guide

### 13.1 Development Setup

```bash
# Clone repository
git clone <repository>
cd los-lms/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit DATABASE_URL if using PostgreSQL

# Initialize database
python -m app.db.init_db

# Run development server
uvicorn app.main:app --reload
```

### 13.2 Production Deployment

```bash
# Docker deployment
docker compose up -d

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 13.3 API Access

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 14. Testing Strategy

### 14.1 Test Distribution

| Category | Tests | Coverage |
|----------|-------|----------|
| Day-Count Conventions | 41 | All 4 conventions |
| Payment Frequencies | 44 | All 6 frequencies |
| Business Day Calendar | 38 | Adjustments + holidays |
| Floating Rates | 21 | Benchmarks + resets |
| Advanced Schedules | 14 | Step-up/down, balloon |
| Lifecycle Operations | 26 | Restructure, prepay, close |
| Rules Engine | 24 | All operators |
| Workflow Engine | 18 | State machine |
| Supply Chain | 21 | Invoice financing |
| Securitization | 22 | Pool management |
| **FLDG** | 21 | Utilization, recovery |
| **ECL** | 29 | Staging, provisions |
| **Servicer Income** | 25 | Fees, excess spread |
| **Total** | **386** | **All modules** |

### 14.2 Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_fldg.py
pytest tests/test_ecl.py
pytest tests/test_servicer_income.py

# With coverage
pytest --cov=app --cov-report=html
```

---

## Appendix A: Business Segment Documentation

| Document | Description |
|----------|-------------|
| `CO_LENDING_PARTNERSHIP.md` | 80:20, 90:10, 100:0 arrangements |
| `FLDG_GUARANTEE.md` | First/Second Loss Default Guarantee |
| `ECL_STAGING_PROVISIONS.md` | IFRS 9 Stage 1, 2, 3 provisioning |
| `SERVICER_FEES_INCOME.md` | Fees, excess spread, withholding |

---

*Unified LOS/LMS - Enterprise Lending Made Simple*
