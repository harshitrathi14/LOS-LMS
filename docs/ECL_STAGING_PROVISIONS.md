# ECL Staging & Provisions Module

## Overview

Expected Credit Loss (ECL) accounting under IFRS 9 / Ind AS 109 requires forward-looking provisioning based on credit risk staging. This module handles stage assignment, provision calculation, and regulatory reporting.

---

## ECL Stages

### Stage Classification

| Stage | Description | ECL Measurement | Typical DPD |
|-------|-------------|-----------------|-------------|
| **Stage 1** | Performing | 12-month ECL | 0-30 days |
| **Stage 2** | Underperforming (SICR) | Lifetime ECL | 31-90 days |
| **Stage 3** | Non-performing (Impaired) | Lifetime ECL | 90+ days |

### Stage Assignment Criteria

```
┌─────────────────────────────────────────────────────┐
│                Stage Assignment Logic               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Is Written Off? ──────Yes──────► STAGE 3          │
│        │                                            │
│        No                                           │
│        │                                            │
│  Is NPA? ──────────────Yes──────► STAGE 3          │
│        │                                            │
│        No                                           │
│        │                                            │
│  DPD > 90? ────────────Yes──────► STAGE 3          │
│        │                                            │
│        No                                           │
│        │                                            │
│  Is Restructured? ─────Yes──────► STAGE 2          │
│        │                                            │
│        No                                           │
│        │                                            │
│  DPD > 30? ────────────Yes──────► STAGE 2          │
│        │                                            │
│        No                                           │
│        │                                            │
│  SICR Triggered? ──────Yes──────► STAGE 2          │
│        │                                            │
│        No                                           │
│        │                                            │
│        └─────────────────────────► STAGE 1          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## ECL Calculation

### Formula

```
ECL = EAD × PD × LGD × (Discount Factor)

Where:
  EAD = Exposure at Default
  PD  = Probability of Default
  LGD = Loss Given Default
```

### Stage-wise Calculation

| Stage | PD Horizon | Typical PD | Typical LGD |
|-------|------------|------------|-------------|
| Stage 1 | 12-month | 0.5% - 2% | 35% - 65% |
| Stage 2 | Lifetime | 5% - 15% | 35% - 65% |
| Stage 3 | Lifetime | 100% | 35% - 65% |

### Example Calculation

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

---

## Data Model

### ECLConfiguration

```python
class ECLConfiguration:
    config_code: str
    product_id: int  # Optional, null = all products

    # DPD criteria
    stage1_max_dpd: int  # Default: 30
    stage2_max_dpd: int  # Default: 90

    # Flag criteria
    stage2_restructure_flag: bool
    stage3_write_off_flag: bool
    stage3_npa_flag: bool

    # SICR thresholds
    sicr_rating_downgrade_notches: int
    sicr_pd_increase_threshold: Decimal

    # Default PD/LGD
    pd_stage1_12m: Decimal   # 0.5%
    pd_stage2_lifetime: Decimal  # 5%
    pd_stage3: Decimal  # 100%
    lgd_secured: Decimal  # 35%
    lgd_unsecured: Decimal  # 65%
```

### ECLStaging

```python
class ECLStaging:
    loan_account_id: int
    current_stage: int  # 1, 2, 3
    stage_effective_date: date
    stage_reason: str  # dpd, sicr, restructure, npa, manual

    # Risk parameters
    pd_12m: Decimal
    pd_lifetime: Decimal
    lgd: Decimal

    # EAD
    ead_on_balance: Decimal
    ead_off_balance: Decimal
    total_ead: Decimal

    # Flags
    is_restructured: bool
    is_npa: bool
    is_written_off: bool
    sicr_triggered: bool
```

### ECLProvision

```python
class ECLProvision:
    loan_account_id: int
    provision_date: date  # Month-end
    is_month_end: bool

    ecl_stage: int

    # Exposure
    principal_outstanding: Decimal
    interest_outstanding: Decimal
    fees_outstanding: Decimal
    total_exposure: Decimal
    total_ead: Decimal

    # Parameters applied
    pd_applied: Decimal
    lgd_applied: Decimal

    # ECL amounts
    ecl_12_month: Decimal
    ecl_lifetime: Decimal
    ecl_applied: Decimal  # 12m for Stage 1, Lifetime for 2/3

    # Provision movement
    opening_provision: Decimal
    provision_charge: Decimal  # P&L impact
    provision_release: Decimal
    write_off_utilized: Decimal
    closing_provision: Decimal

    # Coverage
    provision_coverage: Decimal  # %

    source: str  # calculated, uploaded, manual
