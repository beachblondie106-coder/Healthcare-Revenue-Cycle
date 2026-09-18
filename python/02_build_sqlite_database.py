#!/usr/bin/env python3
"""Load native Synthea and simulated claims into the portfolio SQLite model."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd


def read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def bool_to_int(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.columns:
        if result[column].dtype == bool:
            result[column] = result[column].astype(int)
        elif str(result[column].dtype) == "object":
            lowered = result[column].dropna().astype(str).str.lower().unique()
            if len(lowered) and set(lowered).issubset({"true", "false"}):
                result[column] = result[column].map(
                    {True: 1, False: 0, "True": 1, "False": 0, "true": 1, "false": 0}
                )
    return result


def load_frame(connection: sqlite3.Connection, table: str, frame: pd.DataFrame) -> None:
    clean = bool_to_int(frame).where(pd.notna(frame), None)
    columns = list(clean.columns)
    placeholders = ", ".join(["?"] * len(columns))
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    connection.executemany(sql, clean.itertuples(index=False, name=None))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-dir", required=True, type=Path)
    parser.add_argument("--simulation-file", required=True, type=Path)
    parser.add_argument("--sql-dir", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--qa-output", required=True, type=Path)
    args = parser.parse_args()

    args.database.parent.mkdir(parents=True, exist_ok=True)
    args.qa_output.parent.mkdir(parents=True, exist_ok=True)
    if args.database.exists():
        args.database.unlink()

    connection = sqlite3.connect(args.database)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(read_sql(args.sql_dir / "01_create_schema.sql"))

    patients = pd.read_csv(args.native_dir / "patients.csv", dtype=str)[
        ["Id", "BIRTHDATE", "STATE", "COUNTY", "FIPS"]
    ].rename(columns={
        "Id": "patient_id", "BIRTHDATE": "birth_date", "STATE": "state",
        "COUNTY": "county", "FIPS": "county_fips",
    })
    payers = pd.read_csv(args.native_dir / "payers.csv", dtype=str)[
        ["Id", "NAME", "OWNERSHIP"]
    ].rename(columns={"Id": "payer_id", "NAME": "payer_name", "OWNERSHIP": "ownership"})
    encounters = pd.read_csv(args.native_dir / "encounters.csv", low_memory=False)[
        ["Id", "START", "STOP", "PATIENT", "ORGANIZATION", "PROVIDER", "PAYER",
         "ENCOUNTERCLASS", "TOTAL_CLAIM_COST", "PAYER_COVERAGE"]
    ].rename(columns={
        "Id": "encounter_id", "START": "encounter_start", "STOP": "encounter_end",
        "PATIENT": "patient_id", "ORGANIZATION": "facility_id", "PROVIDER": "provider_id",
        "PAYER": "payer_id", "ENCOUNTERCLASS": "care_setting",
        "TOTAL_CLAIM_COST": "native_total_claim_cost", "PAYER_COVERAGE": "native_payer_coverage",
    })
    claims = pd.read_csv(args.native_dir / "claims.csv", low_memory=False)[
        ["Id", "PATIENTID", "PROVIDERID", "PRIMARYPATIENTINSURANCEID",
         "SECONDARYPATIENTINSURANCEID", "APPOINTMENTID", "SERVICEDATE", "STATUS1",
         "OUTSTANDING1", "LASTBILLEDDATE1"]
    ].rename(columns={
        "Id": "claim_id", "PATIENTID": "patient_id", "PROVIDERID": "provider_id",
        "PRIMARYPATIENTINSURANCEID": "primary_payer_id",
        "SECONDARYPATIENTINSURANCEID": "secondary_payer_id",
        "APPOINTMENTID": "encounter_id", "SERVICEDATE": "service_date",
        "STATUS1": "native_status_primary", "OUTSTANDING1": "native_outstanding_primary",
        "LASTBILLEDDATE1": "native_last_billed_date",
    })
    transactions = pd.read_csv(args.native_dir / "claims_transactions.csv", low_memory=False)[
        ["ID", "CLAIMID", "TYPE", "AMOUNT", "FROMDATE", "TODATE", "PLACEOFSERVICE",
         "PROCEDURECODE", "PAYMENTS", "ADJUSTMENTS", "TRANSFERS", "OUTSTANDING",
         "PATIENTINSURANCEID", "PROVIDERID"]
    ].rename(columns={
        "ID": "transaction_id", "CLAIMID": "claim_id", "TYPE": "transaction_type",
        "AMOUNT": "transaction_amount", "FROMDATE": "transaction_start",
        "TODATE": "transaction_end", "PLACEOFSERVICE": "facility_id",
        "PROCEDURECODE": "procedure_code", "PAYMENTS": "payments",
        "ADJUSTMENTS": "adjustments", "TRANSFERS": "transfers",
        "OUTSTANDING": "outstanding", "PATIENTINSURANCEID": "payer_id",
        "PROVIDERID": "provider_id",
    })

    simulation = pd.read_csv(args.simulation_file, low_memory=False).rename(
        columns={"PROVIDERID": "provider_id"}
    )
    simulation_columns = [
        "claim_id", "simulation_seed", "lineage_notice", "service_date", "submission_date",
        "initial_adjudication_date", "appeal_date", "appeal_decision_date",
        "first_payment_date", "source_payer_name", "payer_category", "care_setting",
        "facility_id", "provider_id", "facility_maturity", "source_state", "source_county",
        "source_county_fips", "patient_age", "diagnosis_count", "claim_line_count",
        "distinct_procedure_count", "claim_charge", "submission_delay_days",
        "initial_denial_probability", "adjudicated_as_of_flag", "initial_denial_flag",
        "initial_denial_as_of_flag", "denial_reason", "preventable_denial_flag",
        "appeal_or_resubmission_flag", "appeal_success_flag", "appeal_decision_as_of_flag",
        "appeal_success_as_of_flag", "final_denial_flag", "expected_allowed_amount",
        "patient_responsibility", "expected_payer_payment", "actual_payer_payment",
        "payment_received_as_of_flag", "underpayment_flag", "underpayment_amount",
        "recovery_amount", "patient_payment", "contractual_adjustment", "outstanding_balance",
        "claim_age_days", "aging_bucket", "timely_filing_risk",
        "follow_up_priority_score", "follow_up_priority_band",
    ]

    with connection:
        load_frame(connection, "stg_patient", patients)
        load_frame(connection, "stg_payer", payers)
        load_frame(connection, "stg_encounter", encounters)
        load_frame(connection, "stg_claim_native", claims)
        load_frame(connection, "stg_claim_transaction", transactions)
        load_frame(connection, "sim_claim_outcome", simulation[simulation_columns])

    connection.executescript(read_sql(args.sql_dir / "02_build_analytics.sql"))
    qa = pd.read_sql_query(read_sql(args.sql_dir / "03_qa_queries.sql"), connection)
    qa.to_csv(args.qa_output, index=False)
    summary = pd.read_sql_query("SELECT * FROM vw_executive_summary", connection)
    connection.close()

    if not qa["status"].eq("PASS").all():
        failures = qa.loc[qa["status"].ne("PASS"), "check_name"].tolist()
        raise RuntimeError(f"SQL QA failed: {failures}")

    print(summary.to_string(index=False))
    print(f"SQL QA checks passed: {len(qa)}/{len(qa)}")


if __name__ == "__main__":
    main()
