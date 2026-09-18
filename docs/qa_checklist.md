# Quality-Assurance Checklist

- [x] Exactly 90,000 claim rows generated
- [x] Exactly 10 states represented
- [x] Exactly 9,000 claims per state
- [x] Unique claim identifiers
- [x] Nonnegative financial amounts
- [x] Valid service, submission, adjudication, and payment chronology
- [x] Final denials restricted to initially denied claims
- [x] Successful appeals excluded from final denials
- [x] Claim and denial fact-table reconciliation
- [x] Required synthetic lineage notice present
- [x] SQL validation checks passed
- [x] Temporal train/test separation used for the model
- [x] Post-adjudication leakage fields excluded from model features
- [x] Model evaluated against predefined approval gates
- [x] Model withheld from operational dashboard use after failing gates
- [x] Power BI totals reconciled to validation extracts
- [x] Slicer and interaction behavior reviewed
- [x] Portfolio disclaimer included in documentation
