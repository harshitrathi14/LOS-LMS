# Servicer Fees & Income Module

## Overview

The Servicer Income module manages all fee and income calculations in co-lending arrangements, including servicer fees, excess interest spread, withholding mechanisms, and income distribution between parties.

---

## Income Components

### 1. Servicer Fee

Fee paid by lender to originator for servicing the loans:

```
Servicer Fee = Portfolio Outstanding × Rate × Days / 365

Example:
  Outstanding: ₹100 Cr
  Rate: 0.5% p.a.
  Period: 30 days

  Fee = ₹100 Cr × 0.5% × 30/365 = ₹41,096
```

### 2. Excess Interest Spread

Difference between borrower rate and lender yield:

```
Excess Spread = Borrower Rate - Lender Yield

Example:
  Borrower Rate: 14% p.a.
  Lender Yield: 10% p.a.
  Excess Spread: 4% p.a.

On ₹1 Lakh outstanding for 30 days:
  Excess = ₹1,00,000 × 4% × 30/365 = ₹329
```

### 3. Performance Fee

Bonus for exceeding collection targets:

```
If Collection Rate ≥ 95%:
  Performance Fee = Collections × 0.1%
```

---

## Data Model

### ServicerArrangement

```python
class ServicerArrangement:
    arrangement_code: str
    servicer_id: int   # Originator
    lender_id: int     # Funding partner

    # Servicer fee
    servicer_fee_rate: Decimal      # 0.5% p.a.
    servicer_fee_calculation: str   # outstanding_principal
    fee_frequency: str              # monthly, quarterly

    # Minimum fee
    min_servicer_fee_monthly: Decimal
    min_servicer_fee_annual: Decimal

    # Excess spread
    has_excess_spread: bool
    lender_yield_rate: Decimal          # 10%
    excess_spread_servicer_share: Decimal  # 100%
    excess_spread_cap_percent: Decimal

    # Withholding
    withhold_servicer_fee: bool
    withholding_method: str  # deduct_from_collections

    # Performance fee
    has_performance_fee: bool
    performance_threshold_collection_rate: Decimal  # 95%
    performance_fee_rate: Decimal  # 0.1%

    # SLA penalty
    sla_breach_penalty_rate: Decimal
```

### ServicerIncomeAccrual

```python
class ServicerIncomeAccrual:
    arrangement_id: int
    accrual_date: date
    period_start: date
    period_end: date
    is_month_end: bool

    # Portfolio
    portfolio_outstanding: Decimal
    total_loans: int
    active_loans: int

    # Collections
    principal_collected: Decimal
    interest_collected: Decimal
    fees_collected: Decimal
    total_collected: Decimal

    # Servicer fee
    servicer_fee_base: Decimal
    servicer_fee_rate_applied: Decimal
    servicer_fee_accrued: Decimal

    # Excess spread
    weighted_avg_borrower_rate: Decimal
    lender_yield_rate: Decimal
    excess_spread_amount: Decimal
    servicer_excess_spread_share: Decimal
    lender_excess_spread_share: Decimal

    # Performance
    collection_rate: Decimal
    performance_fee_earned: Decimal

    # SLA
    sla_penalty_amount: Decimal

    # Totals
    total_servicer_income: Decimal
    total_lender_income: Decimal

    # Tax
    gst_on_servicer_fee: Decimal  # 18%
    tds_on_interest: Decimal      # 10%

    # Net
    net_servicer_income: Decimal
    net_lender_income: Decimal
```

### WithholdingTracker

```python
class WithholdingTracker:
    arrangement_id: int
    collection_date: date
    payment_id: int
    loan_account_id: int

    # Collection breakdown
    total_collection: Decimal
    principal_collected: Decimal
    interest_collected: Decimal
    fees_collected: Decimal

    # Withholding
    servicer_fee_withheld: Decimal
    excess_spread_withheld: Decimal
    gst_withheld: Decimal
    total_withheld: Decimal

    # Net to lender
    net_to_lender: Decimal
    lender_principal_share: Decimal
    lender_interest_share: Decimal
    lender_fee_share: Decimal
```

---

## Income Flow

### Collection Waterfall

```
Collection Received: ₹22,000 (EMI)
           │
           ▼
┌─────────────────────────────────────────┐
│ Step 1: Determine Lender Share (80%)    │
│         Lender Collection = ₹17,600     │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ Step 2: Withhold Servicer Fee           │
│         Fee = ₹17,600 × 0.5% × 30/365   │
│         Fee = ₹72 + GST ₹13 = ₹85       │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ Step 3: Withhold Excess Spread          │
│         Interest Collected = ₹4,000     │
│         Excess Rate = 4% (of 14%)       │
│         Excess = ₹4,000 × 4/14 = ₹1,143 │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ Step 4: Net to Lender                   │
│         ₹17,600 - ₹85 - ₹1,143          │
│         = ₹16,372                       │
└─────────────────────────────────────────┘
```

### Monthly Income Summary

