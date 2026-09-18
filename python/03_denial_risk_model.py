#!/usr/bin/env python3
"""Train an interpretable pre-submission denial-risk model on synthetic claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


SEED = 20260917

CATEGORICAL_FEATURES = [
    "payer_category",
    "care_setting",
    "facility_maturity",
]

NUMERIC_FEATURES = [
    "patient_age",
    "diagnosis_count",
    "claim_line_count",
    "distinct_procedure_count",
    "claim_charge",
    "submission_delay_days",
    "missing_primary_coverage_flag",
    "secondary_coordination_flag",
    "duplicate_signature_flag",
    "documentation_risk_flag",
    "coding_risk_flag",
    "authorization_risk_flag",
    "high_charge_flag",
]

FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET = "initial_denial_as_of_flag"


def make_pipeline() -> Pipeline:
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", categorical, CATEGORICAL_FEATURES),
            ("numeric", numeric, NUMERIC_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    model = LogisticRegression(
        class_weight="balanced",
        max_iter=2000,
        random_state=SEED,
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])


def select_threshold(y_true: pd.Series, probabilities: np.ndarray) -> pd.DataFrame:
    rows = []
    for threshold in np.arange(0.10, 0.91, 0.01):
        predicted = probabilities >= threshold
        tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
        specificity = tn / (tn + fp) if (tn + fp) else 0.0
        rows.append(
            {
                "threshold": round(float(threshold), 2),
                "precision": precision_score(y_true, predicted, zero_division=0),
                "recall": recall_score(y_true, predicted, zero_division=0),
                "specificity": specificity,
                "balanced_accuracy": balanced_accuracy_score(y_true, predicted),
                "f1": f1_score(y_true, predicted, zero_division=0),
            }
        )
    table = pd.DataFrame(rows)
    return table.sort_values(
        ["balanced_accuracy", "f1", "recall", "precision", "threshold"],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)


def risk_band(probability: float | None) -> str:
    if probability is None or pd.isna(probability):
        return "Not Applicable"
    if probability < 0.10:
        return "Low"
    if probability < 0.20:
        return "Moderate"
    if probability < 0.35:
        return "High"
    return "Very High"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claims-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    claims = pd.read_csv(args.claims_file, low_memory=False)
    claims["service_date"] = pd.to_datetime(claims["service_date"], utc=True)
    claims["service_year"] = claims["service_date"].dt.year

    eligible = claims.loc[
        claims["adjudicated_as_of_flag"].astype(bool)
        & claims["payer_category"].ne("Self-Pay")
    ].copy()
    train_pool = eligible.loc[eligible["service_year"].eq(2024)].copy()
    test = eligible.loc[eligible["service_year"].eq(2025)].copy()

    if train_pool[TARGET].nunique() != 2 or test[TARGET].nunique() != 2:
        raise RuntimeError("Both train and test periods must contain denied and non-denied claims.")

    train_core, validation = train_test_split(
        train_pool,
        test_size=0.25,
        stratify=train_pool[TARGET],
        random_state=SEED,
    )

    threshold_model = make_pipeline()
    threshold_model.fit(train_core[FEATURES], train_core[TARGET])
    validation_probability = threshold_model.predict_proba(validation[FEATURES])[:, 1]
    threshold_table = select_threshold(validation[TARGET], validation_probability)
    selected_threshold = float(threshold_table.loc[0, "threshold"])

    final_model = make_pipeline()
    final_model.fit(train_pool[FEATURES], train_pool[TARGET])
    test_probability = final_model.predict_proba(test[FEATURES])[:, 1]
    test_prediction = test_probability >= selected_threshold

    tn, fp, fn, tp = confusion_matrix(test[TARGET], test_prediction, labels=[0, 1]).ravel()
    metrics = {
        "random_seed": SEED,
        "selected_threshold": selected_threshold,
        "train_claims": int(len(train_pool)),
        "validation_claims": int(len(validation)),
        "test_claims": int(len(test)),
        "train_denial_rate": float(train_pool[TARGET].mean()),
        "test_denial_rate": float(test[TARGET].mean()),
        "roc_auc": float(roc_auc_score(test[TARGET], test_probability)),
        "pr_auc": float(average_precision_score(test[TARGET], test_probability)),
        "accuracy": float(accuracy_score(test[TARGET], test_prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(test[TARGET], test_prediction)),
        "precision": float(precision_score(test[TARGET], test_prediction, zero_division=0)),
        "recall": float(recall_score(test[TARGET], test_prediction, zero_division=0)),
        "f1": float(f1_score(test[TARGET], test_prediction, zero_division=0)),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }

    metrics_frame = pd.DataFrame(
        [{"metric": key, "value": value} for key, value in metrics.items()]
    )
    metrics_frame.to_csv(args.output_dir / "denial_model_metrics.csv", index=False)
    threshold_table.to_csv(args.output_dir / "threshold_selection.csv", index=False)

    feature_names = final_model.named_steps["preprocessor"].get_feature_names_out()
    coefficients = final_model.named_steps["model"].coef_[0]
    coefficient_frame = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": coefficients,
            "odds_ratio": np.exp(coefficients),
            "direction": np.where(coefficients >= 0, "Higher simulated risk", "Lower simulated risk"),
        }
    ).sort_values("coefficient", ascending=False)
    coefficient_frame.to_csv(args.output_dir / "denial_model_coefficients.csv", index=False)

    scored = claims[["claim_id", "service_date", "payer_category", "care_setting",
                     "facility_maturity", TARGET]].copy()
    insured = claims["payer_category"].ne("Self-Pay")
    scored["denial_risk_probability"] = np.nan
    scored.loc[insured, "denial_risk_probability"] = final_model.predict_proba(
        claims.loc[insured, FEATURES]
    )[:, 1]
    scored["denial_risk_band"] = scored["denial_risk_probability"].map(risk_band)
    scored["predicted_denial_flag"] = np.where(
        scored["denial_risk_probability"].notna(),
        scored["denial_risk_probability"].ge(selected_threshold).astype(int),
        pd.NA,
    )
    scored["model_threshold"] = selected_threshold
    scored["model_lineage"] = "SYNTHETIC PORTFOLIO MODEL"
    scored.to_csv(args.output_dir / "claim_denial_risk_scores.csv", index=False)

    test_results = test[["claim_id", "service_date", TARGET]].copy()
    test_results["denial_risk_probability"] = test_probability
    test_results["predicted_denial_flag"] = test_prediction.astype(int)
    test_results.to_csv(args.output_dir / "denial_model_test_predictions.csv", index=False)

    joblib.dump(final_model, args.output_dir / "denial_risk_logistic_model.joblib")
    (args.output_dir / "denial_model_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    print(metrics_frame.to_string(index=False))
    print("\nTop positive coefficients:")
    print(coefficient_frame.head(8).to_string(index=False))
    print("\nTop negative coefficients:")
    print(coefficient_frame.tail(8).sort_values("coefficient").to_string(index=False))


if __name__ == "__main__":
    main()
