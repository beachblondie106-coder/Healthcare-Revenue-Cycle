PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS stg_patient;
DROP TABLE IF EXISTS stg_payer;
DROP TABLE IF EXISTS stg_encounter;
DROP TABLE IF EXISTS stg_claim_native;
DROP TABLE IF EXISTS stg_claim_transaction;
DROP TABLE IF EXISTS sim_claim_outcome;

CREATE TABLE stg_patient (
    patient_id TEXT PRIMARY KEY,
    birth_date TEXT,
    state TEXT,
    county TEXT,
    county_fips TEXT
);

CREATE TABLE stg_payer (
    payer_id TEXT PRIMARY KEY,
    payer_name TEXT NOT NULL,
    ownership TEXT
);

CREATE TABLE stg_encounter (
    encounter_id TEXT PRIMARY KEY,
    encounter_start TEXT,
    encounter_end TEXT,
    patient_id TEXT NOT NULL,
    facility_id TEXT,
    provider_id TEXT,
    payer_id TEXT,
    care_setting TEXT,
    native_total_claim_cost REAL,
    native_payer_coverage REAL
);

CREATE TABLE stg_claim_native (
    claim_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    provider_id TEXT,
    primary_payer_id TEXT,
    secondary_payer_id TEXT,
    encounter_id TEXT,
    service_date TEXT,
    native_status_primary TEXT,
    native_outstanding_primary REAL,
    native_last_billed_date TEXT
);

CREATE TABLE stg_claim_transaction (
    transaction_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    transaction_type TEXT,
    transaction_amount REAL,
    transaction_start TEXT,
    transaction_end TEXT,
    facility_id TEXT,
    procedure_code TEXT,
    payments REAL,
    adjustments REAL,
    transfers REAL,
    outstanding REAL,
    payer_id TEXT,
    provider_id TEXT
);

CREATE TABLE sim_claim_outcome (
    claim_id TEXT PRIMARY KEY,
    simulation_seed INTEGER NOT NULL,
    lineage_notice TEXT NOT NULL,
    service_date TEXT NOT NULL,
    submission_date TEXT NOT NULL,
    initial_adjudication_date TEXT,
    appeal_date TEXT,
    appeal_decision_date TEXT,
    first_payment_date TEXT,
    source_payer_name TEXT,
    payer_category TEXT NOT NULL,
    care_setting TEXT,
    facility_id TEXT,
    provider_id TEXT,
    facility_maturity TEXT,
    source_state TEXT,
    source_county TEXT,
    source_county_fips TEXT,
    patient_age REAL,
    diagnosis_count INTEGER,
    claim_line_count INTEGER,
    distinct_procedure_count INTEGER,
    claim_charge REAL NOT NULL,
    submission_delay_days INTEGER,
    initial_denial_probability REAL,
    adjudicated_as_of_flag INTEGER NOT NULL,
    initial_denial_flag INTEGER NOT NULL,
    initial_denial_as_of_flag INTEGER NOT NULL,
    denial_reason TEXT,
    preventable_denial_flag INTEGER NOT NULL,
    appeal_or_resubmission_flag INTEGER NOT NULL,
    appeal_success_flag INTEGER NOT NULL,
    appeal_decision_as_of_flag INTEGER NOT NULL,
    appeal_success_as_of_flag INTEGER NOT NULL,
    final_denial_flag INTEGER NOT NULL,
    expected_allowed_amount REAL NOT NULL,
    patient_responsibility REAL NOT NULL,
    expected_payer_payment REAL NOT NULL,
    actual_payer_payment REAL NOT NULL,
    payment_received_as_of_flag INTEGER NOT NULL,
    underpayment_flag INTEGER NOT NULL,
    underpayment_amount REAL NOT NULL,
    recovery_amount REAL NOT NULL,
    patient_payment REAL NOT NULL,
    contractual_adjustment REAL NOT NULL,
    outstanding_balance REAL NOT NULL,
    claim_age_days INTEGER NOT NULL,
    aging_bucket TEXT NOT NULL,
    timely_filing_risk REAL NOT NULL,
    follow_up_priority_score REAL NOT NULL,
    follow_up_priority_band TEXT NOT NULL
);

CREATE INDEX idx_stg_claim_patient ON stg_claim_native(patient_id);
CREATE INDEX idx_stg_claim_encounter ON stg_claim_native(encounter_id);
CREATE INDEX idx_stg_transaction_claim ON stg_claim_transaction(claim_id);
CREATE INDEX idx_sim_payer ON sim_claim_outcome(payer_category);
CREATE INDEX idx_sim_facility ON sim_claim_outcome(facility_id);
CREATE INDEX idx_sim_service_date ON sim_claim_outcome(service_date);
CREATE INDEX idx_sim_denial ON sim_claim_outcome(initial_denial_as_of_flag, final_denial_flag);
