# FLDG (First Loss Default Guarantee) Module

## Overview

FLDG is a credit enhancement mechanism where the originator provides a guarantee to absorb initial losses on a portfolio, protecting the lender from defaults up to a specified limit.

---

## FLDG Types

### 1. First Loss Default Guarantee (FLDG)

The originator's guarantee absorbs losses first:

```
Portfolio: ₹100 Cr
FLDG: 5% = ₹5 Cr

Default Scenario:
├── Default Amount: ₹3 Cr
│   └── FLDG Absorbs: ₹3 Cr (100%)
│   └── Lender Loss: ₹0
│
├── Default Amount: ₹7 Cr
│   └── FLDG Absorbs: ₹5 Cr (Max)
│   └── Lender Loss: ₹2 Cr
```

### 2. Second Loss Default Guarantee

Kicks in after first loss threshold is breached:

```
Portfolio: ₹100 Cr
First Loss Threshold: ₹3 Cr (Lender absorbs)
Second Loss FLDG: ₹5 Cr (Originator provides)

Default Scenario (₹7 Cr):
├── First Loss (Lender): ₹3 Cr
├── Second Loss (FLDG): ₹4 Cr
└── Remaining (if any): Lender
```

---

## Data Model

### FLDGArrangement

```python
class FLDGArrangement:
    arrangement_code: str
    name: str

    # Parties
    originator_id: int  # Provides FLDG
    lender_id: int      # Protected by FLDG

    # Type
    fldg_type: str  # first_loss, second_loss

    # Limits
    fldg_percent: Decimal           # % of portfolio
    fldg_absolute_amount: Decimal   # Absolute cap
    effective_fldg_limit: Decimal   # Min of above
    first_loss_threshold: Decimal   # For second loss

    # Coverage scope
    covers_principal: bool  # Usually True
    covers_interest: bool   # Usually True
    covers_fees: bool       # Usually False

    # Guarantee form
    guarantee_form: str  # cash_deposit, bank_guarantee, corporate_guarantee
    bank_guarantee_number: str
    bank_guarantee_expiry: date

    # Current status
    current_fldg_balance: Decimal
    total_utilized: Decimal
    total_recovered: Decimal

    # Triggers
    trigger_dpd: int  # DPD threshold (usually 90)
    trigger_on_write_off: bool
    trigger_on_npa: bool

    # Top-up
    requires_top_up: bool
    top_up_threshold_percent: Decimal  # e.g., 50%

    status: str  # active, expired, exhausted, terminated
```

### FLDGUtilization

```python
class FLDGUtilization:
    arrangement_id: int
    loan_account_id: int

    utilization_date: date
    trigger_reason: str  # npa, write_off, dpd_threshold

    # Claimed amounts
    principal_claimed: Decimal
    interest_claimed: Decimal
    fees_claimed: Decimal
    total_claimed: Decimal

    # Approved amounts
    principal_approved: Decimal
    interest_approved: Decimal
    total_approved: Decimal

    # Reference
    write_off_id: int
    dpd_at_utilization: int

    # Balance impact
    fldg_balance_before: Decimal
    fldg_balance_after: Decimal

    status: str  # pending, approved, rejected, settled, recovered
```

### FLDGRecovery

```python
class FLDGRecovery:
    utilization_id: int
    recovery_date: date

    principal_recovered: Decimal
    interest_recovered: Decimal
    total_recovered: Decimal

    amount_returned_to_fldg: Decimal
    recovery_source: str  # borrower, guarantor, collateral, legal
```

---

## FLDG Lifecycle

### 1. Setup

```
┌─────────────────────────────────────────┐
│         FLDG Arrangement Setup          │
├─────────────────────────────────────────┤
│ 1. Define FLDG %/Amount                 │
│ 2. Specify coverage scope               │
│ 3. Set trigger conditions               │
│ 4. Originator deposits guarantee        │
│ 5. Link to co-lending arrangement       │
└─────────────────────────────────────────┘
```

### 2. Utilization Flow

