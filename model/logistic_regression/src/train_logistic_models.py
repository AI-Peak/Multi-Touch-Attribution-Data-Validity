from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
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

C_VALUES = [0.01, 0.1, 1.0, 10.0, 100.0]


def _read_sql_output(name: str) -> pd.DataFrame:
    path = SQL_OUTPUT_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing SQL output: {path}")
    return pd.read_csv(path)


def _calculate_full_metrics(y_true: pd.Series, y_prob: np.ndarray, split_name: str, model_name: str) -> dict:
    y_pred = (y_prob >= 0.5).astype(int)
    metrics = {
        "split": split_name,
        "model": model_name,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    try:
        # Check if y_true contains only one class
        if y_true.nunique() > 1:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
        else:
            metrics["roc_auc"] = np.nan
            print(f"Warning: Cannot calculate ROC-AUC for {model_name} on {split_name} split as y_true contains only one class.", file=sys.stderr)
    except ValueError:
        metrics["roc_auc"] = np.nan
        print(f"Warning: Cannot calculate ROC-AUC for {model_name} on {split_name} split due to ValueError.", file=sys.stderr)
    return metrics


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


def _get_data_splits(
    X: pd.DataFrame, y: pd.Series
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
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
    return X_train, y_train, X_valid, y_valid, X_test, y_test, X_model, y_model


def _fit_statsmodels_logit(
    model_name: str,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    X_model: pd.DataFrame,
    y_model: pd.Series,
) -> tuple[pd.DataFrame, dict[str, float]]:
    # Fit model on Train
    X_train_const = sm.add_constant(X_train, has_constant="add")
    fitted = sm.Logit(y_train, X_train_const).fit(disp=0, maxiter=300)

    # Prediction Probabilities for Test
    y_prob_test = fitted.predict(sm.add_constant(X_test, has_constant="add"))
    test_metrics = _calculate_full_metrics(y_test, y_prob_test, "Test", model_name)

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

    # Compatibility metrics (for old rq2_logistic_model_metrics.csv)
    metrics = {
        "model": model_name,
        "n_obs": int(len(y_model)),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "positive_rate_pct": float(y_model.mean() * 100.0),
        "pseudo_r2_mcfadden": float(fitted.prsquared),
        "auc_test": test_metrics["roc_auc"], # Use ROC AUC from full metrics for consistency
    }

    return coef, metrics


def _tune_sklearn_logistic_model(
    model_name: str,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_valid: pd.DataFrame,
    y_valid: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> tuple[list[dict], dict]:
    tuning_results_list = []
    best_validation_auc = -np.inf
    best_C_for_model = None
    best_test_metrics_for_model = {}
    best_overall_metrics = {}

    for c_val in C_VALUES:
        lr_model = LogisticRegression(
            C=c_val, solver="liblinear", max_iter=1000, random_state=RANDOM_SEED
        )
        lr_model.fit(X_train, y_train)

        y_prob_train = lr_model.predict_proba(X_train)[:, 1]
        y_prob_valid = lr_model.predict_proba(X_valid)[:, 1]
        y_prob_test = lr_model.predict_proba(X_test)[:, 1]

        train_metrics = _calculate_full_metrics(y_train, y_prob_train, "Train", model_name)
        valid_metrics = _calculate_full_metrics(y_valid, y_prob_valid, "Validation", model_name)
        test_metrics = _calculate_full_metrics(y_test, y_prob_test, "Test", model_name)

        current_tuning_result = {
            "model": model_name,
            "C": c_val,
            "train_auc": train_metrics["roc_auc"],
            "validation_auc": valid_metrics["roc_auc"],
            "test_auc": test_metrics["roc_auc"],
            "validation_accuracy": valid_metrics["accuracy"],
            "validation_precision": valid_metrics["precision"],
            "validation_recall": valid_metrics["recall"],
            "validation_f1": valid_metrics["f1"],
            "is_best": False,
        }
        tuning_results_list.append(current_tuning_result)

        # Select best C based on validation ROC-AUC
        if not np.isnan(valid_metrics["roc_auc"]) and valid_metrics["roc_auc"] > best_validation_auc:
            best_validation_auc = valid_metrics["roc_auc"]
            best_C_for_model = c_val
            best_test_metrics_for_model = test_metrics
            best_overall_metrics = {
                "model": model_name,
                "best_C": best_C_for_model,
                "best_validation_auc": best_validation_auc,
                "test_auc": best_test_metrics_for_model["roc_auc"],
                "test_accuracy": best_test_metrics_for_model["accuracy"],
                "test_precision": best_test_metrics_for_model["precision"],
                "test_recall": best_test_metrics_for_model["recall"],
                "test_f1": best_test_metrics_for_model["f1"],
            }
    
    # Mark the best C in the tuning results list
    for result in tuning_results_list:
        if result["C"] == best_C_for_model:
            result["is_best"] = True

    return tuning_results_list, best_overall_metrics


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
    metric_rows: list[dict[str, float]] = [] # For rq2_logistic_model_metrics.csv (statsmodels based)
    all_split_summaries: list[dict] = []
    all_metrics_list: list[dict] = [] # For logistic_regression_metrics.csv (sklearn based)

    all_tuning_results: list[dict] = []
    all_best_hyperparameters: list[dict] = []

    # Helper to process each model
    def process_model(model_name: str, X: pd.DataFrame, y: pd.Series, drop_direct_traffic: bool = False):
        if drop_direct_traffic:
            X_processed = X.drop(columns=["channel_direct_traffic"])
        else:
            X_processed = X

        X_train, y_train, X_valid, y_valid, X_test, y_test, X_model, y_model = _get_data_splits(X_processed, y)
        
        # --- Statsmodels.Logit for original outputs ---
        coef_sm, metrics_sm = _fit_statsmodels_logit(model_name, X_train, y_train, X_test, y_test, X_model, y_model)
        coef_tables.append(coef_sm)
        metric_rows.append(metrics_sm)

        # Split Summaries (same for both statsmodels and sklearn)
        split_summaries = [
            _get_split_summary(y_train, "Train"),
            _get_split_summary(y_valid, "Validation"),
            _get_split_summary(y_test, "Test"),
        ]
        for s in split_summaries:
            s["model"] = model_name
        all_split_summaries.extend(split_summaries)

        # --- Sklearn.LogisticRegression for tuning and full metrics ---
        tuning_results, best_hps_row = _tune_sklearn_logistic_model(
            model_name, X_train, y_train, X_valid, y_valid, X_test, y_test
        )
        all_tuning_results.extend(tuning_results)
        all_best_hyperparameters.append(best_hps_row)

        # Get metrics for the best sklearn model to add to all_metrics_list
        best_C_for_model = best_hps_row["best_C"]
        best_lr_model = LogisticRegression(
            C=best_C_for_model, solver="liblinear", max_iter=1000, random_state=RANDOM_SEED
        )
        best_lr_model.fit(X_train, y_train)

        y_prob_train_best = best_lr_model.predict_proba(X_train)[:, 1]
        y_prob_valid_best = best_lr_model.predict_proba(X_valid)[:, 1]
        y_prob_test_best = best_lr_model.predict_proba(X_test)[:, 1]

        all_metrics_list.append(_calculate_full_metrics(y_train, y_prob_train_best, "Train", model_name))
        all_metrics_list.append(_calculate_full_metrics(y_valid, y_prob_valid_best, "Validation", model_name))
        all_metrics_list.append(_calculate_full_metrics(y_test, y_prob_test_best, "Test", model_name))


    # 1. Row Channel Model
    row_X = _row_channel_matrix(touchpoints)
    process_model(
        "row_channel",
        row_X,
        touchpoints["is_conversion"].astype(int),
        drop_direct_traffic=True,
    )

    # 2. User Any Channel Model
    process_model(
        "user_any_channel",
        users[CHANNEL_FEATURES],
        users["converted_any_yes"].astype(int),
    )

    # 3. Journey Length Only Model
    process_model(
        "journey_length_only",
        users[["n_touchpoints"]],
        users["converted_any_yes"].astype(int),
    )

    # 4. Channel Plus Length Model
    combined_features = CHANNEL_FEATURES + ["n_touchpoints"]
    process_model(
        "channel_plus_length",
        users[combined_features],
        users["converted_any_yes"].astype(int),
    )


    # Create summary dataframes
    split_summary_df = pd.DataFrame(all_split_summaries)
    # This metrics_summary_df now contains metrics for the best sklearn model
    metrics_summary_df = pd.DataFrame(all_metrics_list)
    coefficients = pd.concat(coef_tables, ignore_index=True).round(6)
    model_metrics = pd.DataFrame(metric_rows).round(6) # Original compatibility metrics

    tuning_results_df = pd.DataFrame(all_tuning_results).round(6)
    best_hyperparameters_df = pd.DataFrame(all_best_hyperparameters).round(6)


    # Channel share calculation (using statsmodels coefficients for consistency with original output)
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
    users.to_csv(OUTPUT_DIR / "rq2_logistic_user_model_matrix.csv", index=False) # This is users, not model matrix
    
    tuning_results_df.to_csv(OUTPUT_DIR / "hyperparameter_tuning_results.csv", index=False)
    best_hyperparameters_df.to_csv(OUTPUT_DIR / "best_hyperparameters.csv", index=False)

    # Plotting
    plt.figure(figsize=(10, 6))
    for model_name_plot in tuning_results_df["model"].unique():
        model_data = tuning_results_df[tuning_results_df["model"] == model_name_plot]
        plt.plot(model_data["C"], model_data["validation_auc"], marker="o", label=model_name_plot)
    plt.xscale("log")
    plt.xlabel("C (Regularization Strength)")
    plt.ylabel("Validation ROC-AUC")
    plt.title("Hyper-parameter Tuning: Validation ROC-AUC by C")
    plt.legend()
    plt.grid(True)
    plt.savefig(OUTPUT_DIR / "hyperparameter_tuning_auc.png")
    plt.close()

    plt.figure(figsize=(10, 6))
    plt.bar(best_hyperparameters_df["model"], best_hyperparameters_df["best_validation_auc"])
    plt.xlabel("Model")
    plt.ylabel("Best Validation ROC-AUC")
    plt.title("Best Validation ROC-AUC after Tuning")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "hyperparameter_tuning_best_auc.png")
    plt.close()


    return {
        "split_summary": split_summary_df,
        "metrics_summary": metrics_summary_df, # Sklearn based
        "model_metrics": model_metrics, # Statsmodels based compatibility
        "model_coefficients": coefficients, # Statsmodels based
        "logistic_adjusted_channel_share": adjusted_share, # Statsmodels based
        "user_model_matrix": users,
        "hyperparameter_tuning_results": tuning_results_df,
        "best_hyperparameters": best_hyperparameters_df,
    }


def main() -> None:
    results = run()
    
    print("\n--- Logistic Regression Tuning Complete ---")
    print(f"Modified file: {Path(__file__).resolve()}")
    print(f"C values tested: {C_VALUES}")
    
    print("\nBest Hyperparameters:")
    print(results["best_hyperparameters"].to_markdown(index=False))

    print(f"\nOutput files generated in: {OUTPUT_DIR}")
    print(f" - Hyperparameter Tuning Results: {OUTPUT_DIR / 'hyperparameter_tuning_results.csv'}")
    print(f" - Best Hyperparameters: {OUTPUT_DIR / 'best_hyperparameters.csv'}")
    print(f" - Tuning ROC-AUC Plot: {OUTPUT_DIR / 'hyperparameter_tuning_auc.png'}")
    print(f" - Best ROC-AUC Bar Plot: {OUTPUT_DIR / 'hyperparameter_tuning_best_auc.png'}")
    print(f" - Split Summary: {OUTPUT_DIR / 'split_summary.csv'}")
    print(f" - Full Metrics (best sklearn model): {OUTPUT_DIR / 'logistic_regression_metrics.csv'}")
    print(f" - Original Model Metrics (statsmodels): {OUTPUT_DIR / 'rq2_logistic_model_metrics.csv'}")
    print(f" - Model Coefficients (statsmodels): {OUTPUT_DIR / 'rq2_logistic_model_coefficients.csv'}")
    print(f" - Adjusted Channel Share (statsmodels): {OUTPUT_DIR / 'rq2_logistic_adjusted_channel_share.csv'}")
    print(f" - User Model Matrix: {OUTPUT_DIR / 'rq2_logistic_user_model_matrix.csv'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Logistic model training and tuning failed: {exc}", file=sys.stderr)
        raise

