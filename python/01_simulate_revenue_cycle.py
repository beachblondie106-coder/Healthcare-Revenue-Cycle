#!/usr/bin/env python3
"""Create reproducible fictional revenue-cycle outcomes from Synthea CSV claims.

All operational outcomes produced by this script are simulated for portfolio
demonstration. They do not represent real payer, provider, facility, or state
performance.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 20260917
ANALYSIS_START = pd.Timestamp("2024-01-01", tz="UTC")
ANALYSIS_END_EXCLUSIVE = pd.Timestamp("2026-01-01", tz="UTC")
AS_OF_DATE = pd.Timestamp("2025-12-31", tz="UTC")

PAYER_BASE = {
    "Medicare": 0.080,
    "Medicare Advantage": 0.115,
    "Medicaid": 0.105,
    "Commercial": 0.090,
}

ALLOWED_FACTOR = {
    "Medicare": 0.42,
    "Medicare Advantage": 0.45,
    "Medicaid": 0.32,
    "Commercial": 0.55,
    "Self-Pay": 0.20,
}

ADJUDICATION_DAYS = {
    "Medicare": 18,
    "Medicare Advantage": 24,
    "Medicaid": 25,
    "Commercial": 21,
}

CARE_ADJUSTMENT = {
    "inpatient": 0.025,
    "outpatient": 0.010,
    "emergency": -0.005,
    "ambulatory": 0.000,
    "urgentcare": -0.005,
    "home": 0.015,
    "snf": 0.015,
    "hospice": 0.015,
    "wellness": -0.015,
    "virtual": -0.015,
}

FACILITY_ADJUSTMENT = {
    "Optimized": -0.020,
    "Standard": 0.000,
    "Improvement Opportunity": 0.030,
}

APPEAL_RULES = {
    "Eligibility/Coverage": (0.70, 0.68, 0.90, 1.00),
    "Authorization": (0.65, 0.48, 0.80, 1.00),
    "Coding": (0.78, 0.72, 0.90, 1.00),
    "Documentation": (0.72, 0.62, 0.85, 1.00),
    "Duplicate Claim": (0.35, 0.15, 0.75, 1.00),
    "Timely Filing": (0.40, 0.22, 0.70, 1.00),
    "Medical Necessity": (0.75, 0.52, 0.80, 1.00),
    "Other/Payer Processing": (0.68, 0.58, 0.85, 1.00),
}

PREVENTABLE = {
    "Eligibility/Coverage": True,
    "Authorization": True,
    "Coding": True,
    "Documentation": True,
    "Duplicate Claim": True,
    "Timely Filing": True,
    "Medical Necessity": False,
    "Other/Payer Processing": False,
}

FALLBACK_REASONS = np.array(
    [
        "Eligibility/Coverage",
        "Authorization",
        "Coding",
        "Documentation",
        "Duplicate Claim",
        "Timely Filing",
        "Medical Necessity",
        "Other/Payer Processing",
    ]
)

FALLBACK_WEIGHTS = np.array([0.22, 0.20, 0.18, 0.15, 0.08, 0.06, 0.07, 0.04])


def stable_bucket(value: object, modulus: int = 100) -> int:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulus


def facility_maturity(provider_id: object) -> str:
    bucket = stable_bucket(provider_id)
    if bucket < 25:
        return "Optimized"
    if bucket < 75:
        return "Standard"
    return "Improvement Opportunity"


def payer_category(source_name: object, patient_age: float) -> str:
    name = str(source_name) if pd.notna(source_name) else "NO_INSURANCE"
    if name == "Medicare":
        return "Medicare"
    if name == "Medicaid":
        return "Medicaid"
    if name == "Dual Eligible":
        return "Medicare Advantage"
    if name == "NO_INSURANCE":
        return "Self-Pay"
    if patient_age >= 65 and name in {"Humana", "UnitedHealthcare", "Aetna", "Anthem"}:
        return "Medicare Advantage"
    return "Commercial"


def denial_reason(row: pd.Series, rng: np.random.Generator) -> str:
    if row["duplicate_signature_flag"]:
        return "Duplicate Claim"
    if row["missing_primary_coverage_flag"]:
        return "Eligibility/Coverage"
    if row["submission_delay_days"] > 20:
        return "Timely Filing"
    if row["authorization_risk_flag"]:
        return "Authorization"
    if row["documentation_risk_flag"]:
        return "Documentation"
    if row["coding_risk_flag"]:
        return "Coding"
    if row["high_charge_flag"]:
        return "Medical Necessity"
    return str(rng.choice(FALLBACK_REASONS, p=FALLBACK_WEIGHTS))


def age_bucket(days: int) -> str:
    if days <= 30:
        return "0-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    if days <= 120:
        return "91-120"
    return "Over 120"


def minmax(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.0, index=series.index)
    return (series - lo) / (hi - lo)


def load_source(input_dir: Path) -> pd.DataFrame:
    claims = pd.read_csv(input_dir / "claims.csv", low_memory=False)
    transactions = pd.read_csv(input_dir / "claims_transactions.csv", low_memory=False)
    encounters = pd.read_csv(input_dir / "encounters.csv", low_memory=False)
    payers = pd.read_csv(input_dir / "payers.csv", low_memory=False)
    patients = pd.read_csv(input_dir / "patients.csv", low_memory=False)

    claims["service_date"] = pd.to_datetime(claims["SERVICEDATE"], utc=True)
    claims = claims.loc[
        (claims["service_date"] >= ANALYSIS_START)
        & (claims["service_date"] < ANALYSIS_END_EXCLUSIVE)
    ].copy()

    charge_tx = transactions.loc[transactions["TYPE"].eq("CHARGE")].copy()
    charge_tx["native_charge"] = pd.to_numeric(charge_tx["AMOUNT"], errors="coerce").fillna(0)
    charge_summary = charge_tx.groupby("CLAIMID", as_index=False).agg(
        claim_charge=("native_charge", "sum"),
        claim_line_count=("ID", "count"),
        distinct_procedure_count=("PROCEDURECODE", "nunique"),
    )

    encounter_fields = encounters[
        ["Id", "ENCOUNTERCLASS", "ORGANIZATION", "REASONCODE", "REASONDESCRIPTION"]
    ].rename(
        columns={
            "Id": "encounter_id",
            "ENCOUNTERCLASS": "care_setting",
            "ORGANIZATION": "facility_id",
            "REASONCODE": "encounter_reason_code",
            "REASONDESCRIPTION": "encounter_reason_description",
        }
    )

    payer_lookup = payers[["Id", "NAME"]].rename(
        columns={"Id": "payer_id", "NAME": "source_payer_name"}
    )
    patient_fields = patients[["Id", "BIRTHDATE", "STATE", "COUNTY", "FIPS"]].rename(
        columns={
            "Id": "patient_id",
            "BIRTHDATE": "birth_date",
            "STATE": "source_state",
            "COUNTY": "source_county",
            "FIPS": "source_county_fips",
        }
    )
    patient_fields["birth_date"] = pd.to_datetime(patient_fields["birth_date"], utc=True)

    diagnosis_cols = [f"DIAGNOSIS{i}" for i in range(1, 9)]
    claims["diagnosis_count"] = claims[diagnosis_cols].notna().sum(axis=1)

    data = (
        claims.merge(charge_summary, left_on="Id", right_on="CLAIMID", how="left")
        .merge(encounter_fields, left_on="APPOINTMENTID", right_on="encounter_id", how="left")
        .merge(payer_lookup, left_on="PRIMARYPATIENTINSURANCEID", right_on="payer_id", how="left")
        .merge(patient_fields, left_on="PATIENTID", right_on="patient_id", how="left")
    )
    data["claim_charge"] = data["claim_charge"].fillna(0).round(2)
    data["claim_line_count"] = data["claim_line_count"].fillna(0).astype(int)
    data["distinct_procedure_count"] = data["distinct_procedure_count"].fillna(0).astype(int)
    data["patient_age"] = ((data["service_date"] - data["birth_date"]).dt.days / 365.25).clip(lower=0)
    data["payer_category"] = [
        payer_category(name, age)
        for name, age in zip(data["source_payer_name"], data["patient_age"])
    ]
    return data


def simulate(data: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    n = len(data)
    out = data.copy()
    out["claim_id"] = out["Id"]
    out["facility_maturity"] = out["PROVIDERID"].map(facility_maturity)

    out["documentation_risk_flag"] = rng.random(n) < 0.08
    base_delay = rng.triangular(1, 4, 12, n).round().astype(int)
    documentation_delay = np.where(out["documentation_risk_flag"], rng.integers(3, 13, n), 0)
    out["submission_delay_days"] = base_delay + documentation_delay
    out["submission_date"] = out["service_date"] + pd.to_timedelta(
        out["submission_delay_days"], unit="D"
    )

    out["missing_primary_coverage_flag"] = out["PRIMARYPATIENTINSURANCEID"].isna()
    out["secondary_coordination_flag"] = out["SECONDARYPATIENTINSURANCEID"].notna()
    out["duplicate_signature_flag"] = rng.random(n) < 0.012
    out["coding_risk_flag"] = (out["diagnosis_count"] >= 3) | (out["claim_line_count"] >= 5)
    out["authorization_risk_flag"] = out["care_setting"].isin(["inpatient", "outpatient", "snf"])
    high_charge_threshold = out["claim_charge"].quantile(0.90)
    out["high_charge_flag"] = out["claim_charge"] >= high_charge_threshold

    out["payer_base_probability"] = out["payer_category"].map(PAYER_BASE)
    out["care_setting_adjustment"] = out["care_setting"].map(CARE_ADJUSTMENT).fillna(0)
    out["facility_adjustment"] = out["facility_maturity"].map(FACILITY_ADJUSTMENT)

    risk = out["payer_base_probability"].fillna(0)
    risk += out["care_setting_adjustment"] + out["facility_adjustment"]
    risk += out["missing_primary_coverage_flag"] * 0.120
    risk += out["secondary_coordination_flag"] * 0.025
    risk += out["authorization_risk_flag"] * 0.035
    risk += (out["diagnosis_count"] >= 2) * 0.015
    risk += (out["claim_line_count"] >= 2) * 0.010
    risk += out["high_charge_flag"] * 0.020
    risk += (out["submission_delay_days"] > 10) * 0.025
    risk += (out["submission_delay_days"] > 20) * 0.040
    risk += out["duplicate_signature_flag"] * 0.200
    risk += out["documentation_risk_flag"] * 0.060

    insured = out["payer_category"].ne("Self-Pay")
    out["initial_denial_probability"] = risk.clip(0.020, 0.400).where(insured)
    out["initial_denial_flag"] = False
    out.loc[insured, "initial_denial_flag"] = (
        rng.random(insured.sum()) < out.loc[insured, "initial_denial_probability"]
    )

    out["denial_reason"] = pd.NA
    denied_index = out.index[out["initial_denial_flag"]]
    out.loc[denied_index, "denial_reason"] = [
        denial_reason(out.loc[i], rng) for i in denied_index
    ]
    out["preventable_denial_flag"] = (
        out["denial_reason"].map(PREVENTABLE).astype("boolean").fillna(False).astype(bool)
    )

    standard_days = out["payer_category"].map(ADJUDICATION_DAYS).fillna(0).astype(int)
    variation = rng.integers(-5, 11, n)
    adjudication_days = (standard_days + variation).clip(lower=7)
    out["initial_adjudication_date"] = (
        out["submission_date"] + pd.to_timedelta(adjudication_days, unit="D")
    ).where(insured)

    out["appeal_or_resubmission_flag"] = False
    out["appeal_success_flag"] = False
    out["recovery_factor"] = 0.0
    for i in denied_index:
        reason = str(out.at[i, "denial_reason"])
        propensity, success_probability, recovery_low, recovery_high = APPEAL_RULES[reason]
        pursued = rng.random() < propensity
        success = pursued and (rng.random() < success_probability)
        out.at[i, "appeal_or_resubmission_flag"] = pursued
        out.at[i, "appeal_success_flag"] = success
        if success:
            out.at[i, "recovery_factor"] = rng.uniform(recovery_low, recovery_high)

    out["appeal_date"] = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns, UTC]")
    pursued = out["appeal_or_resubmission_flag"]
    out.loc[pursued, "appeal_date"] = out.loc[pursued, "initial_adjudication_date"] + pd.to_timedelta(
        rng.integers(7, 36, pursued.sum()), unit="D"
    )
    out["appeal_decision_date"] = pd.Series(
        pd.NaT, index=out.index, dtype="datetime64[ns, UTC]"
    )
    out.loc[pursued, "appeal_decision_date"] = out.loc[pursued, "appeal_date"] + pd.to_timedelta(
        rng.integers(10, 46, pursued.sum()), unit="D"
    )

    contract_variation = rng.uniform(0.92, 1.08, n)
    out["expected_allowed_amount"] = (
        out["claim_charge"] * out["payer_category"].map(ALLOWED_FACTOR) * contract_variation
    ).round(2)
    patient_share_base = out["payer_category"].map(
        {"Medicare": 0.20, "Medicare Advantage": 0.17, "Medicaid": 0.05,
         "Commercial": 0.18, "Self-Pay": 1.00}
    )
    patient_share = (patient_share_base * rng.uniform(0.85, 1.15, n)).clip(0, 1)
    out["patient_responsibility"] = (out["expected_allowed_amount"] * patient_share).round(2)
    out["expected_payer_payment"] = (
        out["expected_allowed_amount"] - out["patient_responsibility"]
    ).clip(lower=0).round(2)

    out["adjudicated_as_of_flag"] = (
        out["initial_adjudication_date"].notna()
        & (out["initial_adjudication_date"] <= AS_OF_DATE)
    )
    out["appeal_decision_as_of_flag"] = (
        out["appeal_decision_date"].notna()
        & (out["appeal_decision_date"] <= AS_OF_DATE)
    )
    out["initial_denial_as_of_flag"] = (
        out["initial_denial_flag"] & out["adjudicated_as_of_flag"]
    )
    out["appeal_success_as_of_flag"] = (
        out["appeal_success_flag"] & out["appeal_decision_as_of_flag"]
    )
    out["final_denial_flag"] = (
        out["initial_denial_as_of_flag"]
        & (
            ~out["appeal_or_resubmission_flag"]
            | (out["appeal_decision_as_of_flag"] & ~out["appeal_success_flag"])
        )
    )

    payable_eventually = (insured & ~out["initial_denial_flag"]) | out["appeal_success_flag"]
    underpaid_event = payable_eventually & (rng.random(n) < 0.10)
    severity = rng.uniform(0.05, 0.20, n)
    payment_factor = np.where(out["appeal_success_flag"], out["recovery_factor"], 1.0)
    payment_factor = np.where(underpaid_event, payment_factor * (1 - severity), payment_factor)
    out["eventual_payer_payment"] = np.where(
        payable_eventually, out["expected_payer_payment"] * payment_factor, 0.0
    ).round(2)

    out["patient_payment"] = np.where(
        out["payer_category"].eq("Self-Pay"),
        out["patient_responsibility"] * rng.uniform(0.20, 0.75, n),
        out["patient_responsibility"] * rng.uniform(0.65, 1.00, n),
    ).round(2)
    out["contractual_adjustment"] = (
        out["claim_charge"] - out["expected_allowed_amount"]
    ).clip(lower=0).round(2)
    out["first_payment_date"] = pd.Series(
        pd.NaT, index=out.index, dtype="datetime64[ns, UTC]"
    )
    clean_payable = insured & ~out["initial_denial_flag"]
    out.loc[clean_payable, "first_payment_date"] = out.loc[
        clean_payable, "initial_adjudication_date"
    ] + pd.to_timedelta(rng.integers(3, 26, clean_payable.sum()), unit="D")
    recovered = out["appeal_success_flag"]
    out.loc[recovered, "first_payment_date"] = out.loc[
        recovered, "appeal_decision_date"
    ] + pd.to_timedelta(rng.integers(3, 21, recovered.sum()), unit="D")

    out["payment_received_as_of_flag"] = (
        out["first_payment_date"].notna() & (out["first_payment_date"] <= AS_OF_DATE)
    )
    out["actual_payer_payment"] = np.where(
        out["payment_received_as_of_flag"], out["eventual_payer_payment"], 0.0
    ).round(2)
    out["underpayment_flag"] = underpaid_event & out["payment_received_as_of_flag"]
    out["underpayment_amount"] = np.where(
        out["underpayment_flag"],
        out["expected_payer_payment"] - out["actual_payer_payment"],
        0.0,
    ).round(2)
    out["recovery_amount"] = np.where(
        out["appeal_success_as_of_flag"] & out["payment_received_as_of_flag"],
        out["actual_payer_payment"],
        0.0,
    ).round(2)
    patient_payment_realized = np.where(
        out["service_date"] <= AS_OF_DATE, out["patient_payment"], 0.0
    )
    out["outstanding_balance"] = (
        out["expected_allowed_amount"]
        - out["actual_payer_payment"]
        - patient_payment_realized
    ).clip(lower=0).round(2)

    out["claim_age_days"] = (AS_OF_DATE - out["submission_date"]).dt.days.clip(lower=0)
    out["aging_bucket"] = out["claim_age_days"].map(age_bucket)
    out["timely_filing_risk"] = ((out["claim_age_days"] >= 90) & (out["outstanding_balance"] > 0)).astype(float)

    recovery_likelihood = out["denial_reason"].map(
        {reason: values[1] for reason, values in APPEAL_RULES.items()}
    ).fillna(0.90)
    priority = (
        0.40 * minmax(out["outstanding_balance"])
        + 0.25 * minmax(out["claim_age_days"])
        + 0.20 * recovery_likelihood
        + 0.15 * out["timely_filing_risk"]
    ) * 100
    out["follow_up_priority_score"] = priority.round(2)
    out["follow_up_priority_band"] = pd.cut(
        out["follow_up_priority_score"],
        bins=[-np.inf, 40, 70, np.inf],
        labels=["Low", "Medium", "High"],
        right=False,
    ).astype(str)

    keep = [
        "claim_id", "PATIENTID", "encounter_id", "service_date", "submission_date",
        "initial_adjudication_date", "appeal_date", "appeal_decision_date",
        "first_payment_date", "source_payer_name", "payer_category", "care_setting",
        "facility_id", "PROVIDERID", "facility_maturity", "source_state",
        "source_county", "source_county_fips", "patient_age", "diagnosis_count",
        "claim_line_count", "distinct_procedure_count", "claim_charge",
        "missing_primary_coverage_flag", "secondary_coordination_flag",
        "duplicate_signature_flag", "documentation_risk_flag", "coding_risk_flag",
        "authorization_risk_flag", "high_charge_flag", "submission_delay_days",
        "initial_denial_probability", "adjudicated_as_of_flag", "initial_denial_flag",
        "initial_denial_as_of_flag", "denial_reason", "preventable_denial_flag",
        "appeal_or_resubmission_flag", "appeal_success_flag",
        "appeal_decision_as_of_flag", "appeal_success_as_of_flag",
        "final_denial_flag", "expected_allowed_amount",
        "patient_responsibility", "expected_payer_payment", "actual_payer_payment",
        "payment_received_as_of_flag", "underpayment_flag", "underpayment_amount",
        "recovery_amount",
        "patient_payment", "contractual_adjustment", "outstanding_balance",
        "claim_age_days", "aging_bucket", "timely_filing_risk",
        "follow_up_priority_score", "follow_up_priority_band",
    ]
    result = out[keep].copy()
    result.insert(0, "simulation_seed", SEED)
    result.insert(1, "lineage_notice", "SIMULATED PORTFOLIO DATA")
    return result


def validate(result: pd.DataFrame) -> pd.DataFrame:
    insured = result["payer_category"].ne("Self-Pay")
    checks = [
        ("claim_id_unique", result["claim_id"].is_unique),
        ("no_negative_charge", result["claim_charge"].ge(0).all()),
        ("no_negative_outstanding", result["outstanding_balance"].ge(0).all()),
        ("submission_not_before_service", (result["submission_date"] >= result["service_date"]).all()),
        (
            "adjudication_not_before_submission",
            (result.loc[insured, "initial_adjudication_date"] >= result.loc[insured, "submission_date"]).all(),
        ),
        (
            "final_denials_subset_initial",
            (~result["final_denial_flag"] | result["initial_denial_flag"]).all(),
        ),
        (
            "successful_appeals_not_final_denials",
            (~result["appeal_success_as_of_flag"] | ~result["final_denial_flag"]).all(),
        ),
        (
            "self_pay_denial_probability_null",
            result.loc[~insured, "initial_denial_probability"].isna().all(),
        ),
    ]
    return pd.DataFrame(checks, columns=["check_name", "passed"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = load_source(args.input_dir)
    result = simulate(source)
    qa = validate(result)

    if not qa["passed"].all():
        failed = qa.loc[~qa["passed"], "check_name"].tolist()
        raise RuntimeError(f"Simulation QA failed: {failed}")

    result.to_csv(args.output_dir / "pilot_simulated_claims.csv", index=False)
    qa.to_csv(args.output_dir / "pilot_simulation_qa.csv", index=False)

    insured = result["payer_category"].ne("Self-Pay")
    adjudicated = insured & result["adjudicated_as_of_flag"]
    pursued_decided = (
        result["appeal_or_resubmission_flag"] & result["appeal_decision_as_of_flag"]
    )
    paid = result["payment_received_as_of_flag"]
    summary = pd.DataFrame(
        {
            "metric": [
                "claim_count", "insured_claim_count", "initial_denial_rate",
                "final_denial_rate", "appeal_success_rate", "preventable_denial_share",
                "underpayment_rate", "total_claim_charges", "total_expected_allowed",
                "total_actual_payer_payment", "total_outstanding_balance",
            ],
            "value": [
                len(result), insured.sum(),
                result.loc[adjudicated, "initial_denial_as_of_flag"].mean(),
                result.loc[adjudicated, "final_denial_flag"].mean(),
                result.loc[pursued_decided, "appeal_success_as_of_flag"].mean(),
                result.loc[result["initial_denial_as_of_flag"], "preventable_denial_flag"].mean(),
                result.loc[paid, "underpayment_flag"].mean(),
                result["claim_charge"].sum(), result["expected_allowed_amount"].sum(),
                result["actual_payer_payment"].sum(), result["outstanding_balance"].sum(),
            ],
        }
    )
    summary.to_csv(args.output_dir / "pilot_simulation_summary.csv", index=False)

    print(summary.to_string(index=False))
    print(f"QA checks passed: {qa['passed'].sum()}/{len(qa)}")


if __name__ == "__main__":
    main()