```

### ECLMovement

```python
class ECLMovement:
    loan_account_id: int
    movement_date: date

    from_stage: int
    to_stage: int
    movement_direction: str  # upgrade, downgrade

    movement_reason: str

    dpd_before: int
    dpd_after: int

    exposure_at_movement: Decimal
    provision_impact: Decimal
```

---

## Month-End Processing

### Provision Calculation Flow

```
Month-End Batch (e.g., 31-Jan-2024)
            │
            ▼
┌─────────────────────────────┐
│ For each active loan:       │
│ 1. Determine ECL stage      │
│ 2. Calculate EAD            │
│ 3. Get PD, LGD parameters   │
│ 4. Calculate ECL            │
│ 5. Record provision         │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Track stage movements       │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Generate portfolio summary  │
└─────────────────────────────┘
```

### Portfolio Summary

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

Stage Movements (Jan-2024):
  Stage 1 → Stage 2: 50 loans
  Stage 2 → Stage 3: 10 loans
  Stage 2 → Stage 1: 20 loans (upgrades)
  Stage 3 → Stage 2: 5 loans (upgrades)

Provision Movement:
  Opening (31-Dec): ₹11.50 Cr
  Charge: ₹1.20 Cr
  Release: ₹0.30 Cr
  Write-off utilized: ₹0.21 Cr
  Closing (31-Jan): ₹12.19 Cr
```

---

## ECL Upload

For institutions calculating ECL externally, the system supports bulk upload:

```python
ECLUpload:
    upload_reference: str
    upload_date: date
    provision_date: date  # As-on date

    total_records: int
    successful_records: int
    failed_records: int

    # Totals from upload
    total_exposure: Decimal
    total_provision: Decimal

    # Stage-wise
    stage1_exposure: Decimal
    stage1_provision: Decimal
    stage2_exposure: Decimal
    stage2_provision: Decimal
    stage3_exposure: Decimal
    stage3_provision: Decimal

    status: str  # pending, processing, completed
    requires_approval: bool
```

### Upload File Format

```csv
account_number,ecl_stage,pd,lgd,provision_amount
ACC001,1,0.5,65,325
ACC002,2,5.0,65,3250
ACC003,3,100,65,65000
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ecl-configurations` | POST | Create ECL config |
| `/ecl-staging/{loan_id}` | GET | Get loan ECL stage |
| `/ecl-staging/{loan_id}/assign` | POST | Assign/update stage |
| `/ecl-provisions` | POST | Calculate provision |
| `/ecl-provisions/batch` | POST | Month-end batch |
| `/ecl-provisions/{loan_id}/history` | GET | Provision history |
| `/ecl-uploads` | POST | Create upload record |
| `/ecl-uploads/{id}/process` | POST | Process upload |
| `/ecl-portfolio-summary` | GET | Get portfolio summary |

---

## SICR (Significant Increase in Credit Risk)

### Triggers

1. **Rating Downgrade**: ≥ 2 notches downgrade
2. **PD Increase**: > 100% increase in PD
3. **Qualitative**: Restructuring, watch-list, etc.

### Example

```
Original Assessment (at origination):
  Rating: A
  12-month PD: 0.3%

Current Assessment:
  Rating: BB (2 notches down)
  12-month PD: 1.2% (300% increase)

SICR Triggered: Yes
Action: Move to Stage 2
```

---

## Integration with Write-off Flags

### LoanAccount Write-off Fields

```python
# Write-off flags (in LoanAccount)
is_written_off: bool
write_off_date: date
write_off_amount: Decimal
write_off_reason: str

# NPA flags
is_npa: bool
npa_date: date
npa_category: str  # substandard, doubtful, loss

# Restructure flags
is_restructured: bool

# ECL
ecl_stage: int
ecl_stage_date: date
ecl_provision: Decimal
ecl_provision_date: date
```

---

## Reports

### ECL Stage Report
- Stage-wise loan count and exposure
- Coverage ratios by stage
- Stage movement trends

### Provision Movement Report
- Opening → Closing reconciliation
- Charge/Release analysis
- Write-off utilization

### SICR Analysis Report
- SICR trigger analysis
- Stage 1 → Stage 2 migration reasons
- Early warning indicators

### Regulatory Report
- RBI/IRAC compliant format
- Asset quality disclosure
- Provision coverage disclosure

---

## Best Practices

1. **Monthly Processing**: Run ECL batch at month-end
2. **Parameter Review**: Review PD/LGD annually
3. **Stage Override**: Document all manual overrides
4. **Audit Trail**: Maintain complete provision history
5. **Reconciliation**: Reconcile with GL provisions
