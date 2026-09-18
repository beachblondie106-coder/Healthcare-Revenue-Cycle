# Data Access and Reproduction

The full generated analytical dataset contains 90,000 synthetic claims and is intentionally not committed as raw source data. This keeps the repository reviewable and follows the publication plan in the project blueprint.

Use the scripts in `python/` to reproduce the full dataset with the fixed seed `20260917`. The generated reporting model contains:

- `FactClaims.csv`
- `FactDenials.csv`
- `DimDate.csv`
- `DimPayer.csv`
- `DimFacility.csv`

The repository includes compact validation extracts and model-development outputs for auditability. All records are constructed synthetic portfolio data and contain no PHI.
