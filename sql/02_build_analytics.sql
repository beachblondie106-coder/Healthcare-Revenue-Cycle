PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS vw_monthly_revenue_cycle_trend;
DROP VIEW IF EXISTS vw_follow_up_worklist;
DROP VIEW IF EXISTS vw_claims_aging;
DROP VIEW IF EXISTS vw_denial_root_cause;
DROP VIEW IF EXISTS vw_payer_performance;
DROP VIEW IF EXISTS vw_executive_summary;
DROP TABLE IF EXISTS fact_denial;
DROP TABLE IF EXISTS fact_claim_transaction;
DROP TABLE IF EXISTS fact_claim;
DROP TABLE IF EXISTS dim_facility;
DROP TABLE IF EXISTS dim_payer;

CREATE TABLE dim_payer AS
SELECT
    ROW_NUMBER() OVER (ORDER BY payer_category) AS payer_key,
    payer_category,
    CASE payer_category
        WHEN 'Medicare' THEN 'Federal Medicare'
        WHEN 'Medicare Advantage' THEN 'Summit Medicare Advantage'
        WHEN 'Medicaid' THEN 'Community Medicaid'
        WHEN 'Commercial' THEN 'Horizon Commercial Health'
        WHEN 'Self-Pay' THEN 'Self-Pay'
    END AS fictional_payer_name,
    CASE WHEN payer_category = 'Self-Pay' THEN 0 ELSE 1 END AS insured_flag
FROM (SELECT DISTINCT payer_category FROM sim_claim_outcome);

CREATE UNIQUE INDEX idx_dim_payer_key ON dim_payer(payer_key);
CREATE UNIQUE INDEX idx_dim_payer_category ON dim_payer(payer_category);

CREATE TABLE dim_facility AS
SELECT
    ROW_NUMBER() OVER (ORDER BY facility_id) AS facility_key,
    facility_id,
    'Fictional Facility ' || printf('%03d', ROW_NUMBER() OVER (ORDER BY facility_id))
        AS fictional_facility_name,
    MAX(source_state) AS state,
    MAX(source_county) AS county,
    MAX(source_county_fips) AS county_fips,
    MAX(facility_maturity) AS facility_maturity
FROM sim_claim_outcome
WHERE facility_id IS NOT NULL
GROUP BY facility_id;

CREATE UNIQUE INDEX idx_dim_facility_key ON dim_facility(facility_key);
CREATE UNIQUE INDEX idx_dim_facility_id ON dim_facility(facility_id);

CREATE TABLE fact_claim AS
SELECT
    s.claim_id,
    n.patient_id,
    n.encounter_id,
    p.payer_key,
    f.facility_key,
    s.provider_id,
    s.service_date,
    s.submission_date,
    s.initial_adjudication_date,
    s.first_payment_date,
    s.care_setting,
    s.facility_maturity,
    s.patient_age,
    s.diagnosis_count,
    s.claim_line_count,
    s.distinct_procedure_count,
    s.submission_delay_days,
    s.claim_charge,
    s.expected_allowed_amount,
    s.patient_responsibility,
    s.expected_payer_payment,
    s.actual_payer_payment,
    s.patient_payment,
    s.contractual_adjustment,
    s.outstanding_balance,
    s.underpayment_flag,
    s.underpayment_amount,
    s.payment_received_as_of_flag,
    s.adjudicated_as_of_flag,
    s.initial_denial_as_of_flag,
    s.final_denial_flag,
    s.claim_age_days,
    s.aging_bucket,
    s.timely_filing_risk,
    s.follow_up_priority_score,
    s.follow_up_priority_band,
    s.simulation_seed,
    s.lineage_notice
FROM sim_claim_outcome s
LEFT JOIN stg_claim_native n ON n.claim_id = s.claim_id
LEFT JOIN dim_payer p ON p.payer_category = s.payer_category
LEFT JOIN dim_facility f ON f.facility_id = s.facility_id;

CREATE UNIQUE INDEX idx_fact_claim_id ON fact_claim(claim_id);
CREATE INDEX idx_fact_claim_payer ON fact_claim(payer_key);
CREATE INDEX idx_fact_claim_facility ON fact_claim(facility_key);

CREATE TABLE fact_claim_transaction AS
SELECT
    t.transaction_id,
    t.claim_id,
    t.transaction_type,
    t.transaction_amount,
    t.transaction_start,
    t.transaction_end,
    t.procedure_code,
    t.payments,
    t.adjustments,
    t.transfers,
    t.outstanding,
    t.payer_id,
    t.provider_id
FROM stg_claim_transaction t
INNER JOIN fact_claim c ON c.claim_id = t.claim_id;

CREATE UNIQUE INDEX idx_fact_transaction_id ON fact_claim_transaction(transaction_id);
CREATE INDEX idx_fact_transaction_claim ON fact_claim_transaction(claim_id);

CREATE TABLE fact_denial AS
SELECT
    s.claim_id,
    s.denial_reason,
    s.preventable_denial_flag,
    s.appeal_or_resubmission_flag,
    s.appeal_date,
    s.appeal_decision_date,
    s.appeal_decision_as_of_flag,
    s.appeal_success_as_of_flag,
    s.final_denial_flag,
    s.recovery_amount,
    s.expected_payer_payment AS denied_dollars,
    s.facility_id,
    s.payer_category
FROM sim_claim_outcome s
WHERE s.initial_denial_as_of_flag = 1;

