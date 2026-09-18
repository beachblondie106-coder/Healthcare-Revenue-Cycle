WITH qa AS (
    SELECT 'duplicate_fact_claim_id' AS check_name, COUNT(*) AS failed_rows
    FROM (SELECT claim_id FROM fact_claim GROUP BY claim_id HAVING COUNT(*) > 1)
    UNION ALL SELECT 'negative_financial_amount', COUNT(*) FROM fact_claim
      WHERE claim_charge < 0 OR expected_allowed_amount < 0 OR actual_payer_payment < 0 OR outstanding_balance < 0
    UNION ALL SELECT 'submission_before_service', COUNT(*) FROM fact_claim WHERE submission_date < service_date
    UNION ALL SELECT 'adjudication_before_submission', COUNT(*) FROM fact_claim
      WHERE initial_adjudication_date IS NOT NULL AND initial_adjudication_date < submission_date
    UNION ALL SELECT 'final_denial_without_initial_denial', COUNT(*) FROM fact_claim
      WHERE final_denial_flag = 1 AND initial_denial_as_of_flag = 0
    UNION ALL SELECT 'successful_appeal_still_final_denial', COUNT(*) FROM sim_claim_outcome
      WHERE appeal_success_as_of_flag = 1 AND final_denial_flag = 1
    UNION ALL SELECT 'fact_claim_row_count_mismatch',
      ABS((SELECT COUNT(*) FROM sim_claim_outcome) - (SELECT COUNT(*) FROM fact_claim))
    UNION ALL SELECT 'denial_fact_row_count_mismatch',
      ABS((SELECT COUNT(*) FROM sim_claim_outcome WHERE initial_denial_as_of_flag = 1) - (SELECT COUNT(*) FROM fact_denial))
    UNION ALL SELECT 'unexpected_lineage_notice', COUNT(*) FROM fact_claim
      WHERE lineage_notice <> 'CONSTRUCTED SYNTHETIC PORTFOLIO DATA' OR lineage_notice IS NULL
    UNION ALL SELECT 'state_claim_count_not_9000', COUNT(*) FROM (
      SELECT source_state FROM sim_claim_outcome GROUP BY source_state HAVING COUNT(*) <> 9000
    )
    UNION ALL SELECT 'state_count_not_10', ABS(10 - (SELECT COUNT(DISTINCT source_state) FROM sim_claim_outcome))
)
SELECT check_name, failed_rows, CASE WHEN failed_rows = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM qa ORDER BY check_name;

