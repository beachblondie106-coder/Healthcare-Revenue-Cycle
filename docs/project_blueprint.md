# Multi-State Healthcare Revenue Cycle & Claims Denial Analytics

## Project Blueprint

### Portfolio Positioning

This independent portfolio project will analyze the financial and operational performance of a fictional multi-state healthcare organization. It will demonstrate end-to-end healthcare analytics using SQL, Python, Power BI, Power Query, DAX, and Excel-based quality assurance.

The project will use synthetic patient and claims data. All organizations, facilities, payer outcomes, denial reasons, operational scenarios, and financial results will be fictional and created exclusively for portfolio demonstration. The project will not contain protected health information (PHI).

## Primary Business Question

Where are claims being denied, delayed, or underpaid, what factors are associated with those outcomes, and which operational interventions offer the greatest opportunity to improve reimbursement and reduce avoidable revenue leakage?

## Intended Audience

- Revenue cycle and patient financial services leaders
- Healthcare operations executives
- Finance and reimbursement teams
- Coding, billing, and authorization managers
- Business intelligence and data analytics teams
- Payer and provider strategy leaders

## Geographic Scope

The fictional healthcare organization will operate across 10 states:

| Region | State | Market role in the simulation |
|---|---|---|
| Southeast | Florida | Large Medicare-oriented market and mixed urban/rural operations |
| Southeast | Alabama | Rural access and Medicaid-oriented comparisons |
| Southeast | Tennessee | Regional health-system representation |
| Southeast | North Carolina | Growing urban and rural healthcare markets |
| South Central | Texas | Large and diverse healthcare market |
| Northeast | New York | Dense urban market and complex payer mix |
| Midwest | Wisconsin | Midwestern regional representation |
| Mountain West | Montana | Rural and frontier healthcare conditions |
| Southwest | Arizona | Urban, rural, and Medicare population mix |
| West | California | Large and varied payer market |

Geographic comparisons will represent fictional operating markets. They will not be presented as measurements of actual state denial or reimbursement performance.

## Proposed Analysis Period and Volume

- Analysis period: January 2024 through December 2025
- Monthly trend structure: 24 months
- Target claim volume: approximately 75,000 to 100,000 claims
- Facility types: hospitals, outpatient centers, emergency departments, and professional practices
- Payer groups: Medicare, Medicaid, Commercial, Medicare Advantage, and Self-Pay
- Care settings: Inpatient, Outpatient, Emergency, and Professional

## Data Strategy

### Foundation Data

Synthea-generated CSV data will supply synthetic patients, encounters, procedures, diagnoses, organizations, providers, payers, claims, and claim transactions where available.

### Simulated Revenue-Cycle Layer

A documented and reproducible rules engine will create the operational fields needed for denial and revenue-cycle analysis. These fields may include:

- Claim submission and adjudication dates
- Claim status
- Initial allowed amount
- Paid amount
- Patient responsibility
- Outstanding balance
- Denial indicator
- Denial reason category
- Resubmission indicator
- Appeal indicator and outcome
- Authorization indicator
- Coding edit indicator
- Eligibility issue indicator
- Documentation issue indicator
- Duplicate claim indicator
- Timely-filing risk

The simulation logic will be retained in source-controlled SQL and/or Python files. No simulated outcome will be represented as an observed real-world payer result.

## Core Business Questions

1. What are the submitted charges, allowed amounts, payments, outstanding balances, and collection rates?
2. Which payers, facilities, states, service lines, and care settings have the highest denial rates?
3. Which denial categories generate the greatest financial exposure?
4. How quickly are claims paid, denied, appealed, and resolved?
5. Which outstanding claims are approaching timely-filing or follow-up thresholds?
6. Where do underpayments occur relative to expected reimbursement?
7. Which operational factors are associated with avoidable denials?
8. Which claims should be prioritized for follow-up based on value, age, and recovery likelihood?
9. Can an interpretable model identify claims at elevated denial risk before submission?
10. What actions would most effectively reduce avoidable denials and improve cash flow?

## Analytical Data Model

### Dimension Tables

| Table | Purpose |
|---|---|
| `dim_date` | Calendar, month, quarter, year, and aging attributes |
| `dim_patient` | De-identified synthetic patient demographics and geography |
| `dim_facility` | Fictional facility, state, region, and facility type |
| `dim_provider` | Synthetic provider and specialty attributes |
| `dim_payer` | Payer group, product type, and fictional payer name |
| `dim_service_line` | Clinical service-line categories |
| `dim_diagnosis` | Diagnosis code and grouped condition category |
| `dim_procedure` | Procedure code and grouped procedure category |
| `dim_denial_reason` | Denial category, preventability, and responsible workflow |

### Fact Tables

| Table | Grain and purpose |
|---|---|
| `fact_claim` | One row per claim with financial and adjudication outcomes |
| `fact_claim_line` | One row per claim line for service and coding analysis |
| `fact_claim_transaction` | One row per payment, adjustment, denial, appeal, or recovery transaction |
| `fact_encounter` | One row per synthetic patient encounter |
| `fact_denial` | One row per denied claim with reason, status, and resolution details |

## Key Performance Indicators

