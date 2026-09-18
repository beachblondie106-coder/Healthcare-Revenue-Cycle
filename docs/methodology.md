# Methodology

## 1. Data foundation

The project began with a synthetic Synthea-style pilot structure. A fixed-seed Python rules engine expanded the analytical population to 90,000 claims, with 9,000 claims in each of 10 fictional operating markets. The reporting period covers 2024 and 2025.

## 2. Revenue-cycle simulation

Submission, adjudication, payment, denial, appeal, recovery, underpayment, aging, and follow-up attributes were generated with documented rules. The generator uses seed `20260917` so the output can be reproduced. State is not an explicit denial-risk input.

## 3. Analytical database

Python loads the generated CSV data into SQLite. SQL creates dimension and fact structures, analytical views, financial summaries, payer comparisons, facility rankings, and validation queries.

## 4. Quality assurance

Validation covers row counts, unique claim identifiers, foreign-key integrity, financial non-negativity, date chronology, claim-status consistency, geographic coverage, denial reconciliation, and required synthetic-data lineage.

## 5. Predictive experiment

An interpretable logistic-regression classifier estimates simulated initial-denial risk using only pre-submission features. Training and testing are separated by time. Evaluation emphasizes ROC-AUC, precision-recall AUC, balanced accuracy, precision, recall, and F1 rather than headline accuracy.

The final experiment did not meet the predefined approval gates, so its output is retained for model-governance demonstration only.

## 6. Reporting layer

Power Query enforces types and reporting-layer transformations. The Power BI model connects claims, denials, payer, facility, and date tables. DAX calculates financial, denial, underpayment, aging, and payment-realization measures.

## Reproduction order

1. Run `python/04_generate_multistate_claims.py`.
2. Run `python/05_build_final_database.py`.
3. Execute the SQL QA checks in `sql/04_qa_final.sql`.
4. Run `python/03_denial_risk_model.py` for the governed model experiment.
5. Load the generated reporting tables into the Power BI file.

Exact local input and output paths may need to be updated for the user's environment.
