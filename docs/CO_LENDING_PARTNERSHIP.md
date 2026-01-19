# Co-Lending & Partnership Module

## Overview

The Co-Lending module supports various partnership arrangements between originators and lenders, enabling flexible funding structures while maintaining proper tracking of shares, collections, and settlements.

---

## Partnership Types

### 1. Co-Lending (80:20, 90:10)

Traditional co-lending where both parties fund the loan:

| Ratio | Lender Share | Originator Share | Use Case |
|-------|--------------|------------------|----------|
| 80:20 | 80% | 20% | Standard NBFC-Bank co-lending |
| 90:10 | 90% | 10% | Low capital NBFC arrangements |
| 75:25 | 75% | 25% | Higher originator stake |

**Flow:**
```
Disbursement:
┌───────────────┐
│ Loan: ₹10 Lakh│
└───────┬───────┘
        │
   ┌────┴────┐
   ▼         ▼
Lender    Originator
 80%         20%
₹8 Lakh   ₹2 Lakh
```

### 2. Direct Assignment (100:0)

Lender funds entire loan, originator only services:

```
Disbursement: 100% from Lender
Servicing: By Originator
Income: Lender gets yield, Originator gets servicer fee + excess spread
```

### 3. Participation

Existing loans sold to lender:

```
Day 1: Originator funds 100%
Day N: Sells X% participation to Lender
       Originator retains (100-X)%
```

---

## Data Model

### LoanParticipation

```python
class LoanParticipation:
    loan_account_id: int
    partner_id: int
    participation_type: str  # co_lending, assignment, participation
    share_percent: Decimal   # 80.00, 90.00, 100.00
    interest_rate: Decimal   # Lender's yield rate
    is_fully_backed: bool    # True for 100:0 arrangements

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
    net_write_off: Decimal  # After FLDG

    # ECL
    ecl_stage: int
    ecl_provision: Decimal
```

### LoanPartner

```python
class LoanPartner:
    name: str
    partner_type: str  # originator, lender, servicer, investor

    # Default terms
    default_share_percent: Decimal
    default_yield_rate: Decimal

    # FLDG capability
    provides_fldg: bool
    default_fldg_percent: Decimal

    # Servicer capability
    is_servicer: bool
    default_servicer_fee_rate: Decimal

    # Limits
    total_exposure_limit: Decimal
    current_exposure: Decimal
```

---

## Collection Split

### EMI Collection Example (80:20)

```
EMI Received: ₹22,000
├── Principal: ₹17,000
│   ├── Lender (80%): ₹13,600
│   └── Originator (20%): ₹3,400
│
├── Interest: ₹5,000
│   ├── Lender Yield (10% of principal)
│   ├── Excess Spread (4% to Originator)
│   └── Net Interest split per share
│
└── Fees: As per arrangement
```

### Waterfall Priority

```
1. Servicer Fee (withheld)
2. Excess Spread (to originator)
3. Lender's Yield Interest
4. Principal Split (per share)
5. Remaining Interest Split
```

---

## Settlement Process

### Daily Settlement (Collections)

```
Collection Date: 2024-01-15
Total Collections: ₹50,00,000

Partner Ledger Entry:
┌────────────┬────────────┬────────────┐
│ Partner    │ Share      │ Amount     │
├────────────┼────────────┼────────────┤
│ Lender     │ 80%        │ ₹40,00,000 │
│ Originator │ 20%        │ ₹10,00,000 │
└────────────┴────────────┴────────────┘

Less: Servicer Fee Withheld: ₹20,000
Net to Lender: ₹39,80,000
```

### Monthly Settlement

```python
PartnerSettlement:
    partner_id: int
    period_start: date
    period_end: date

    total_principal: Decimal
    total_interest: Decimal
    total_fees: Decimal
    total_adjustments: Decimal
    net_amount: Decimal

    status: str  # pending, approved, paid
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/loan-participations` | POST | Create participation |
| `/loan-participations/{id}` | GET | Get participation details |
| `/loan-participations/{id}/collections` | GET | View collections |
| `/partner-settlements` | POST | Generate settlement |
| `/partner-settlements/{id}/approve` | POST | Approve settlement |

---

## Key Business Rules

1. **Share Validation**: Total shares must equal 100%
2. **Rate Validation**: Lender yield ≤ Borrower rate
3. **FLDG Linkage**: Required for co-lending in most cases
4. **Settlement Frequency**: Daily/Weekly/Monthly as per arrangement
5. **Write-off Sync**: Must update all partner shares on write-off

---

## Reports

### Partner Portfolio Report
- Total disbursed by partner
- Outstanding by partner
- Collections by partner
- DPD/NPA by partner share

### Settlement Report
- Period-wise settlements
- Principal/Interest/Fee breakup
- Servicer fee deductions
- Net amounts

### Excess Spread Report
- Loan-wise excess spread
- Cumulative tracking
- Accrued vs. realized

---

## Integration Points

1. **Disbursement**: Split funding between partners
2. **Collections**: Split and allocate to partners
3. **Write-off**: FLDG claim, partner notification
4. **ECL**: Partner-wise provision tracking
5. **Settlements**: Generate and reconcile