| KPI | Working definition |
|---|---|
| Initial denial rate | Initially denied claims divided by adjudicated claims |
| Final denial rate | Unresolved denied claims divided by adjudicated claims |
| Clean claim rate | Claims accepted on first submission divided by submitted claims |
| Gross collection rate | Total payments divided by total charges |
| Net collection rate | Total payments divided by expected collectible amount |
| Underpayment amount | Expected reimbursement minus actual payer payment when positive |
| Days to initial adjudication | Initial adjudication date minus submission date |
| Days to payment | First payment date minus submission date |
| Accounts receivable days | Outstanding receivables divided by average daily charges |
| Appeal success rate | Successful appeals divided by completed appeals |
| Denial recovery rate | Recovered denied dollars divided by denied dollars pursued |
| Avoidable denial rate | Preventable denials divided by adjudicated claims |
| High-priority balance | Outstanding dollars meeting value, age, and recoverability criteria |

All KPI denominators, exclusions, date rules, and edge cases will be documented before dashboard construction.

## Power BI Dashboard Plan

### Page 1 — Executive Revenue Cycle Summary

- Submitted charges, allowed amounts, payments, and outstanding balance
- Initial and final denial rates
- Clean claim rate and net collection rate
- Monthly cash and denial trends
- State, payer, and facility filters

### Page 2 — Denial and Underpayment Analysis

- Denied claims and dollars by reason
- Denial rate by payer, service line, facility, and care setting
- Preventable versus non-preventable denials
- Underpayment frequency and financial impact
- High-value denial detail

### Page 3 — Claims Aging and Follow-Up

- Aging buckets: 0–30, 31–60, 61–90, 91–120, and over 120 days
- Outstanding balance by payer and facility
- Timely-filing and follow-up risk
- Claim-priority worklist
- Resolution and recovery trends

### Page 4 — Payer Performance

- Payment turnaround time
- Allowed-to-charge and paid-to-allowed ratios
- Initial denial and appeal overturn rates
- Underpayment exposure
- Payer performance scorecard

### Page 5 — Operational Root-Cause Analysis

- Authorization, eligibility, coding, documentation, and duplicate-claim patterns
- Denial responsibility by workflow area
- Facility and service-line comparisons
- Process and outcome measures
- Recommended operational interventions

### Page 6 — Predictive Denial Risk

- Model performance and validation summary
- Most influential risk factors
- High-risk claims by expected financial exposure
- Risk bands and intervention opportunities
- Clear model limitations and non-production disclaimer

## SQL Scope

SQL will be used in the actual analytical workflow to:

- Create the relational schema
- Load and standardize source tables
- Join claims, encounters, payers, facilities, providers, and services
- Build reusable revenue-cycle views
- Calculate aging and reimbursement metrics
- Use CTEs and window functions for ranking, trends, and claim prioritization
- Produce validated analytical tables for Python and Power BI

## Python Scope

Python will be used to:

- Validate source and transformed data
- Generate reproducible simulated revenue-cycle outcomes
- Perform exploratory analysis
- Detect missing values, duplicates, outliers, and referential-integrity problems
- Engineer denial-risk features
- Train and evaluate an interpretable classification model
- Export model scores for Power BI

The predictive component will be framed as a portfolio demonstration, not a clinical or production decision system.

## Power Query and DAX Scope

Power Query will handle final ingestion, type enforcement, field naming, and reporting-layer transformations. DAX will calculate report-context measures, time trends, payer and facility benchmarks, aging KPIs, recovery measures, and dynamic dashboard labels.

## Quality-Assurance Framework

- Source-to-target row-count reconciliation
- Primary-key and duplicate testing
- Foreign-key integrity testing
- Financial balance testing
- Mutually exclusive claim-status testing
- Date-sequence validation
- KPI numerator and denominator reconciliation
- SQL-to-Power BI metric comparison
- Model train/test separation and leakage review
- Visual filter and interaction testing

## Repository Structure

```text
healthcare-revenue-cycle-claims-analytics/
  README.md
  data/
    raw/
    interim/
    processed/
    sample/
  docs/
    project_blueprint.md
    data_dictionary.md
    methodology.md
    kpi_definitions.md
    qa_checklist.md
    model_card.md
  sql/
    01_create_schema.sql
    02_load_staging.sql
    03_transform_claims.sql
    04_revenue_cycle_views.sql
    05_validation_queries.sql
  python/
    01_generate_simulated_outcomes.ipynb
    02_data_quality_and_eda.ipynb
    03_denial_risk_model.ipynb
  powerbi/
    Healthcare Revenue Cycle Analytics.pbix
    dax_measures.md
    power_query_scripts/
  qa/
    reconciliation_workbook.xlsx
  exports/
    dashboard_preview.pdf
    executive_presentation.pdf
  LICENSE
```

Large raw data files will not be committed to GitHub. The repository will include a reproducible generation process, a small sample dataset where appropriate, and clear download or generation instructions.

## Build Sequence

1. Finalize blueprint, definitions, and data rules.
2. Generate and inspect a small Synthea sample.
3. Create the data dictionary and source-to-target mapping.
4. Design and build the SQL schema.
5. Build the reproducible outcome-simulation layer.
6. Load and validate the analytical database.
7. Perform Python exploratory analysis and feature engineering.
8. Develop and validate the denial-risk model.
9. Build the Power BI semantic model and DAX measures.
10. Create and validate the dashboard pages.
11. Write executive findings, recommendations, and limitations.
12. Package the project for GitHub and the professional portfolio.

## Publication Disclaimer

This is an independent portfolio project using synthetic data. All patients, claims, payers, providers, facilities, denial outcomes, operational scenarios, and financial results are fictional. The analysis is not affiliated with, commissioned by, sponsored by, reviewed by, or endorsed by any healthcare organization, payer, government agency, or data provider. The project is intended solely to demonstrate healthcare analytics, business intelligence, SQL, Python, data modeling, and process-improvement skills.

