#!/usr/bin/env python3
"""Generate a reproducible 90,000-claim synthetic multistate portfolio dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 20260917
AS_OF = pd.Timestamp("2025-12-31", tz="UTC")
STATES = [
    "Florida", "Alabama", "Tennessee", "North Carolina", "Texas",
    "New York", "Wisconsin", "Montana", "Arizona", "California",
]
PAYER_CATEGORIES = ["Medicare", "Medicare Advantage", "Medicaid", "Commercial", "Self-Pay"]
PAYER_MIX = [0.28, 0.12, 0.18, 0.32, 0.10]
PAYER_BASE = {"Medicare": .08, "Medicare Advantage": .115, "Medicaid": .105, "Commercial": .09}
ALLOWED = {"Medicare": .42, "Medicare Advantage": .45, "Medicaid": .32, "Commercial": .55, "Self-Pay": .20}
ADJ_DAYS = {"Medicare": 18, "Medicare Advantage": 24, "Medicaid": 25, "Commercial": 21}
CARE = ["inpatient", "outpatient", "emergency", "ambulatory", "urgentcare", "home", "snf", "hospice", "wellness", "virtual"]
CARE_MIX = [.08, .20, .11, .34, .07, .03, .02, .01, .11, .03]
CARE_ADJ = {"inpatient":.025,"outpatient":.01,"emergency":-.005,"ambulatory":0,"urgentcare":-.005,"home":.015,"snf":.015,"hospice":.015,"wellness":-.015,"virtual":-.015}
MATURITY_ADJ = {"Optimized": -.02, "Standard": 0, "Improvement Opportunity": .03}
REASONS = np.array(["Eligibility/Coverage","Authorization","Coding","Documentation","Duplicate Claim","Timely Filing","Medical Necessity","Other/Payer Processing"])
REASON_W = np.array([.22,.20,.18,.15,.08,.06,.07,.04])
PREVENTABLE = {"Eligibility/Coverage":1,"Authorization":1,"Coding":1,"Documentation":1,"Duplicate Claim":1,"Timely Filing":1,"Medical Necessity":0,"Other/Payer Processing":0}
APPEAL = {"Eligibility/Coverage":(.70,.68,.90,1.0),"Authorization":(.65,.48,.80,1.0),"Coding":(.78,.72,.90,1.0),"Documentation":(.72,.62,.85,1.0),"Duplicate Claim":(.35,.15,.75,1.0),"Timely Filing":(.40,.22,.70,1.0),"Medical Necessity":(.75,.52,.80,1.0),"Other/Payer Processing":(.68,.58,.85,1.0)}


def make_ids(prefix: str, n: int) -> np.ndarray:
    return np.array([f"{prefix}-{i:08d}" for i in range(1, n + 1)])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--claims-per-state", type=int, default=9000)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    n = args.claims_per_state * len(STATES)

    state = np.repeat(STATES, args.claims_per_state)
    state_index = np.repeat(np.arange(len(STATES)), args.claims_per_state)
    facility_number = rng.integers(1, 13, n)
    facility_id = np.array([f"FAC-{s+1:02d}-{f:02d}" for s, f in zip(state_index, facility_number)])
    provider_number = rng.integers(1, 31, n)
    provider_id = np.array([f"PRV-{s+1:02d}-{f:02d}-{p:02d}" for s, f, p in zip(state_index, facility_number, provider_number)])
    maturity_by_number = np.where(facility_number <= 3, "Optimized", np.where(facility_number <= 9, "Standard", "Improvement Opportunity"))

    payer = rng.choice(PAYER_CATEGORIES, n, p=PAYER_MIX)
    care = rng.choice(CARE, n, p=CARE_MIX)
    service_day = rng.integers(0, 731, n)
    service_date = pd.Timestamp("2024-01-01", tz="UTC") + pd.to_timedelta(service_day, unit="D")
    age = np.clip(rng.normal(np.where(np.isin(payer,["Medicare","Medicare Advantage"]),72,45), 16, n), 0, 95).round(1)
    diagnosis_count = np.clip(rng.poisson(1.7, n)+1,1,8)
    line_count = np.clip(rng.poisson(2.1,n)+1,1,15)
    procedure_count = np.minimum(line_count, np.clip(rng.poisson(1.3,n)+1,1,10))

    setting_multiplier = pd.Series(care).map({"inpatient":8,"outpatient":2.2,"emergency":2.8,"ambulatory":1,"urgentcare":.8,"home":1.2,"snf":3.5,"hospice":2.5,"wellness":.5,"virtual":.35}).to_numpy()
    charge = np.clip(rng.lognormal(6.25, .85, n) * setting_multiplier, 50, 150000).round(2)
    high_charge = charge >= np.quantile(charge, .90)
    missing_coverage = (payer == "Self-Pay") | (rng.random(n) < .012)
    secondary = (~missing_coverage) & (rng.random(n) < .11)
    duplicate = rng.random(n) < .012
    documentation = rng.random(n) < .08
    coding = (diagnosis_count >= 4) | (line_count >= 6)
    authorization = np.isin(care,["inpatient","outpatient","snf"]) & (rng.random(n) < .55)
    submission_delay = rng.triangular(1,4,12,n).round().astype(int) + np.where(documentation,rng.integers(3,13,n),0)
    submission_date = service_date + pd.to_timedelta(submission_delay,unit="D")

    insured = payer != "Self-Pay"
    prob = np.array([PAYER_BASE.get(x,0) for x in payer]) + np.array([CARE_ADJ[x] for x in care]) + np.array([MATURITY_ADJ[x] for x in maturity_by_number])
    prob += missing_coverage*.12 + secondary*.025 + authorization*.035 + (diagnosis_count>=2)*.015 + (line_count>=2)*.01 + high_charge*.02 + (submission_delay>10)*.025 + (submission_delay>20)*.04 + duplicate*.20 + documentation*.06
    prob = np.clip(prob,.02,.40)
    denial_event = insured & (rng.random(n) < prob)

    denial_reason = np.full(n, None, dtype=object)
    fallback = rng.choice(REASONS,n,p=REASON_W)
    denial_reason[denial_event] = fallback[denial_event]
    denial_reason[denial_event & high_charge] = "Medical Necessity"
    denial_reason[denial_event & coding] = "Coding"
    denial_reason[denial_event & documentation] = "Documentation"
    denial_reason[denial_event & authorization] = "Authorization"
    denial_reason[denial_event & (submission_delay>20)] = "Timely Filing"
    denial_reason[denial_event & missing_coverage] = "Eligibility/Coverage"
    denial_reason[denial_event & duplicate] = "Duplicate Claim"

    adj_base = np.array([ADJ_DAYS.get(x,0) for x in payer])
    adj_days = np.clip(adj_base + rng.integers(-5,11,n),7,None)
    adjudication = pd.Series(submission_date + pd.to_timedelta(adj_days,unit="D"))
    adjudication[~insured] = pd.NaT
    adjudicated_asof = adjudication.notna().to_numpy() & (adjudication <= AS_OF).to_numpy()
    denial_asof = denial_event & adjudicated_asof

    pursued=np.zeros(n,bool); success=np.zeros(n,bool); recovery_factor=np.zeros(n)
    for reason,(prop,succ,lo,hi) in APPEAL.items():
        mask=denial_event & (denial_reason==reason)
        pursued[mask]=rng.random(mask.sum())<prop
        success_mask=mask & pursued
        success[success_mask]=rng.random(success_mask.sum())<succ
        recovery_factor[success_mask]=rng.uniform(lo,hi,success_mask.sum())
    appeal_date=pd.Series(pd.NaT,index=np.arange(n),dtype="datetime64[ns, UTC]")
    appeal_date[pursued]=adjudication[pursued]+pd.to_timedelta(rng.integers(7,36,pursued.sum()),unit="D")
    appeal_decision=pd.Series(pd.NaT,index=np.arange(n),dtype="datetime64[ns, UTC]")
    appeal_decision[pursued]=appeal_date[pursued]+pd.to_timedelta(rng.integers(10,46,pursued.sum()),unit="D")
    decided_asof=appeal_decision.notna().to_numpy() & (appeal_decision<=AS_OF).to_numpy()
    success_asof=success & decided_asof
    final_denial=denial_asof & (~pursued | (decided_asof & ~success))

    allowed=(charge*np.array([ALLOWED[x] for x in payer])*rng.uniform(.92,1.08,n)).round(2)
    patient_share=np.array([{"Medicare":.20,"Medicare Advantage":.17,"Medicaid":.05,"Commercial":.18,"Self-Pay":1}[x] for x in payer])*rng.uniform(.85,1.15,n)
    patient_resp=(allowed*np.clip(patient_share,0,1)).round(2)
    expected_payer=np.clip(allowed-patient_resp,0,None).round(2)
    payable_eventually=(insured & ~denial_event)|success
    underpaid_event=payable_eventually & (rng.random(n)<.10)
    payment_factor=np.where(success,recovery_factor,1.0)*np.where(underpaid_event,1-rng.uniform(.05,.20,n),1)
    eventual_payment=np.where(payable_eventually,expected_payer*payment_factor,0).round(2)
    first_payment=pd.Series(pd.NaT,index=np.arange(n),dtype="datetime64[ns, UTC]")
    clean=insured & ~denial_event
    first_payment[clean]=adjudication[clean]+pd.to_timedelta(rng.integers(3,26,clean.sum()),unit="D")
    first_payment[success]=appeal_decision[success]+pd.to_timedelta(rng.integers(3,21,success.sum()),unit="D")
    paid_asof=first_payment.notna().to_numpy() & (first_payment<=AS_OF).to_numpy()
    actual_payment=np.where(paid_asof,eventual_payment,0).round(2)
    underpaid=underpaid_event & paid_asof
    underpayment=np.where(underpaid,expected_payer-actual_payment,0).round(2)
    patient_payment=np.where(payer=="Self-Pay",patient_resp*rng.uniform(.20,.75,n),patient_resp*rng.uniform(.65,1,n)).round(2)
    contractual=np.clip(charge-allowed,0,None).round(2)
    outstanding=np.clip(allowed-actual_payment-patient_payment,0,None).round(2)
    claim_age=np.clip((AS_OF-pd.Series(submission_date)).dt.days.to_numpy(),0,None)
    aging=np.select([claim_age<=30,claim_age<=60,claim_age<=90,claim_age<=120],["0-30","31-60","61-90","91-120"],default="Over 120")
    timely=((claim_age>=90)&(outstanding>0)).astype(float)
    recovery_likelihood=np.array([APPEAL.get(x,(0,0.9,0,0))[1] if x else .9 for x in denial_reason])
    def mm(x):
        return (x-x.min())/(x.max()-x.min()) if x.max()!=x.min() else np.zeros_like(x,dtype=float)
    priority=(.40*mm(outstanding)+.25*mm(claim_age)+.20*recovery_likelihood+.15*timely)*100
    priority_band=np.select([priority<40,priority<70],["Low","Medium"],default="High")

    df=pd.DataFrame({
        "simulation_seed":SEED,"lineage_notice":"CONSTRUCTED SYNTHETIC PORTFOLIO DATA",
        "claim_id":make_ids("CLM",n),"PATIENTID":make_ids("PAT",n),"encounter_id":make_ids("ENC",n),
        "service_date":service_date,"submission_date":submission_date,"initial_adjudication_date":adjudication,
        "appeal_date":appeal_date,"appeal_decision_date":appeal_decision,"first_payment_date":first_payment,
        "source_payer_name":payer,"payer_category":payer,"care_setting":care,"facility_id":facility_id,"PROVIDERID":provider_id,
        "facility_maturity":maturity_by_number,"source_state":state,"source_county":np.array([f"Synthetic County {(i%5)+1}" for i in state_index]),
        "source_county_fips":np.array([f"{i+1:02d}{(j%5)+1:03d}" for i,j in zip(state_index,np.arange(n))]),
        "patient_age":age,"diagnosis_count":diagnosis_count,"claim_line_count":line_count,"distinct_procedure_count":procedure_count,
        "claim_charge":charge,"missing_primary_coverage_flag":missing_coverage,"secondary_coordination_flag":secondary,
        "duplicate_signature_flag":duplicate,"documentation_risk_flag":documentation,"coding_risk_flag":coding,
        "authorization_risk_flag":authorization,"high_charge_flag":high_charge,"submission_delay_days":submission_delay,
        "initial_denial_probability":np.where(insured,prob,np.nan),"adjudicated_as_of_flag":adjudicated_asof,
        "initial_denial_flag":denial_event,"initial_denial_as_of_flag":denial_asof,"denial_reason":denial_reason,
        "preventable_denial_flag":np.array([PREVENTABLE.get(x,0) for x in denial_reason],dtype=bool),
        "appeal_or_resubmission_flag":pursued,"appeal_success_flag":success,"appeal_decision_as_of_flag":decided_asof,
        "appeal_success_as_of_flag":success_asof,"final_denial_flag":final_denial,"expected_allowed_amount":allowed,
        "patient_responsibility":patient_resp,"expected_payer_payment":expected_payer,"actual_payer_payment":actual_payment,
        "payment_received_as_of_flag":paid_asof,"underpayment_flag":underpaid,"underpayment_amount":underpayment,
        "recovery_amount":np.where(success_asof&paid_asof,actual_payment,0).round(2),"patient_payment":patient_payment,
        "contractual_adjustment":contractual,"outstanding_balance":outstanding,"claim_age_days":claim_age,
        "aging_bucket":aging,"timely_filing_risk":timely,"follow_up_priority_score":priority.round(2),
        "follow_up_priority_band":priority_band,
    })
    df.to_csv(args.output,index=False)
    print(df.groupby("source_state").size().to_string())
    insured_adjudicated=df.adjudicated_as_of_flag & df.payer_category.ne("Self-Pay")
    print("claims",len(df),"initial_denial_rate",round(df.loc[insured_adjudicated,"initial_denial_as_of_flag"].mean(),4),"final_denial_rate",round(df.loc[insured_adjudicated,"final_denial_flag"].mean(),4))


if __name__ == "__main__":
    main()