```
Servicer Income (Jan-2024):
┌────────────────────────────┬────────────┐
│ Servicer Fee               │ ₹4,10,000  │
│ Excess Spread              │ ₹3,29,000  │
│ Performance Fee            │ ₹98,000    │
│ Less: SLA Penalty          │ (₹0)       │
├────────────────────────────┼────────────┤
│ Gross Income               │ ₹8,37,000  │
│ GST Collected              │ ₹73,800    │
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

## Excess Spread Tracking

### Loan-Level Tracking

```python
ExcessSpreadTracking:
    loan_account_id: int
    participation_id: int

    tracking_date: date
    period_start: date
    period_end: date

    # Rates
    borrower_interest_rate: Decimal  # 14%
    lender_yield_rate: Decimal       # 10%
    excess_spread_rate: Decimal      # 4%

    # Amounts
    principal_outstanding: Decimal
    gross_excess_spread: Decimal
    servicer_share_amount: Decimal
    lender_share_amount: Decimal

    # Cumulative
    cumulative_excess_spread: Decimal
```

### Example Tracking

```
Loan: ACC-001
Outstanding: ₹5,00,000
Period: Jan-2024 (31 days)

Borrower Rate: 14% p.a.
Lender Yield: 10% p.a.
Excess Rate: 4% p.a.

Gross Excess = ₹5,00,000 × 4% × 31/365 = ₹1,699
Servicer Share (100%): ₹1,699
Lender Share (0%): ₹0
```

---

## Tax Implications

### GST on Servicer Fee

```
Servicer Fee: ₹50,000
GST Rate: 18%
GST Amount: ₹9,000

Invoice to Lender:
  Servicer Fee: ₹50,000
  GST: ₹9,000
  Total: ₹59,000
```

### TDS on Interest

```
Interest Income to Lender: ₹82,192
TDS Rate: 10%
TDS Deducted: ₹8,219

Net to Lender: ₹73,973
```

---

## Settlement Process

### Monthly Settlement

```
ServicerIncomeDistribution:
    arrangement_id: int
    distribution_date: date
    period_start: date
    period_end: date

    recipient_type: str  # servicer, lender
    recipient_partner_id: int

    # Components
    servicer_fee_amount: Decimal
    excess_spread_amount: Decimal
    performance_fee_amount: Decimal
    gross_amount: Decimal

    # Deductions
    gst_deducted: Decimal
    tds_deducted: Decimal
    sla_penalty_deducted: Decimal
    total_deductions: Decimal

    net_amount: Decimal

    # Payment
    payment_mode: str  # neft, rtgs
    payment_reference: str
    payment_date: date
    status: str  # pending, paid
```

### Settlement Flow

```
Month-End (31-Jan)
      │
      ▼
┌─────────────────────────────┐
│ Calculate accrued income    │
│ - Servicer fee              │
│ - Excess spread             │
│ - Performance fee           │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Reconcile with withholdings │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Generate settlement         │
│ - Invoice to lender (GST)   │
│ - Payment advice (TDS)      │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Execute payment             │
│ - Net servicer settlement   │
│ - Net lender settlement     │
└─────────────────────────────┘
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/servicer-arrangements` | POST | Create arrangement |
| `/servicer-arrangements/{id}` | GET | Get arrangement |
| `/servicer-income/accrue` | POST | Accrue income |
| `/servicer-income/withhold` | POST | Record withholding |
| `/servicer-income/distribute` | POST | Create distribution |
| `/excess-spread/{loan_id}` | GET | Get excess spread |
| `/excess-spread/track` | POST | Track excess spread |

---

## Reports

### Servicer Income Report
```
Period: Jan-2024
Arrangement: SVC-2024-001

Income Summary:
┌─────────────────┬────────────┬────────────┐
│ Component       │ Accrued    │ Realized   │
├─────────────────┼────────────┼────────────┤
│ Servicer Fee    │ ₹4,10,000  │ ₹4,00,000  │
│ Excess Spread   │ ₹3,29,000  │ ₹3,20,000  │
│ Performance Fee │ ₹98,000    │ ₹98,000    │
├─────────────────┼────────────┼────────────┤
│ Total           │ ₹8,37,000  │ ₹8,18,000  │
└─────────────────┴────────────┴────────────┘

Unrealized: ₹19,000 (due to shortfalls)
```

### Excess Spread Analysis
- Portfolio-level weighted average
- Loan-level tracking
- Trend analysis

### Withholding Report
- Collection-wise withholdings
- Reconciliation with settlements
- GST/TDS tracking

---

## Business Rules

### Servicer Fee Rules
1. Calculate on outstanding principal
2. Apply minimum fee if calculated fee is lower
3. Charge GST at 18%
4. Invoice monthly/quarterly as per arrangement

### Excess Spread Rules
1. Only applicable if borrower rate > lender yield
2. Share as per arrangement (typically 100% to servicer)
3. Apply cap if specified

### Withholding Rules
1. Withhold from each collection if enabled
2. Maintain tracker for reconciliation
3. Settle net amounts monthly

### Performance Fee Rules
1. Calculate collection rate (actual/expected)
2. Award fee only if threshold met
3. Calculate on actual collections
