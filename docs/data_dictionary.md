# Data Dictionary

## FactClaims

| Field group | Representative fields | Purpose |
|---|---|---|
| Identifiers | `claim_id`, `patient_id`, `encounter_id`, `provider_id` | Synthetic record linkage |
| Dimensions | `payer_key`, `facility_key`, `care_setting`, `facility_maturity` | Reporting relationships and segmentation |
| Dates | `service_date`, `submission_date`, `initial_adjudication_date`, `first_payment_date` | Timeline and turnaround analysis |
| Claim profile | `patient_age`, `diagnosis_count`, `claim_line_count`, `distinct_procedure_count` | Pre-submission analytical features |
| Financials | `claim_charge`, `expected_allowed_amount`, `expected_payer_payment`, `actual_payer_payment`, `patient_payment`, `outstanding_balance` | Revenue-cycle KPIs |
| Outcomes | `underpayment_flag`, `initial_denial_as_of_flag`, `final_denial_flag` | Denial and reimbursement analysis |
| Work queue | `claim_age_days`, `aging_bucket`, `timely_filing_risk`, `follow_up_priority_score`, `follow_up_priority_band` | Operational prioritization |
| Governance | `simulation_seed`, `lineage_notice` | Reproducibility and synthetic-data disclosure |

## FactDenials

| Field | Description |
|---|---|
| `claim_id` | Claim-level foreign key |
| `denial_reason` | Simulated denial category |
| `preventable_denial_flag` | Indicates a potentially avoidable workflow cause |
| `appeal_or_resubmission_flag` | Indicates remediation activity |
| `appeal_date` / `appeal_decision_date` | Simulated appeal timeline |
| `appeal_success_as_of_flag` | Successful appeal by the reporting date |
| `final_denial_flag` | Denial remaining unresolved |
| `recovery_amount` | Amount recovered after remediation |
| `denied_dollars` | Financial exposure associated with the denial |

## DimFacility

Contains the facility key and ID, fictional facility name, state, synthetic county, county FIPS, and facility-maturity category for 120 fictional facilities.

## DimPayer

Contains payer key, payer category, fictional payer name, and insured/self-pay indicator.

## DimDate

Provides a continuous calendar with date key, year, quarter, month, weekday, and weekend attributes.
