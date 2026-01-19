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
8. [Selldown Module](#8-selldown-module)
9. [Investment Module (NCDs, CPs, Bonds)](#9-investment-module-ncds-cps-bonds)
10. [Data Models](#10-data-models)
11. [Business Logic & Services](#11-business-logic--services)
12. [API Reference](#12-api-reference)
13. [Financial Calculations](#13-financial-calculations)
14. [Security & Compliance](#14-security--compliance)
15. [Deployment Guide](#15-deployment-guide)
16. [Testing Strategy](#16-testing-strategy)

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

## 8. Selldown Module

### 8.1 Overview

The Selldown module enables sale/transfer of loans or investments to third parties during their tenure, supporting both full and partial selldowns.

### 8.2 Selldown Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Full Selldown** | 100% of position sold | Portfolio cleanup, regulatory compliance |
| **Partial Selldown** | Portion of position sold | Risk distribution, capital release |
| **Assignment** | Direct sale with transfer of ownership | Secondary market transactions |
| **Participation Sale** | Sale of participation in existing loan | Co-lending exit |

### 8.3 Selldown Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Initiate     │────►│     Approve     │────►│     Settle      │
│   Transaction   │     │   Transaction   │     │   Transaction   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
  - Identify asset        - Review terms         - Transfer funds
  - Calculate price       - Verify buyer         - Update records
  - Compute gain/loss     - Check limits         - Update exposure
```

### 8.4 Key Data Models

```python
class SelldownTransaction:
    transaction_code: str
    transaction_type: str          # full_selldown, partial_selldown
    asset_type: str                # loan, investment
    loan_account_id: int           # For loan selldowns
    investment_id: int             # For investment selldowns
    buyer_id: int

    # Sale details
    selldown_percent: Decimal      # 100 for full, <100 for partial
    selldown_principal: Decimal
    sale_price: Decimal
    price_percent: Decimal         # % of book value

    # Gain/Loss
    book_value: Decimal
    gain_loss: Decimal
    gain_loss_percent: Decimal

    # Yield analysis
    original_yield: Decimal
    sale_yield: Decimal
    yield_spread: Decimal

    # Post-sale servicing
    servicing_retained: bool
    servicer_fee_rate: Decimal

    # Status
    status: str                    # initiated, approved, settled
```

### 8.5 Pricing & Valuation

```
Sale Price Determination:
┌────────────────────────────────────────┐
│ Price % = Sale Price / Book Value × 100│
├────────────────────────────────────────┤
│ Premium: Price % > 100 (e.g., 102%)    │
│ Par: Price % = 100                      │
│ Discount: Price % < 100 (e.g., 98%)    │
└────────────────────────────────────────┘

Gain/Loss Calculation:
  Gain/Loss = Sale Price - Book Value
  Book Value = Outstanding Principal + Accrued Interest
```

### 8.6 Post-Selldown Servicing

When servicing is retained:
```
Collection Received: ₹22,000
           │
           ▼
┌─────────────────────────────────────────┐
│ Step 1: Split by selldown percentage    │
│   Buyer Share (80%): ₹17,600            │
│   Seller Retained (20%): ₹4,400         │
├─────────────────────────────────────────┤
│ Step 2: Deduct servicer fee from buyer  │
│   Servicer Fee: ₹50                     │
│   GST on Fee: ₹9                        │
├─────────────────────────────────────────┤
│ Step 3: Net to buyer                    │
│   Net Remittance: ₹17,541               │
└─────────────────────────────────────────┘
```

---

## 9. Investment Module (NCDs, CPs, Bonds)

### 9.1 Overview

The Investment module handles fixed income instruments including Non-Convertible Debentures (NCDs), Commercial Papers (CPs), Bonds, Government Securities, and other debt instruments.

### 9.2 Supported Instrument Types

| Type | Description | Typical Tenure |
|------|-------------|----------------|
| **NCD** | Non-Convertible Debentures | 1-10 years |
| **CP** | Commercial Paper | 7 days - 1 year |
| **Bond** | Corporate/PSU Bonds | 1-30 years |
| **G-Sec** | Government Securities | 1-40 years |
| **T-Bill** | Treasury Bills | 91/182/364 days |
| **CD** | Certificate of Deposit | 7 days - 1 year |
| **SDL** | State Development Loans | 1-15 years |

### 9.3 Coupon Types

| Type | Description |
|------|-------------|
| **Fixed** | Constant coupon rate throughout tenure |
| **Floating** | Linked to benchmark (MIBOR, T-Bill, etc.) + spread |
| **Zero Coupon** | No periodic coupon, issued at discount |
| **Step-Up** | Coupon rate increases at predefined intervals |
| **Step-Down** | Coupon rate decreases at predefined intervals |

### 9.4 Investment Lifecycle

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Purchase │───►│  Accrue  │───►│ Receive  │───►│ Maturity │
│          │    │ Interest │    │  Coupon  │    │  /Sale   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │
     ▼               ▼               ▼               ▼
- Book at cost   - Daily accrual - Record receipt- Redeem/Sell
- Generate       - Amortize      - TDS handling  - Gain/loss
  schedule         premium/disc  - Reset accrual - Close position
```

### 9.5 Key Data Models

```python
class Investment:
    investment_code: str
    isin: str                      # ISIN code
    security_name: str
    instrument_type: str           # ncd, cp, bond, gsec

    # Holdings
    face_value_per_unit: Decimal
    units_held: Decimal
    total_face_value: Decimal

    # Purchase details
    purchase_date: date
    purchase_price_per_unit: Decimal
    purchase_yield: Decimal        # YTM at purchase
    total_purchase_cost: Decimal

    # Coupon
    coupon_rate: Decimal
    coupon_type: str               # fixed, floating, zero_coupon
    coupon_frequency: str          # monthly, quarterly, semi_annual

    # For floating rate
    benchmark_rate_id: int
    spread_over_benchmark: Decimal
    current_effective_rate: Decimal

    # Valuation
    amortized_cost: Decimal
    accrued_interest: Decimal
    current_market_price: Decimal
    current_ytm: Decimal

    # Classification
    classification: str            # HTM, AFS, HFT

    # Maturity
    maturity_date: date
    remaining_tenure_days: int
```

### 9.6 Yield to Maturity (YTM) Calculation

```
        C × (1 - (1+r)^-n)     F
Price = ─────────────────── + ─────
              r               (1+r)^n

Where:
  C = Coupon payment per period
  r = YTM per period
  n = Number of periods
  F = Face value

Example (Semi-annual):
  Face Value: ₹1,000
  Coupon: 8% (₹40 semi-annual)
  Price: ₹980
  Tenure: 5 years (10 periods)
  YTM ≈ 8.35%
```

### 9.7 Interest Accrual

```
Daily Accrual (ACT/365):
  Interest = Face Value × Rate × Days / 365

Premium/Discount Amortization:
  Daily Amortization = (Purchase Price - Face Value) / Days to Maturity

Net Interest Income:
  = Accrued Interest - Premium Amortization (if premium)
  = Accrued Interest + Discount Accretion (if discount)
```

### 9.8 Mark-to-Market (MTM)

```
MTM Process:
┌─────────────────────────────────────────┐
│ 1. Get market price (exchange/dealer)   │
│ 2. Calculate market value               │
│    Market Value = Units × Market Price  │
│ 3. Compare to book value                │
│    Book Value = Amortized Cost + Accrued│
│ 4. Record MTM gain/loss                 │
│    MTM = Market Value - Book Value      │
└─────────────────────────────────────────┘

Classification Impact:
  HTM: No MTM impact on P&L
  AFS: MTM through OCI (equity)
  HFT: MTM through P&L
```

### 9.9 Portfolio Summary Example

```
Investment Portfolio as on 31-Jan-2024
┌────────────┬───────┬────────────┬────────────┬─────────┬─────────┐
│ Type       │ Count │ Face Value │ Book Value │ Mkt Val │ MTM G/L │
├────────────┼───────┼────────────┼────────────┼─────────┼─────────┤
│ NCDs       │ 25    │ ₹50 Cr     │ ₹51.2 Cr   │ ₹52 Cr  │ +₹0.8Cr │
│ CPs        │ 10    │ ₹20 Cr     │ ₹19.5 Cr   │ ₹19.6Cr │ +₹0.1Cr │
│ G-Secs     │ 5     │ ₹30 Cr     │ ₹31.5 Cr   │ ₹30.8Cr │ -₹0.7Cr │
├────────────┼───────┼────────────┼────────────┼─────────┼─────────┤
│ Total      │ 40    │ ₹100 Cr    │ ₹102.2 Cr  │ ₹102.4Cr│ +₹0.2Cr │
└────────────┴───────┴────────────┴────────────┴─────────┴─────────┘

Maturity Profile:
  0-30 days:   ₹15 Cr (15%)
  31-90 days:  ₹20 Cr (20%)
  91-365 days: ₹35 Cr (35%)
  1-3 years:   ₹20 Cr (20%)
  3+ years:    ₹10 Cr (10%)

Weighted Avg YTM: 8.25%
Weighted Avg Duration: 2.3 years
```

---

## 10. Data Models

### 10.1 Model Categories

| Category | Models |
|----------|--------|
| **Core** | Borrower, LoanApplication, LoanAccount, LoanProduct |
| **Schedule** | RepaymentSchedule, ScheduleConfiguration |
| **Payments** | Payment, PaymentAllocation |
| **Co-Lending** | LoanPartner, LoanParticipation, PartnerLedger, PartnerSettlement |
| **FLDG** | FLDGArrangement, FLDGUtilization, FLDGRecovery |
| **ECL** | ECLConfiguration, ECLStaging, ECLProvision, ECLMovement, ECLUpload |
| **Servicer Income** | ServicerArrangement, ServicerIncomeAccrual, ExcessSpreadTracking, WithholdingTracker |
| **Selldown** | SelldownBuyer, SelldownTransaction, SelldownSettlement, SelldownCollectionSplit |
| **Investment** | Investment, InvestmentProduct, InvestmentIssuer, InvestmentCouponSchedule, InvestmentAccrual, InvestmentValuation |
| **Collections** | CollectionCase, CollectionAction, PromiseToPay, DelinquencySnapshot |
| **Lifecycle** | LoanRestructure, Prepayment, WriteOff, WriteOffRecovery |
| **Workflow** | WorkflowDefinition, WorkflowInstance, WorkflowTask |
| **Rules** | RuleSet, DecisionRule, RuleExecutionLog |
| **SCF** | Counterparty, Invoice, CreditLimit |
| **Securitization** | SecuritizationPool, PoolLoan, Investor, PoolInvestment |

### 10.2 Entity Relationships

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

## 11. Business Logic & Services

### 11.1 Core Services

| Service | Purpose |
|---------|---------|
| `schedule.py` | Amortization schedule generation |
| `payments.py` | Payment processing and allocation |
| `interest.py` | Day-count conventions and interest calculation |
| `frequency.py` | Payment frequency management |
| `calendar.py` | Business day adjustments |
| `fees.py` | Fee calculation and charging |

### 11.2 Co-Lending Services

| Service | Purpose |
|---------|---------|
| `co_lending.py` | Payment splitting between partners |
| `settlement.py` | Partner settlement generation |
| `fldg.py` | FLDG utilization and recovery |
| `servicer_income.py` | Servicer fee and excess spread |

### 11.3 Risk & Compliance Services

| Service | Purpose |
|---------|---------|
| `ecl.py` | ECL staging and provision calculation |
| `delinquency.py` | DPD tracking and bucket assignment |
| `collections.py` | Collection case management |
| `escalation.py` | Escalation rule execution |

### 11.4 Lifecycle Services

| Service | Purpose |
|---------|---------|
| `restructure.py` | Loan restructuring |
| `prepayment.py` | Prepayment processing |
| `closure.py` | Loan closure and write-off |

### 11.5 Selldown Services

| Service | Purpose |
|---------|---------|
| `selldown.py` | Loan/investment selldown processing |
| - `initiate_loan_selldown()` | Create loan selldown transaction |
| - `initiate_investment_selldown()` | Create investment selldown transaction |
| - `approve_selldown()` | Approve selldown for settlement |
| - `settle_selldown()` | Settle and transfer assets |
| - `split_collection_for_selldown()` | Split collections post-selldown |

### 11.6 Investment Services

| Service | Purpose |
|---------|---------|
| `investment.py` | Fixed income investment management |
| - `create_investment()` | Create new investment (NCD, CP, Bond) |
| - `generate_coupon_schedule()` | Generate coupon payment schedule |
| - `accrue_interest()` | Daily interest accrual |
| - `receive_coupon()` | Record coupon receipt |
| - `mature_investment()` | Process maturity/redemption |
| - `mark_to_market()` | MTM valuation |
| - `update_floating_rate()` | Reset floating rate |
| - `calculate_ytm()` | Yield to maturity calculation |

---

## 12. API Reference

### 12.1 Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/borrowers` | CRUD | Borrower management |
| `/loan-products` | CRUD | Product configuration |
| `/loan-applications` | CRUD | Application management |
| `/loan-accounts` | CRUD | Account management |
| `/loan-accounts/{id}/schedule` | GET | Get repayment schedule |
| `/loan-accounts/{id}/payments` | POST | Record payment |

### 12.2 Co-Lending Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/loan-participations` | CRUD | Participation management |
| `/partner-settlements` | POST | Generate settlement |
| `/partner-settlements/{id}/approve` | POST | Approve settlement |

### 12.3 FLDG Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/fldg-arrangements` | CRUD | FLDG arrangement management |
| `/fldg-arrangements/{id}/summary` | GET | Utilization summary |
| `/fldg-utilizations` | POST | Trigger utilization |
| `/fldg-utilizations/{id}/approve` | POST | Approve utilization |
| `/fldg-recoveries` | POST | Record recovery |

### 12.4 ECL Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ecl-configurations` | CRUD | ECL config management |
| `/ecl-staging/{loan_id}` | GET | Get loan ECL stage |
| `/ecl-provisions/batch` | POST | Month-end batch |
| `/ecl-uploads` | POST | Upload external ECL |
| `/ecl-portfolio-summary` | GET | Portfolio summary |

### 12.5 Lifecycle Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/loan-lifecycle/restructure` | POST | Create restructure |
| `/loan-lifecycle/prepayment/calculate` | POST | Calculate prepayment |
| `/loan-lifecycle/prepayment/process` | POST | Process prepayment |
| `/loan-lifecycle/close` | POST | Close loan |
| `/loan-lifecycle/write-off` | POST | Write-off loan |

### 12.6 Selldown Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/selldown-buyers` | CRUD | Buyer management |
| `/selldown-transactions` | POST | Create selldown |
| `/selldown-transactions/{id}` | GET | Get transaction details |
| `/selldown-transactions/{id}/approve` | POST | Approve selldown |
| `/selldown-transactions/{id}/settle` | POST | Settle selldown |
| `/selldown-transactions/{id}/cancel` | POST | Cancel selldown |
| `/selldown-collection-splits` | POST | Record collection split |
| `/selldown-portfolio-summary` | GET | Buyer portfolio summary |

### 12.7 Investment Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/investment-issuers` | CRUD | Issuer management |
| `/investment-products` | CRUD | Product configuration |
| `/investments` | CRUD | Investment management |
| `/investments/{id}/schedule` | GET | Get coupon schedule |
| `/investments/{id}/accrue` | POST | Run interest accrual |
| `/investments/{id}/coupon` | POST | Record coupon receipt |
| `/investments/{id}/mature` | POST | Process maturity |
| `/investments/{id}/mtm` | POST | Mark-to-market |
| `/investments/{id}/selldown` | POST | Initiate selldown |
| `/investment-portfolio-summary` | GET | Portfolio summary |

---

## 13. Financial Calculations

### 13.1 EMI Formula

```
        P × r × (1+r)^n
EMI = ─────────────────
         (1+r)^n - 1

Where:
  P = Principal Amount
  r = Monthly Interest Rate (Annual Rate / 12 / 100)
  n = Tenure in Months
```

### 13.2 Day-Count Conventions

| Convention | Year Basis | Day Calculation |
|------------|------------|-----------------|
| 30/360 | 360 days | Each month = 30 days |
| ACT/365 | 365 days | Actual days |
| ACT/ACT | Actual | Actual days, actual year |
| ACT/360 | 360 days | Actual days |

### 13.3 Interest Calculation

```python
def calculate_interest(principal, rate, start_date, end_date, convention):
    year_fraction = get_year_fraction(start_date, end_date, convention)
    return principal * (rate / 100) * year_fraction
```

---

## 14. Security & Compliance

### 14.1 Access Control

- Role-based permissions (RBAC)
- User authentication support
- API key management

### 14.2 Data Protection

- Input validation (Pydantic)
- SQL injection prevention (ORM)
- Sensitive data encryption

### 14.3 Audit & Compliance

- Complete audit trail
- Rule execution logging
- Workflow transition history
- ECL provision history
- FLDG utilization records

### 14.4 Regulatory Compliance

- IFRS 9 / Ind AS 109 ECL staging
- RBI NPA classification
- Co-lending guidelines compliance
- FLDG disclosure requirements

---

## 15. Deployment Guide

### 15.1 Development Setup

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

### 15.2 Production Deployment

```bash
# Docker deployment
docker compose up -d

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 15.3 API Access

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 16. Testing Strategy

### 16.1 Test Distribution

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

### 16.2 Running Tests

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

## Appendix B: Detailed Module Statistics

> **Note:** Full statistics available in Excel format: `docs/LOS_LMS_Module_Statistics.xlsx`

### B.1 Overall System Statistics

| Metric | Value |
|--------|-------|
| **Total Python Files** | 96 |
| **Total Lines of Code** | 18,460+ |
| **Database Models** | 31 |
| **Business Services** | 24 |
| **API Routers** | 12 |
| **Pydantic Schemas** | 13 |
| **Test Files** | 8 |
| **Test Cases** | 179+ |

### B.2 Data Models Layer (3,677 lines | 31 files)

| Model File | Lines | Description |
|------------|-------|-------------|
| `ecl.py` | 399 | ECL staging & provisioning (IFRS 9/Ind AS 109) |
| `servicer_income.py` | 380 | Servicer fees, excess spread tracking |
| `securitization.py` | 265 | Pool, investor, PTC/DA structures |
| `fldg.py` | 244 | First Loss Default Guarantee arrangements |
| `supply_chain.py` | 209 | Counterparty, invoice, credit limits |
| `workflow.py` | 192 | Workflow definitions, stages, tasks |
| `collection.py` | 175 | Collection cases, actions, PTP |
| `kyc.py` | 160 | KYC verification, documents |
| `fee.py` | 150 | Fee types, charges, waivers |
| `partner_ledger.py` | 148 | Partner transactions, settlements |
| `rules.py` | 142 | Rule sets, decision rules |
| `write_off.py` | 116 | Write-off, recovery tracking |
| `loan_account.py` | 108 | Core loan account entity |
| `loan_participation.py` | 94 | Co-lending participations |
| `user.py` | 77 | User authentication model |
| `prepayment.py` | 72 | Prepayment records |
| `loan_partner.py` | 72 | Partner configuration |
| `restructure.py` | 70 | Loan restructuring records |
| `benchmark_rate.py` | 69 | Floating rate benchmarks |
| `holiday_calendar.py` | 65 | Business day calendars |
| `schedule_config.py` | 64 | Schedule configuration |
| `interest_accrual.py` | 57 | Interest accrual entries |
| `delinquency.py` | 55 | Delinquency snapshots |
| `repayment_schedule.py` | 27 | EMI schedule items |
| `loan_application.py` | 27 | Loan applications |
| `loan_product.py` | 26 | Product configuration |
| `document.py` | 24 | Document attachments |
| `payment_allocation.py` | 21 | Payment allocation records |
| `payment.py` | 19 | Payment transactions |
| `borrower.py` | 19 | Borrower entity |

### B.3 Business Services Layer (9,823 lines | 24 files)

| Service File | Lines | Key Functions |
|--------------|-------|---------------|
| `securitization.py` | 709 | Pool creation, cash flow distribution, investor reporting |
| `ecl.py` | 606 | Stage classification, PD/LGD calculation, provision computation |
| `closure.py` | 516 | Loan closure, settlement, foreclosure processing |
| `workflow.py` | 514 | State machine, task assignment, SLA tracking |
| `servicer_income.py` | 510 | Fee calculation, excess spread, income recognition |
| `supply_chain.py` | 492 | Invoice financing, credit limit management |
| `prepayment.py` | 451 | Partial/full prepayment, EMI/tenure reduction |
| `fees.py` | 446 | Fee engine, late fees, processing fees |
| `fldg.py` | 438 | FLDG utilization, claims, replenishment |
| `kyc.py` | 435 | Verification workflows, document validation |
| `rules_engine.py` | 426 | JSON rule evaluation, decision automation |
| `advanced_schedule.py` | 424 | Step-up/down, balloon, custom schedules |
| `restructure.py` | 404 | Rate/tenure modification, principal haircut |
| `accrual.py` | 380 | Daily interest accrual, posting |
| `co_lending.py` | 357 | Payment splitting, partner allocation |
| `calendar.py` | 355 | Business day adjustment, holiday handling |
| `schedule.py` | 345 | EMI/bullet/interest-only schedule generation |
| `delinquency.py` | 338 | DPD calculation, bucket classification |
| `floating_rate.py` | 320 | Benchmark tracking, rate resets |
| `settlement.py` | 310 | Partner settlement generation |
| `frequency.py` | 294 | Payment frequency calculations |
| `lifecycle.py` | 291 | Loan lifecycle state management |
| `interest.py` | 274 | Interest calculation engine |
| `payments.py` | 188 | Payment processing, waterfall allocation |

### B.4 API Layer (1,697 lines | 12 routers)

| Router File | Lines | Endpoints |
|-------------|-------|-----------|
| `loan_lifecycle.py` | 546 | Restructure, prepay, close, write-off APIs |
| `benchmark_rates.py` | 306 | Rate management, history tracking |
| `holiday_calendars.py` | 304 | Calendar CRUD, holiday management |
| `loan_accounts.py` | 185 | Account CRUD, schedule, payments |
| `loan_applications.py` | 83 | Application workflow APIs |
| `documents.py` | 71 | Document upload/download |
| `loan_participations.py` | 56 | Co-lending participation APIs |
| `loan_products.py` | 36 | Product configuration |
| `loan_partners.py` | 36 | Partner management |
| `borrowers.py` | 34 | Borrower CRUD |
| `health.py` | 8 | Health check endpoint |

### B.5 Test Suite (2,477 lines | 179+ test cases)

| Test File | Lines | Tests | Coverage Area |
|-----------|-------|-------|---------------|
| `test_lifecycle.py` | 502 | 26 | Restructure, prepayment, closure |
| `test_rules_engine.py` | 355 | 24 | All rule operators & logic |
| `test_ecl.py` | 336 | 29 | Stage classification, provisions |
| `test_servicer_income.py` | 292 | 25 | Fee calculations, income |
| `test_securitization.py` | 275 | 20 | Pool management, distributions |
| `test_workflow.py` | 263 | 18 | State transitions, tasks |
| `test_fldg.py` | 248 | 21 | Guarantee utilization |
| `test_supply_chain.py` | 206 | 16 | Invoice financing |

### B.6 Functional Module Summary

| Module | Models | Services | Lines | Description |
|--------|--------|----------|-------|-------------|
| **Core Lending** | 6 | 5 | 2,800+ | Accounts, schedules, payments, products |
| **Co-Lending & Partnership** | 3 | 3 | 1,500+ | Participation, settlement, partner ledger |
| **Collections** | 2 | 2 | 1,000+ | Delinquency tracking, case management |
| **Lifecycle Management** | 3 | 4 | 1,800+ | Restructure, prepayment, closure, write-off |
| **Underwriting** | 3 | 3 | 1,500+ | Rules engine, workflow, KYC verification |
| **Risk & Compliance** | 2 | 2 | 1,400+ | ECL staging, FLDG management |
| **Supply Chain Finance** | 1 | 1 | 700+ | Invoice financing, credit limits |
| **Securitization** | 1 | 1 | 970+ | Pools, investors, cash flow distribution |
| **Servicer Income** | 1 | 1 | 890+ | Fees, excess spread, income tracking |
| **Configuration** | 5 | 4 | 1,500+ | Products, rates, calendars, fees |

### B.7 Pydantic Schemas Layer (641 lines | 13 files)

| Schema File | Lines | Purpose |
|-------------|-------|---------|
| `benchmark_rate.py` | 108 | Rate request/response models |
| `holiday_calendar.py` | 90 | Calendar schemas |
| `loan_account.py` | 67 | Account DTOs |
| `interest_accrual.py` | 64 | Accrual schemas |
| `loan_application.py` | 40 | Application schemas |
| `loan_product.py` | 32 | Product schemas |
| `payment.py` | 27 | Payment schemas |
| `borrower.py` | 25 | Borrower schemas |
| `repayment_schedule.py` | 25 | Schedule schemas |
| `document.py` | 24 | Document schemas |
| `loan_participation.py` | 23 | Participation schemas |
| `loan_partner.py` | 21 | Partner schemas |

---

*Unified LOS/LMS - Enterprise Lending Made Simple*