CREATE UNIQUE INDEX idx_fact_denial_claim ON fact_denial(claim_id);
CREATE INDEX idx_fact_denial_reason ON fact_denial(denial_reason);

CREATE VIEW vw_executive_summary AS
SELECT
    COUNT(*) AS claim_count,
    ROUND(SUM(claim_charge), 2) AS total_charges,
    ROUND(SUM(expected_allowed_amount), 2) AS expected_allowed,
    ROUND(SUM(actual_payer_payment), 2) AS payer_payments,
    ROUND(SUM(patient_payment), 2) AS patient_payments,
    ROUND(SUM(outstanding_balance), 2) AS outstanding_balance,
    ROUND(AVG(CASE WHEN adjudicated_as_of_flag = 1 AND payer_key <>
        (SELECT payer_key FROM dim_payer WHERE payer_category = 'Self-Pay')
        THEN initial_denial_as_of_flag END), 4) AS initial_denial_rate,
    ROUND(AVG(CASE WHEN adjudicated_as_of_flag = 1 AND payer_key <>
        (SELECT payer_key FROM dim_payer WHERE payer_category = 'Self-Pay')
        THEN final_denial_flag END), 4) AS final_denial_rate,
    ROUND(AVG(CASE WHEN payment_received_as_of_flag = 1 THEN underpayment_flag END), 4)
        AS underpayment_rate
FROM fact_claim;

CREATE VIEW vw_payer_performance AS
SELECT
    p.payer_category,
    p.fictional_payer_name,
    COUNT(*) AS claim_count,
    SUM(c.adjudicated_as_of_flag) AS adjudicated_claims,
    ROUND(AVG(CASE WHEN c.adjudicated_as_of_flag = 1 THEN c.initial_denial_as_of_flag END), 4)
        AS initial_denial_rate,
    ROUND(AVG(CASE WHEN c.adjudicated_as_of_flag = 1 THEN c.final_denial_flag END), 4)
        AS final_denial_rate,
    ROUND(AVG(CASE WHEN c.payment_received_as_of_flag = 1 THEN c.underpayment_flag END), 4)
        AS underpayment_rate,
    ROUND(SUM(c.expected_payer_payment), 2) AS expected_payer_payment,
    ROUND(SUM(c.actual_payer_payment), 2) AS actual_payer_payment,
    ROUND(SUM(c.underpayment_amount), 2) AS underpayment_amount,
    ROUND(SUM(c.outstanding_balance), 2) AS outstanding_balance
FROM fact_claim c
JOIN dim_payer p ON p.payer_key = c.payer_key
GROUP BY p.payer_category, p.fictional_payer_name;

CREATE VIEW vw_denial_root_cause AS
SELECT
    denial_reason,
    preventable_denial_flag,
    COUNT(*) AS denied_claims,
    ROUND(SUM(denied_dollars), 2) AS denied_dollars,
    SUM(appeal_or_resubmission_flag) AS pursued_claims,
    SUM(appeal_success_as_of_flag) AS successful_appeals,
    ROUND(AVG(CASE WHEN appeal_decision_as_of_flag = 1 THEN appeal_success_as_of_flag END), 4)
        AS decided_appeal_success_rate,
    ROUND(SUM(recovery_amount), 2) AS recovered_dollars,
    SUM(final_denial_flag) AS final_denials
FROM fact_denial
GROUP BY denial_reason, preventable_denial_flag;

CREATE VIEW vw_claims_aging AS
SELECT
    aging_bucket,
    CASE aging_bucket
        WHEN '0-30' THEN 1 WHEN '31-60' THEN 2 WHEN '61-90' THEN 3
        WHEN '91-120' THEN 4 ELSE 5 END AS aging_sort,
    COUNT(*) AS claim_count,
    ROUND(SUM(outstanding_balance), 2) AS outstanding_balance,
    ROUND(AVG(follow_up_priority_score), 2) AS average_priority_score
FROM fact_claim
WHERE outstanding_balance > 0
GROUP BY aging_bucket;

CREATE VIEW vw_follow_up_worklist AS
SELECT
    c.claim_id,
    f.fictional_facility_name,
    p.fictional_payer_name,
    c.service_date,
    c.aging_bucket,
    c.claim_age_days,
    c.outstanding_balance,
    c.final_denial_flag,
    c.underpayment_flag,
    c.timely_filing_risk,
    c.follow_up_priority_score,
    c.follow_up_priority_band
FROM fact_claim c
LEFT JOIN dim_facility f ON f.facility_key = c.facility_key
LEFT JOIN dim_payer p ON p.payer_key = c.payer_key
WHERE c.outstanding_balance > 0
ORDER BY c.follow_up_priority_score DESC, c.outstanding_balance DESC;

CREATE VIEW vw_monthly_revenue_cycle_trend AS
SELECT
    substr(service_date, 1, 7) AS service_month,
    COUNT(*) AS claim_count,
    ROUND(SUM(claim_charge), 2) AS charges,
    ROUND(SUM(actual_payer_payment), 2) AS payer_payments,
    ROUND(SUM(outstanding_balance), 2) AS outstanding_balance,
    ROUND(AVG(CASE WHEN adjudicated_as_of_flag = 1 THEN initial_denial_as_of_flag END), 4)
        AS initial_denial_rate,
    ROUND(AVG(CASE WHEN adjudicated_as_of_flag = 1 THEN final_denial_flag END), 4)
        AS final_denial_rate
FROM fact_claim
GROUP BY substr(service_date, 1, 7);
