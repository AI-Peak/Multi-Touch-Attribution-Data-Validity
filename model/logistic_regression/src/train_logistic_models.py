from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SQL_OUTPUT_DIR = PROJECT_ROOT / "data" / "sql_outputs"
OUTPUT_DIR = PROJECT_ROOT / "model" / "logistic_regression" / "outputs"
RANDOM_SEED = 42

CHANNEL_FEATURES = [
    "channel_direct_traffic",
    "channel_display_ads",
    "channel_email",
    "channel_referral",
    "channel_search_ads",
    "channel_social_media",
]

DISPLAY_NAMES = {
    "channel_direct_traffic": "Direct Traffic",
    "channel_display_ads": "Display Ads",
    "channel_email": "Email",
    "channel_referral": "Referral",
    "channel_search_ads": "Search Ads",
    "channel_social_media": "Social Media",
}


def _read_sql_output(name: str) -> pd.DataFrame:
    path = SQL_OUTPUT_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing SQL output: {path}")
    return pd.read_csv(path)


def _calculate_metrics(y_true: pd.Series, y_prob: pd.Series, split_name: str) -> dict:
    y_pred = (y_prob >= 0.5).astype(int)
    return {
        "split": split_name,
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def _get_split_summary(y: pd.Series, split_name: str) -> dict:
    n_samples = len(y)
    n_converted = int(y.sum())
    n_not_converted = n_samples - n_converted
    conversion_rate = float(y.mean())
    return {
        "split": split_name,
        "n_samples": n_samples,
        "n_converted": n_converted,
        "n_not_converted": n_not_converted,
        "conversion_rate": conversion_rate,
    }


def _fit_logit(
    model_name: str, X: pd.DataFrame, y: pd.Series
) -> tuple[pd.DataFrame, dict[str, float], list[dict], list[dict]]:
    X_model = X.astype(float)
    y_model = y.astype(int)

    # Step 1: Train 70%, Temp 30%
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_model,
        y_model,
        test_size=0.30,
        random_state=RANDOM_SEED,
        stratify=y_model,
    )

    # Step 2: Validation 15%, Test 15% (50% of Temp)
    X_valid, X_test, y_valid, y_test = train_test_split(
        X_temp,
        y_temp,
        test_size=0.50,
        random_state=RANDOM_SEED,
        stratify=y_temp,
    )

    # Fit model on Train
    X_train_const = sm.add_constant(X_train, has_constant="add")
    fitted = sm.Logit(y_train, X_train_const).fit(disp=0, maxiter=300)

    # Split Summaries
    split_summaries = [
        _get_split_summary(y_train, "Train"),
        _get_split_summary(y_valid, "Validation"),
        _get_split_summary(y_test, "Test"),
    ]
    for s in split_summaries:
        s["model"] = model_name

    # Prediction Probabilities
    y_prob_train = fitted.predict(X_train_const)
    y_prob_valid = fitted.predict(sm.add_constant(X_valid, has_constant="add"))
    y_prob_test = fitted.predict(sm.add_constant(X_test, has_constant="add"))

    # Metrics
    metrics_list = [
        _calculate_metrics(y_train, y_prob_train, "Train"),
        _calculate_metrics(y_valid, y_prob_valid, "Validation"),
        _calculate_metrics(y_test, y_prob_test, "Test"),
    ]
    for m in metrics_list:
        m["model"] = model_name

    # Coefficients
    conf = fitted.conf_int()
    coef = pd.DataFrame(
        {
            "model": model_name,
            "term": fitted.params.index,
            "coef": fitted.params.to_numpy(dtype=float),
            "odds_ratio": np.exp(fitted.params.to_numpy(dtype=float)),
            "or_ci_low": np.exp(conf[0].to_numpy(dtype=float)),
            "or_ci_high": np.exp(conf[1].to_numpy(dtype=float)),
            "p_value": fitted.pvalues.to_numpy(dtype=float),
        }
    )

    # Compatibility metrics
    metrics = {
        "model": model_name,
        "n_obs": int(len(y_model)),
        "n_train": int(len(y_train)),
        "n_valid": int(len(y_valid)),
        "n_test": int(len(y_test)),
        "positive_rate_pct": float(y_model.mean() * 100.0),
        "pseudo_r2_mcfadden": float(fitted.prsquared),
        "auc_test": metrics_list[2]["roc_auc"],
    }

    return coef, metrics, split_summaries, metrics_list


