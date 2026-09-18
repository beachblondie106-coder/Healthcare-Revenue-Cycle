# Core DAX Measures

```DAX
Total Claims = DISTINCTCOUNT(FactClaims[claim_id])

Total Charges = SUM(FactClaims[claim_charge])

Actual Payer Payments = SUM(FactClaims[actual_payer_payment])

Outstanding Balance = SUM(FactClaims[outstanding_balance])

Denied Claims =
CALCULATE(
    [Total Claims],
    FactClaims[initial_denial_as_of_flag] = 1
)

Initial Denial Rate =
DIVIDE(
    [Denied Claims],
    CALCULATE([Total Claims], FactClaims[adjudicated_as_of_flag] = 1)
)

Underpayment Amount = SUM(FactClaims[underpayment_amount])

Payment Realization Rate =
DIVIDE(
    [Actual Payer Payments],
    SUM(FactClaims[expected_payer_payment])
)
```

These representative measures document the main reporting logic. The PBIX remains the authoritative semantic model, including visual-specific filters and formatting.
