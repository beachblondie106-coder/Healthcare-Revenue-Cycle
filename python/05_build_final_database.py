#!/usr/bin/env python3
"""Build the final analytical SQLite database from constructed synthetic claims."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd


def read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_frame(con: sqlite3.Connection, table: str, frame: pd.DataFrame) -> None:
    clean = frame.copy()
    for col in clean.columns:
        if clean[col].dtype == bool:
            clean[col] = clean[col].astype(int)
    clean = clean.astype(object).where(pd.notna(clean), None)
    cols = list(clean.columns)
    placeholders = ",".join(["?"] * len(cols))
    con.executemany(
        f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
        clean.itertuples(index=False, name=None),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claims-file", required=True, type=Path)
    parser.add_argument("--sql-dir", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--qa-output", required=True, type=Path)
    args = parser.parse_args()
    args.database.parent.mkdir(parents=True, exist_ok=True)
    args.qa_output.parent.mkdir(parents=True, exist_ok=True)
    if args.database.exists():
        args.database.unlink()

    data = pd.read_csv(args.claims_file, low_memory=False).rename(columns={"PROVIDERID": "provider_id"})
    sim_columns = [
        "claim_id","simulation_seed","lineage_notice","service_date","submission_date",
        "initial_adjudication_date","appeal_date","appeal_decision_date","first_payment_date",
        "source_payer_name","payer_category","care_setting","facility_id","provider_id",
        "facility_maturity","source_state","source_county","source_county_fips","patient_age",
        "diagnosis_count","claim_line_count","distinct_procedure_count","claim_charge",
        "submission_delay_days","initial_denial_probability","adjudicated_as_of_flag",
        "initial_denial_flag","initial_denial_as_of_flag","denial_reason","preventable_denial_flag",
        "appeal_or_resubmission_flag","appeal_success_flag","appeal_decision_as_of_flag",
        "appeal_success_as_of_flag","final_denial_flag","expected_allowed_amount",
        "patient_responsibility","expected_payer_payment","actual_payer_payment",
        "payment_received_as_of_flag","underpayment_flag","underpayment_amount","recovery_amount",
        "patient_payment","contractual_adjustment","outstanding_balance","claim_age_days",
        "aging_bucket","timely_filing_risk","follow_up_priority_score","follow_up_priority_band",
    ]
    native_claim = data[["claim_id","PATIENTID","provider_id","encounter_id","service_date"]].rename(
        columns={"PATIENTID":"patient_id"}
    )
    native_claim["primary_payer_id"] = None
    native_claim["secondary_payer_id"] = None
    native_claim["native_status_primary"] = None
    native_claim["native_outstanding_primary"] = None
    native_claim["native_last_billed_date"] = None
    native_claim = native_claim[["claim_id","patient_id","provider_id","primary_payer_id",
        "secondary_payer_id","encounter_id","service_date","native_status_primary",
        "native_outstanding_primary","native_last_billed_date"]]

    con = sqlite3.connect(args.database)
    con.executescript(read_sql(args.sql_dir / "01_create_schema.sql"))
    with con:
        load_frame(con, "stg_claim_native", native_claim)
        load_frame(con, "sim_claim_outcome", data[sim_columns])
    con.executescript(read_sql(args.sql_dir / "02_build_analytics.sql"))
    qa = pd.read_sql_query(read_sql(args.sql_dir / "04_qa_final.sql"), con)
    summary = pd.read_sql_query("SELECT * FROM vw_executive_summary", con)
    state_summary = pd.read_sql_query(
        "SELECT source_state, COUNT(*) claim_count, ROUND(AVG(initial_denial_as_of_flag),4) initial_denial_rate FROM sim_claim_outcome WHERE adjudicated_as_of_flag=1 AND payer_category<>'Self-Pay' GROUP BY source_state ORDER BY source_state",
        con,
    )
    qa.to_csv(args.qa_output, index=False)
    state_summary.to_csv(args.qa_output.with_name("final_state_summary.csv"), index=False)
    con.close()
    if not qa.status.eq("PASS").all():
        raise RuntimeError(qa.loc[qa.status.ne("PASS"),"check_name"].tolist())
    print(summary.to_string(index=False))
    print(f"Final SQL QA checks passed: {len(qa)}/{len(qa)}")


if __name__ == "__main__":
    main()