def _row_channel_matrix(touchpoints: pd.DataFrame) -> pd.DataFrame:
    dummies = pd.get_dummies(
        touchpoints["channel"].astype(str), prefix="channel", drop_first=False
    ).astype(int)
    dummies = dummies.rename(
        columns={
            "channel_Direct Traffic": "channel_direct_traffic",
            "channel_Display Ads": "channel_display_ads",
            "channel_Email": "channel_email",
            "channel_Referral": "channel_referral",
            "channel_Search Ads": "channel_search_ads",
            "channel_Social Media": "channel_social_media",
        }
    )
    return dummies.reindex(columns=CHANNEL_FEATURES, fill_value=0)


def run() -> dict[str, pd.DataFrame]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    touchpoints = _read_sql_output("rq23_touchpoint_features")
    users = _read_sql_output("rq2_user_channel_features")

    coef_tables: list[pd.DataFrame] = []
    metric_rows: list[dict[str, float]] = []
    all_split_summaries: list[dict] = []
    all_metrics_list: list[dict] = []

    # 1. Row Channel Model
    row_X = _row_channel_matrix(touchpoints)
    coef, metrics, summaries, m_list = _fit_logit(
        "row_channel",
        row_X.drop(columns=["channel_direct_traffic"]),
        touchpoints["is_conversion"].astype(int),
    )
    coef_tables.append(coef)
    metric_rows.append(metrics)
    all_split_summaries.extend(summaries)
    all_metrics_list.extend(m_list)

    # 2. User Any Channel Model
    coef, metrics, summaries, m_list = _fit_logit(
        "user_any_channel", users[CHANNEL_FEATURES], users["converted_any_yes"].astype(int)
    )
    coef_tables.append(coef)
    metric_rows.append(metrics)
    all_split_summaries.extend(summaries)
    all_metrics_list.extend(m_list)

    # 3. Journey Length Only Model
    coef, metrics, summaries, m_list = _fit_logit(
        "journey_length_only",
        users[["n_touchpoints"]],
        users["converted_any_yes"].astype(int),
    )
    coef_tables.append(coef)
    metric_rows.append(metrics)
    all_split_summaries.extend(summaries)
    all_metrics_list.extend(m_list)

    # 4. Channel Plus Length Model
    combined_features = CHANNEL_FEATURES + ["n_touchpoints"]
    coef, metrics, summaries, m_list = _fit_logit(
        "channel_plus_length", users[combined_features], users["converted_any_yes"].astype(int)
    )
    coef_tables.append(coef)
    metric_rows.append(metrics)
    all_split_summaries.extend(summaries)
    all_metrics_list.extend(m_list)

    # Create summary dataframes
    split_summary_df = pd.DataFrame(all_split_summaries)
    metrics_summary_df = pd.DataFrame(all_metrics_list)
    coefficients = pd.concat(coef_tables, ignore_index=True).round(6)
    model_metrics = pd.DataFrame(metric_rows).round(6)

    # Channel share calculation
    channel_plus = coefficients[
        coefficients["model"].eq("channel_plus_length")
        & coefficients["term"].isin(CHANNEL_FEATURES)
    ].copy()
    channel_plus["channel"] = channel_plus["term"].map(DISPLAY_NAMES)
    channel_plus["score"] = np.exp(channel_plus["coef"] - channel_plus["coef"].max())
    channel_plus["logistic_adjusted_share_pct"] = (
        channel_plus["score"] / channel_plus["score"].sum() * 100.0
    )
    adjusted_share = channel_plus[
        ["channel", "logistic_adjusted_share_pct", "coef", "odds_ratio", "p_value"]
    ].round(6)

    # Save all outputs
    split_summary_df.to_csv(OUTPUT_DIR / "split_summary.csv", index=False)
    metrics_summary_df.to_csv(OUTPUT_DIR / "logistic_regression_metrics.csv", index=False)
    model_metrics.to_csv(OUTPUT_DIR / "rq2_logistic_model_metrics.csv", index=False)
    coefficients.to_csv(OUTPUT_DIR / "rq2_logistic_model_coefficients.csv", index=False)
    adjusted_share.to_csv(
        OUTPUT_DIR / "rq2_logistic_adjusted_channel_share.csv", index=False
    )
    users.to_csv(OUTPUT_DIR / "rq2_logistic_user_model_matrix.csv", index=False)

    return {
        "split_summary": split_summary_df,
        "metrics_summary": metrics_summary_df,
        "model_metrics": model_metrics,
        "model_coefficients": coefficients,
        "logistic_adjusted_channel_share": adjusted_share,
        "user_model_matrix": users,
    }


def main() -> None:
    run()
    print("Logistic regression model layer complete. Inputs were SQL outputs only.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Logistic model training failed: {exc}", file=sys.stderr)
        raise

