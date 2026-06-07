from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import roc_auc_score
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


def _fit_logit(model_name: str, X: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, dict[str, float]]:
    X_model = X.astype(float)
    y_model = y.astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X_model,
        y_model,
        test_size=0.30,
        random_state=RANDOM_SEED,
        stratify=y_model,
    )
    fitted = sm.Logit(y_train, sm.add_constant(X_train, has_constant="add")).fit(disp=0, maxiter=300)
    y_score = fitted.predict(sm.add_constant(X_test, has_constant="add"))
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
    metrics = {
        "model": model_name,
        "n_obs": int(len(y_model)),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "positive_rate_pct": float(y_model.mean() * 100.0),
        "pseudo_r2_mcfadden": float(fitted.prsquared),
        "auc_test": float(roc_auc_score(y_test, y_score)),
    }
    return coef, metrics


def _row_channel_matrix(touchpoints: pd.DataFrame) -> pd.DataFrame:
    dummies = pd.get_dummies(touchpoints["channel"].astype(str), prefix="channel", drop_first=False).astype(int)
    dummies = dummies.rename(columns={
        "channel_Direct Traffic": "channel_direct_traffic",
        "channel_Display Ads": "channel_display_ads",
        "channel_Email": "channel_email",
        "channel_Referral": "channel_referral",
        "channel_Search Ads": "channel_search_ads",
        "channel_Social Media": "channel_social_media",
    })
    return dummies.reindex(columns=CHANNEL_FEATURES, fill_value=0)


def run() -> dict[str, pd.DataFrame]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    touchpoints = _read_sql_output("rq123_touchpoint_features")
    users = _read_sql_output("rq2_user_channel_features")

    coef_tables: list[pd.DataFrame] = []
    metric_rows: list[dict[str, float]] = []

    row_X = _row_channel_matrix(touchpoints)
    coef, metrics = _fit_logit("row_channel", row_X.drop(columns=["channel_direct_traffic"]), touchpoints["is_conversion"].astype(int))
    coef_tables.append(coef)
    metric_rows.append(metrics)

    coef, metrics = _fit_logit("user_any_channel", users[CHANNEL_FEATURES], users["converted_any_yes"].astype(int))
    coef_tables.append(coef)
    metric_rows.append(metrics)

    coef, metrics = _fit_logit("journey_length_only", users[["n_touchpoints"]], users["converted_any_yes"].astype(int))
    coef_tables.append(coef)
    metric_rows.append(metrics)

    combined_features = CHANNEL_FEATURES + ["n_touchpoints"]
    coef, metrics = _fit_logit("channel_plus_length", users[combined_features], users["converted_any_yes"].astype(int))
    coef_tables.append(coef)
    metric_rows.append(metrics)

    coefficients = pd.concat(coef_tables, ignore_index=True).round(6)
    model_metrics = pd.DataFrame(metric_rows).round(6)

    channel_plus = coefficients[coefficients["model"].eq("channel_plus_length") & coefficients["term"].isin(CHANNEL_FEATURES)].copy()
    channel_plus["channel"] = channel_plus["term"].map(DISPLAY_NAMES)
    channel_plus["score"] = np.exp(channel_plus["coef"] - channel_plus["coef"].max())
    channel_plus["logistic_adjusted_share_pct"] = channel_plus["score"] / channel_plus["score"].sum() * 100.0
    adjusted_share = channel_plus[["channel", "logistic_adjusted_share_pct", "coef", "odds_ratio", "p_value"]].round(6)

    model_metrics.to_csv(OUTPUT_DIR / "rq2_logistic_model_metrics.csv", index=False)
    coefficients.to_csv(OUTPUT_DIR / "rq2_logistic_model_coefficients.csv", index=False)
    adjusted_share.to_csv(OUTPUT_DIR / "rq2_logistic_adjusted_channel_share.csv", index=False)
    users.to_csv(OUTPUT_DIR / "rq2_logistic_user_model_matrix.csv", index=False)

    return {
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

