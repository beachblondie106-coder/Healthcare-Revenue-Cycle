# Project Summary

This portfolio project demonstrates an end-to-end healthcare revenue-cycle analytics workflow using 90,000 constructed synthetic claims across 120 fictional facilities in 10 states. The work combines reproducible Python simulation, a relational SQLite analytical layer, SQL validation, a governed denial-risk modeling experiment, Power Query, DAX, and a three-page Power BI report.

## Business objective

Identify where reimbursement is delayed, denied, underpaid, or left outstanding, and translate those patterns into practical payer, facility, and follow-up priorities.

## Delivered components

- Reproducible multi-state synthetic claims generator
- SQLite schema, analytical views, and QA queries
- Logistic-regression denial-risk experiment with predefined approval gates
- Power BI semantic model and three interactive report pages
- Executive, denial/underpayment, and facility/payer analysis
- Documented simulation rules, lineage, validation, and model-governance decision

## Responsible-use decision

The model did not meet the project's predefined approval gates. Its scores remain a development artifact and are not used as a validated operational decision tool. Dashboard prioritization relies on observed simulated outcomes and transparent rule-based indicators.

## Data disclosure

All data is synthetic. Facilities, patients, providers, payers, claims, denial outcomes, and financial results are fictional and contain no PHI.