```
Loan Defaults (90+ DPD or Write-off)
           │
           ▼
┌─────────────────────┐
│ Check FLDG Coverage │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Calculate Claim     │
│ - Principal share   │
│ - Interest share    │
│ - Fee share (if any)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Check FLDG Balance  │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
Sufficient    Insufficient
    │             │
    ▼             ▼
Full Claim    Partial Claim
Approved      (Max Balance)
    │             │
    └──────┬──────┘
           ▼
┌─────────────────────┐
│ Update FLDG Balance │
│ Record Utilization  │
│ Update Participation│
└─────────────────────┘
```

### 3. Recovery Flow

```
Recovery from Written-off Loan
           │
           ▼
┌─────────────────────┐
│ Check FLDG Utilized │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Return to FLDG Pool │
│ (up to utilized)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Excess to Lender    │
└─────────────────────┘
```

---

## Calculation Examples

### FLDG Limit Calculation

```
Portfolio Outstanding: ₹100,00,00,000
FLDG Percent: 5%
Absolute Cap: ₹4,00,00,000

Calculated Limit = ₹100 Cr × 5% = ₹5 Cr
Effective Limit = Min(₹5 Cr, ₹4 Cr) = ₹4 Cr
```

### Utilization Calculation (80:20 Co-Lending)

```
Loan Outstanding:
  Principal: ₹1,00,000
  Interest: ₹5,000
  Fees: ₹1,000

Lender Share: 80%

FLDG Claim:
  Principal: ₹1,00,000 × 80% = ₹80,000
  Interest: ₹5,000 × 80% = ₹4,000
  Total Claim: ₹84,000
```

### Top-Up Requirement

```
Effective Limit: ₹5,00,00,000
Current Balance: ₹1,50,00,000
Threshold: 50%

Threshold Amount = ₹5 Cr × 50% = ₹2.5 Cr
Current Balance (₹1.5 Cr) < Threshold (₹2.5 Cr)

Top-Up Required: ₹5 Cr - ₹1.5 Cr = ₹3.5 Cr
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/fldg-arrangements` | POST | Create FLDG arrangement |
| `/fldg-arrangements/{id}` | GET | Get arrangement details |
| `/fldg-arrangements/{id}/summary` | GET | Get utilization summary |
| `/fldg-arrangements/{id}/top-up-check` | GET | Check if top-up needed |
| `/fldg-utilizations` | POST | Trigger FLDG utilization |
| `/fldg-utilizations/{id}/approve` | POST | Approve utilization |
| `/fldg-recoveries` | POST | Record recovery |

---

## Business Rules

### Trigger Conditions
1. **DPD Trigger**: Usually 90+ DPD
2. **NPA Classification**: On RBI NPA classification
3. **Write-off**: On loan write-off

### Coverage Rules
1. Principal: Always covered
2. Interest: Usually covered (check arrangement)
3. Fees: Rarely covered

### Top-Up Rules
1. Monitor balance vs threshold (typically 50%)
2. Notify originator when top-up required
3. Track compliance with top-up timelines

### Recovery Priority
1. FLDG replenishment first (up to utilized amount)
2. Excess to lender
3. Remaining to originator (if any)

---

## Reports

### FLDG Status Report
```
Arrangement: FLDG-2024-001
Type: First Loss

Effective Limit: ₹5,00,00,000
Current Balance: ₹3,50,00,000
Total Utilized: ₹1,50,00,000
Total Recovered: ₹50,00,000

Utilization Rate: 30%
Active Claims: 15
Pending Approval: 2
```

### Utilization Report
- Loan-wise utilization
- Trigger reason analysis
- Approval rates
- Settlement status

### Recovery Report
- Recovery by source
- FLDG replenishment tracking
- Net utilization trend

---

## Integration Points

1. **Write-off**: Auto-trigger FLDG claim
2. **Collections**: Route recoveries to FLDG
3. **ECL**: Consider FLDG in provision calculation
4. **Settlements**: Include FLDG in partner settlements
5. **Reporting**: FLDG exposure in regulatory reports
