from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split, RepeatedStratifiedKFold
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    log_loss,
)
from sklearn.inspection import permutation_importance
from scipy.stats import ttest_ind, ttest_rel, wilcoxon

# Suppress warnings
warnings.filterwarnings("ignore")

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

LEAKAGE_FEATURES = [
    "last_touch_yes",
    "n_conversion_events",
    "first_conversion_rank",
    "any_yes_before_last",
    "multiple_yes_events",
    "conversion",
    "is_conversion",
    "converted_any_yes",
    "Timestamp",
    "timestamp_iso",
]


def _read_sql_output(name: str) -> pd.DataFrame:
    path = SQL_OUTPUT_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing SQL output: {path}")
    return pd.read_csv(path)


def validate_no_leakage(feature_names: list[str], leakage_features: list[str]) -> None:
    detected = [feat for feat in feature_names if feat in leakage_features]
    if detected:
        raise ValueError(f"CRITICAL ERROR: Data leakage detected! The following features are prohibited: {detected}")


def compute_metrics(y_true: pd.Series, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    
    if len(np.unique(y_true)) < 2:
        roc_auc = np.nan
        pr_auc = np.nan
    else:
        roc_auc = float(roc_auc_score(y_true, y_prob))
        pr_auc = float(average_precision_score(y_true, y_prob))
        
    accuracy = float(accuracy_score(y_true, y_pred))
    balanced_accuracy = float(balanced_accuracy_score(y_true, y_pred))
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    specificity = float(recall_score(y_true, y_pred, pos_label=0, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    
    try:
        brier = float(brier_score_loss(y_true, y_prob))
    except Exception:
        brier = np.nan
        
    try:
        logloss = float(log_loss(y_true, y_prob, labels=[0, 1]))
    except Exception:
        logloss = np.nan
        
    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "brier_score": brier,
        "log_loss": logloss
    }


def build_user_journey_features(tp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds enhanced user-level journey features from touchpoint sequences.
    Ensures zero target leakage.
    """
    tp_df = tp_df.sort_values(by=["user_id", "touchpoint_rank"]).copy()
    tp_df["timestamp"] = pd.to_datetime(tp_df["timestamp_iso"])
    
    PAID_CHANNELS = {"Search Ads", "Display Ads", "Social Media"}
    ORGANIC_CHANNELS = {"Direct Traffic", "Referral", "Email"}
    
    rows = []
    for user_id, group in tp_df.groupby("user_id"):
        n_touchpoints = len(group)
        channels = group["channel"].tolist()
        campaigns = group["campaign"].tolist()
        timestamps = group["timestamp"].tolist()
        
        unique_channels = list(set(channels))
        n_unique_channels = len(unique_channels)
        
        t_first = timestamps[0]
        t_last = timestamps[-1]
        journey_duration_hours = (t_last - t_first).total_seconds() / 3600.0
        
        repeat_touchpoint_count = n_touchpoints - n_unique_channels
        repeat_touchpoint_ratio = repeat_touchpoint_count / n_touchpoints if n_touchpoints > 0 else 0.0
        
        gaps = []
        if n_touchpoints > 1:
            gaps = [(timestamps[i+1] - timestamps[i]).total_seconds() / 3600.0 for i in range(n_touchpoints - 1)]
            mean_time_between_touchpoints = float(np.mean(gaps))
            median_time_between_touchpoints = float(np.median(gaps))
            max_time_gap = float(np.max(gaps))
        else:
            mean_time_between_touchpoints = 0.0
            median_time_between_touchpoints = 0.0
            max_time_gap = 0.0
            
        n_channel_transitions = 0
        n_consecutive_same = 0
        n_consecutive_diff = 0
        n_paid_to_organic = 0
        n_organic_to_paid = 0
        unique_transitions = set()
        
        if n_touchpoints > 1:
            for i in range(n_touchpoints - 1):
                c_curr = channels[i]
                c_next = channels[i+1]
                unique_transitions.add((c_curr, c_next))
                if c_curr != c_next:
                    n_channel_transitions += 1
                    n_consecutive_diff += 1
                else:
                    n_consecutive_same += 1
                
                if c_curr in PAID_CHANNELS and c_next in ORGANIC_CHANNELS:
                    n_paid_to_organic += 1
                elif c_curr in ORGANIC_CHANNELS and c_next in PAID_CHANNELS:
                    n_organic_to_paid += 1
                    
        n_unique_transitions = len(unique_transitions)
        channel_switch_rate = n_channel_transitions / (n_touchpoints - 1) if n_touchpoints > 1 else 0.0
        prop_paid_to_organic = n_paid_to_organic / (n_touchpoints - 1) if n_touchpoints > 1 else 0.0
        prop_organic_to_paid = n_organic_to_paid / (n_touchpoints - 1) if n_touchpoints > 1 else 0.0
        
        channel_counts = {}
        for c in channels:
            channel_counts[c] = channel_counts.get(c, 0) + 1
        entropy = 0.0
        for c, count in channel_counts.items():
            p = count / n_touchpoints
            entropy -= p * np.log(p)
            
        all_channels_list = ["Direct Traffic", "Display Ads", "Email", "Referral", "Search Ads", "Social Media"]
        counts_dict = {f"count_{c.lower().replace(' ', '_')}": float(channel_counts.get(c, 0)) for c in all_channels_list}
        props_dict = {f"prop_{c.lower().replace(' ', '_')}": float(channel_counts.get(c, 0) / n_touchpoints) for c in all_channels_list}
        
        first_touch_channel = channels[0]
        last_touch_channel = channels[-1]
        second_touch_channel = channels[1] if n_touchpoints > 1 else "None"
        penultimate_touch_channel = channels[-2] if n_touchpoints > 1 else "None"
        first_touch_campaign = campaigns[0]
        last_touch_campaign = campaigns[-1]
        
        sorted_counts = sorted(channel_counts.items(), key=lambda x: (-x[1], x[0]))
        most_frequent_channel = sorted_counts[0][0]
        
        count_first_half = 0
        count_second_half = 0
        first_half_counts = {c: 0 for c in all_channels_list}
        second_half_counts = {c: 0 for c in all_channels_list}
        
        if journey_duration_hours == 0:
            count_first_half = n_touchpoints
            for c in channels:
                first_half_counts[c] += 1
        else:
            t_mid = t_first + (t_last - t_first) / 2
            for c, t in zip(channels, timestamps):
                if t <= t_mid:
                    count_first_half += 1
                    first_half_counts[c] += 1
                else:
                    count_second_half += 1
                    second_half_counts[c] += 1
                    
        prop_touchpoints_first_half = count_first_half / n_touchpoints
        prop_touchpoints_second_half = count_second_half / n_touchpoints
        
        first_half_counts_dict = {f"count_first_half_{c.lower().replace(' ', '_')}": float(first_half_counts[c]) for c in all_channels_list}
        second_half_counts_dict = {f"count_second_half_{c.lower().replace(' ', '_')}": float(second_half_counts[c]) for c in all_channels_list}
        
        first_last_same = 1 if first_touch_channel == last_touch_channel else 0
        first_touch_repeated = 1 if channel_counts.get(first_touch_channel, 0) > 1 else 0
        
        converted_any_yes = int(group["converted_any_yes"].iloc[0])
        
        row = {
            "user_id": user_id,
            "n_touchpoints": float(n_touchpoints),
            "n_unique_channels": float(n_unique_channels),
            "journey_duration_hours": journey_duration_hours,
            "repeat_touchpoint_count": float(repeat_touchpoint_count),
            "repeat_touchpoint_ratio": repeat_touchpoint_ratio,
            "mean_time_between_touchpoints": mean_time_between_touchpoints,
            "median_time_between_touchpoints": median_time_between_touchpoints,
            "max_time_gap": max_time_gap,
            "n_channel_transitions": float(n_channel_transitions),
            "n_unique_transitions": float(n_unique_transitions),
            "channel_switch_rate": channel_switch_rate,
            "journey_entropy": entropy,
            "first_touch_channel": first_touch_channel,
            "last_touch_channel": last_touch_channel,
            "second_touch_channel": second_touch_channel,
            "penultimate_touch_channel": penultimate_touch_channel,
            "first_touch_campaign": first_touch_campaign,
            "last_touch_campaign": last_touch_campaign,
            "most_frequent_channel": most_frequent_channel,
            "prop_touchpoints_first_half": prop_touchpoints_first_half,
            "prop_touchpoints_second_half": prop_touchpoints_second_half,
            "n_consecutive_same": float(n_consecutive_same),
            "n_consecutive_diff": float(n_consecutive_diff),
            "prop_paid_to_organic": prop_paid_to_organic,
            "prop_organic_to_paid": prop_organic_to_paid,
            "first_last_same": float(first_last_same),
            "first_touch_repeated": float(first_touch_repeated),
            "converted_any_yes": converted_any_yes
        }
        row.update(counts_dict)
        row.update(props_dict)
        row.update(first_half_counts_dict)
        row.update(second_half_counts_dict)
        
        rows.append(row)
        
    return pd.DataFrame(rows)


def _get_data_splits(
    X: pd.DataFrame, y: pd.Series
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    X_model = X.copy()
    y_model = y.astype(int)

    X_train, X_temp, y_train, y_temp = train_test_split(
        X_model,
        y_model,
        test_size=0.30,
        random_state=RANDOM_SEED,
        stratify=y_model,
    )

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
    X_train_const = sm.add_constant(X_train, has_constant="add")
    fitted = sm.Logit(y_train, X_train_const).fit(disp=0, maxiter=300)

    y_prob_test = fitted.predict(sm.add_constant(X_test, has_constant="add"))
    y_pred_test = (y_prob_test >= 0.5).astype(int)
    
    accuracy = float(accuracy_score(y_test, y_pred_test))
    precision = float(precision_score(y_test, y_pred_test, zero_division=0))
    recall = float(recall_score(y_test, y_pred_test, zero_division=0))
    f1 = float(f1_score(y_test, y_pred_test, zero_division=0))
    
    if y_test.nunique() > 1:
        roc_auc = float(roc_auc_score(y_test, y_prob_test))
    else:
        roc_auc = np.nan

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
        "auc_test": roc_auc,
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

        train_metrics = compute_metrics(y_train, y_prob_train)
        valid_metrics = compute_metrics(y_valid, y_prob_valid)
        test_metrics = compute_metrics(y_test, y_prob_test)

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

    # --- COMPATIBILITY STAGE ---
    coef_tables: list[pd.DataFrame] = []
    metric_rows: list[dict[str, float]] = []
    all_split_summaries: list[dict] = []
    all_metrics_list: list[dict] = []
    all_tuning_results: list[dict] = []
    all_best_hyperparameters: list[dict] = []

    def process_model_compatibility(model_name: str, X: pd.DataFrame, y: pd.Series, drop_direct_traffic: bool = False):
        if drop_direct_traffic:
            X_processed = X.drop(columns=["channel_direct_traffic"])
        else:
            X_processed = X

        X_train, y_train, X_valid, y_valid, X_test, y_test, X_model, y_model = _get_data_splits(X_processed, y)
        
        coef_sm, metrics_sm = _fit_statsmodels_logit(model_name, X_train, y_train, X_test, y_test, X_model, y_model)
        coef_tables.append(coef_sm)
        metric_rows.append(metrics_sm)

        split_summaries = [
            {"split": "Train", "n_samples": len(y_train), "n_converted": int(y_train.sum()), "n_not_converted": len(y_train)-int(y_train.sum()), "conversion_rate": float(y_train.mean())},
            {"split": "Validation", "n_samples": len(y_valid), "n_converted": int(y_valid.sum()), "n_not_converted": len(y_valid)-int(y_valid.sum()), "conversion_rate": float(y_valid.mean())},
            {"split": "Test", "n_samples": len(y_test), "n_converted": int(y_test.sum()), "n_not_converted": len(y_test)-int(y_test.sum()), "conversion_rate": float(y_test.mean())},
        ]
        for s in split_summaries:
            s["model"] = model_name
        all_split_summaries.extend(split_summaries)

        tuning_results, best_hps_row = _tune_sklearn_logistic_model(
            model_name, X_train, y_train, X_valid, y_valid, X_test, y_test
        )
        all_tuning_results.extend(tuning_results)
        all_best_hyperparameters.append(best_hps_row)

        best_C_for_model = best_hps_row["best_C"]
        best_lr_model = LogisticRegression(
            C=best_C_for_model, solver="liblinear", max_iter=1000, random_state=RANDOM_SEED
        )
        best_lr_model.fit(X_train, y_train)

        y_prob_train_best = best_lr_model.predict_proba(X_train)[:, 1]
        y_prob_valid_best = best_lr_model.predict_proba(X_valid)[:, 1]
        y_prob_test_best = best_lr_model.predict_proba(X_test)[:, 1]

        tr_m = compute_metrics(y_train, y_prob_train_best)
        val_m = compute_metrics(y_valid, y_prob_valid_best)
        te_m = compute_metrics(y_test, y_prob_test_best)
        
        all_metrics_list.append({"split": "Train", "model": model_name, "accuracy": tr_m["accuracy"], "precision": tr_m["precision"], "recall": tr_m["recall"], "f1": tr_m["f1"], "roc_auc": tr_m["roc_auc"]})
        all_metrics_list.append({"split": "Validation", "model": model_name, "accuracy": val_m["accuracy"], "precision": val_m["precision"], "recall": val_m["recall"], "f1": val_m["f1"], "roc_auc": val_m["roc_auc"]})
        all_metrics_list.append({"split": "Test", "model": model_name, "accuracy": te_m["accuracy"], "precision": te_m["precision"], "recall": te_m["recall"], "f1": te_m["f1"], "roc_auc": te_m["roc_auc"]})

    # Compatibility runs
    row_X = _row_channel_matrix(touchpoints)
    process_model_compatibility("row_channel", row_X, touchpoints["is_conversion"].astype(int), drop_direct_traffic=True)
    process_model_compatibility("user_any_channel", users[CHANNEL_FEATURES], users["converted_any_yes"].astype(int))
    process_model_compatibility("journey_length_only", users[["n_touchpoints"]], users["converted_any_yes"].astype(int))
    process_model_compatibility("channel_plus_length", users[CHANNEL_FEATURES + ["n_touchpoints"]], users["converted_any_yes"].astype(int))

    # Save compatibility outputs
    split_summary_df = pd.DataFrame(all_split_summaries)
    metrics_summary_df = pd.DataFrame(all_metrics_list)
    coefficients = pd.concat(coef_tables, ignore_index=True).round(6)
    model_metrics = pd.DataFrame(metric_rows).round(6)
    tuning_results_df = pd.DataFrame(all_tuning_results).round(6)
    best_hyperparameters_df = pd.DataFrame(all_best_hyperparameters).round(6)

    channel_plus = coefficients[coefficients["model"].eq("channel_plus_length") & coefficients["term"].isin(CHANNEL_FEATURES)].copy()
    channel_plus["channel"] = channel_plus["term"].map(DISPLAY_NAMES)
    channel_plus["score"] = np.exp(channel_plus["coef"] - channel_plus["coef"].max())
    channel_plus["logistic_adjusted_share_pct"] = (channel_plus["score"] / channel_plus["score"].sum() * 100.0)
    adjusted_share = channel_plus[["channel", "logistic_adjusted_share_pct", "coef", "odds_ratio", "p_value"]].round(6)

    split_summary_df.to_csv(OUTPUT_DIR / "split_summary.csv", index=False)
    metrics_summary_df.to_csv(OUTPUT_DIR / "logistic_regression_metrics.csv", index=False)
    model_metrics.to_csv(OUTPUT_DIR / "rq2_logistic_model_metrics.csv", index=False)
    coefficients.to_csv(OUTPUT_DIR / "rq2_logistic_model_coefficients.csv", index=False)
    adjusted_share.to_csv(OUTPUT_DIR / "rq2_logistic_adjusted_channel_share.csv", index=False)
    users.to_csv(OUTPUT_DIR / "rq2_logistic_user_model_matrix.csv", index=False)
    tuning_results_df.to_csv(OUTPUT_DIR / "hyperparameter_tuning_results.csv", index=False)
    best_hyperparameters_df.to_csv(OUTPUT_DIR / "best_hyperparameters.csv", index=False)

    # --- ENHANCED RESEARCH STAGE ---
    print("Generating enhanced journey features...")
    enhanced_df = build_user_journey_features(touchpoints)
    
    # Feature distribution summary and dictionary are handled in README documentation.

    # Save Data Leakage Check
    leakage_check_rows = []
    all_potential_features = list(enhanced_df.columns) + ["conversion", "is_conversion"]
    for feat in all_potential_features:
        if feat == "user_id":
            continue
        is_leak = feat in LEAKAGE_FEATURES
        reason = "Directly contains target or target-derived information" if is_leak else "Calculated strictly prior to target outcome"
        attempting = "None" if is_leak else "enhanced_journey_logistic"
        action = "Excluded from predictor variables" if is_leak else "Allowed"
        leakage_check_rows.append({
            "feature_name": feat, "leakage_status": "Leakage" if is_leak else "Safe", "reason": reason, "model_attempting": attempting, "handling_action": action
        })
    pd.DataFrame(leakage_check_rows).to_csv(OUTPUT_DIR / "leakage_feature_check.csv", index=False)

    # Pre-generate Repeated Stratified K-Fold splits
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=42)
    
    # Define model structures and preprocessing
    from pandas.api.types import is_numeric_dtype
    all_features = [c for c in enhanced_df.columns if c not in ["user_id", "converted_any_yes"]]
    cat_features = [c for c in all_features if not is_numeric_dtype(enhanced_df[c])]
    num_features = [c for c in all_features if is_numeric_dtype(enhanced_df[c])]
    
    full_preprocessor = build_preprocessing_pipeline(num_features, cat_features)
    
    models = {
        "user_any_channel": {
            "features": CHANNEL_FEATURES,
            "preprocessor": build_preprocessing_pipeline(CHANNEL_FEATURES, []),
            "model": LogisticRegression(C=1.0, solver="liblinear", random_state=42),
            "feature_set_name": "channel_presence_only"
        },
        "journey_length_only": {
            "features": ["n_touchpoints"],
            "preprocessor": build_preprocessing_pipeline(["n_touchpoints"], []),
            "model": LogisticRegression(C=1.0, solver="liblinear", random_state=42),
            "feature_set_name": "journey_length_only"
        },
        "channel_plus_length": {
            "features": CHANNEL_FEATURES + ["n_touchpoints"],
            "preprocessor": build_preprocessing_pipeline(CHANNEL_FEATURES + ["n_touchpoints"], []),
            "model": LogisticRegression(C=1.0, solver="liblinear", random_state=42),
            "feature_set_name": "channel_presence_plus_length"
        },
        "enhanced_journey_logistic": {
            "features": all_features,
            "preprocessor": full_preprocessor,
            "model": LogisticRegression(C=1.0, solver="liblinear", random_state=42),
            "feature_set_name": "full_enhanced_features"
        },
        "enhanced_journey_logistic_balanced": {
            "features": all_features,
            "preprocessor": full_preprocessor,
            "model": LogisticRegression(C=1.0, solver="liblinear", class_weight="balanced", random_state=42),
            "feature_set_name": "full_enhanced_features_balanced"
        },
        "random_forest": {
            "features": all_features,
            "preprocessor": full_preprocessor,
            "model": RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
            "feature_set_name": "full_enhanced_features"
        },
        "extra_trees": {
            "features": all_features,
            "preprocessor": full_preprocessor,
            "model": ExtraTreesClassifier(n_estimators=100, random_state=42, n_jobs=-1),
            "feature_set_name": "full_enhanced_features"
        },
        "gradient_boosting": {
            "features": all_features,
            "preprocessor": full_preprocessor,
            "model": HistGradientBoostingClassifier(random_state=42),
            "feature_set_name": "full_enhanced_features"
        }
    }

    # Holdout Split
    users_merged = users.merge(enhanced_df, on=["user_id", "converted_any_yes", "n_touchpoints"], how="left")
    feature_cols = [c for c in users_merged.columns if c not in ["user_id", "converted_any_yes"]]
    X_full = users_merged[feature_cols]
    y_full = users_merged["converted_any_yes"]
    
    X_train, y_train, X_valid, y_valid, X_test, y_test, X_model, y_model = _get_data_splits(X_full, y_full)
    
    # Tune and update models with best C
    for m_name, m_info in models.items():
        if "logistic" in m_name or m_name in ["user_any_channel", "journey_length_only", "channel_plus_length"]:
            feats = m_info["features"]
            prep = m_info["preprocessor"]
            
            X_tr_p = prep.fit_transform(X_train[feats])
            X_val_p = prep.transform(X_valid[feats])
            
            class_w = m_info["model"].class_weight
            best_m, best_c = tune_and_fit_logistic(m_name, X_tr_p, y_train, X_val_p, y_valid, class_weight=class_w)
            models[m_name]["model"] = LogisticRegression(C=best_c, solver="liblinear", class_weight=class_w, random_state=42)
            print(f"Tuned C for {m_name}: {best_c}")

    # Evaluate Row Channel in Repeated Stratified CV
    row_cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=42)
    row_X_cv = row_X.drop(columns=["channel_direct_traffic"])
    row_y_cv = touchpoints["is_conversion"].astype(int)
    row_model = LogisticRegression(C=1.0, solver="liblinear", random_state=42)
    
    row_fold_results = []
    print("Evaluating row_channel in Repeated CV...")
    for rep, (train_idx, test_idx) in enumerate(row_cv.split(row_X_cv, row_y_cv)):
        rep_id = rep // 5
        fold_id = rep % 5
        
        X_tr_f, y_tr_f = row_X_cv.iloc[train_idx], row_y_cv.iloc[train_idx]
        X_te_f, y_te_f = row_X_cv.iloc[test_idx], row_y_cv.iloc[test_idx]
        
        scaler = StandardScaler()
        X_tr_f_s = scaler.fit_transform(X_tr_f)
        X_te_f_s = scaler.transform(X_te_f)
        
        row_model.fit(X_tr_f_s, y_tr_f)
        y_prob_f = row_model.predict_proba(X_te_f_s)[:, 1]
        
        metrics_f = compute_metrics(y_te_f, y_prob_f)
        metrics_f.update({
            "model": "row_channel", "feature_set": "row_channel_presence", "repeat": rep_id, "fold": fold_id,
            "random_state": RANDOM_SEED, "n_train": len(y_tr_f), "n_test": len(y_te_f),
            "positive_rate_train": float(y_tr_f.mean()), "positive_rate_test": float(y_te_f.mean())
        })
        row_fold_results.append(metrics_f)

    # Evaluate User-level Models in Repeated Stratified CV
    user_fold_results = {}
    for m_name in models.keys():
        user_fold_results[m_name] = []
        
    print("Evaluating user-level models in Repeated CV...")
    for rep_fold_idx, (train_idx, test_idx) in enumerate(cv.split(X_model, y_model)):
        rep_id = rep_fold_idx // 5
        fold_id = rep_fold_idx % 5
        
        X_tr_f, y_tr_f = X_model.iloc[train_idx], y_model.iloc[train_idx]
        X_te_f, y_te_f = X_model.iloc[test_idx], y_model.iloc[test_idx]
        
        for m_name, m_info in models.items():
            feats = m_info["features"]
            prep = m_info["preprocessor"]
            clf = m_info["model"]
            
            X_tr_f_p = prep.fit_transform(X_tr_f[feats])
            X_te_f_p = prep.transform(X_te_f[feats])
            
            clf.fit(X_tr_f_p, y_tr_f)
            y_prob_f = clf.predict_proba(X_te_f_p)[:, 1]
            
            metrics_f = compute_metrics(y_te_f, y_prob_f)
            metrics_f.update({
                "model": m_name, "feature_set": m_info["feature_set_name"], "repeat": rep_id, "fold": fold_id,
                "random_state": RANDOM_SEED, "n_train": len(y_tr_f), "n_test": len(y_te_f),
                "positive_rate_train": float(y_tr_f.mean()), "positive_rate_test": float(y_te_f.mean())
            })
            user_fold_results[m_name].append(metrics_f)
            
    # Combine fold results
    all_fold_rows = row_fold_results.copy()
    for m_name, f_results in user_fold_results.items():
        all_fold_rows.extend(f_results)
    
    cv_fold_df = pd.DataFrame(all_fold_rows)
    cv_fold_df.to_csv(OUTPUT_DIR / "repeated_cv_fold_results.csv", index=False)

    # Compute summary repeated CV metrics
    cv_summary_rows = []
    for m_name in ["row_channel"] + list(models.keys()):
        m_df = cv_fold_df[cv_fold_df["model"] == m_name]
        n_folds = len(m_df)
        
        roc_aucs = m_df["roc_auc"].dropna()
        pr_aucs = m_df["pr_auc"].dropna()
        
        mean_roc = float(roc_aucs.mean())
        std_roc = float(roc_aucs.std())
        median_roc = float(roc_aucs.median())
        min_roc = float(roc_aucs.min())
        max_roc = float(roc_aucs.max())
        
        se = std_roc / np.sqrt(n_folds)
        ci_lower = mean_roc - 1.96 * se
        ci_upper = mean_roc + 1.96 * se
        
        feature_set_name = m_df["feature_set"].iloc[0]
        n_raw = len(models[m_name]["features"]) if m_name in models else len(row_X_cv.columns)
        if m_name in models:
            prep_temp = models[m_name]["preprocessor"]
            n_enc = prep_temp.fit_transform(X_model[models[m_name]["features"]]).shape[1]
        else:
            n_enc = row_X_cv.shape[1]
            
        # Determine positive prevalence and analysis level
        if m_name == "row_channel":
            pos_prevalence = float(row_y_cv.mean())
            analysis_level = "touchpoint"
        else:
            pos_prevalence = float(y_model.mean())
            analysis_level = "user"
            
        cv_summary_rows.append({
            "model": m_name,
            "feature_set": feature_set_name,
            "n_raw_features": n_raw,
            "n_encoded_features": n_enc,
            "n_folds": n_folds,
            "mean_roc_auc": mean_roc,
            "std_roc_auc": std_roc,
            "median_roc_auc": median_roc,
            "min_roc_auc": min_roc,
            "max_roc_auc": max_roc,
            "ci_lower_95": ci_lower,
            "ci_upper_95": ci_upper,
            "mean_pr_auc": float(pr_aucs.mean()),
            "std_pr_auc": float(pr_aucs.std()),
            "positive_prevalence": pos_prevalence,
            "pr_auc_baseline": pos_prevalence,
            "pr_auc_improvement_over_baseline": float(pr_aucs.mean()) - pos_prevalence,
            "analysis_level": analysis_level,
            "mean_accuracy": float(m_df["accuracy"].mean()),
            "mean_balanced_accuracy": float(m_df["balanced_accuracy"].mean()),
            "mean_precision": float(m_df["precision"].mean()),
            "mean_recall": float(m_df["recall"].mean()),
            "mean_specificity": float(m_df["specificity"].mean()),
            "mean_f1": float(m_df["f1"].mean()),
            "mean_brier_score": float(m_df["brier_score"].mean()),
            "mean_log_loss": float(m_df["log_loss"].mean())
        })
    cv_summary_df = pd.DataFrame(cv_summary_rows)
    cv_summary_df.to_csv(OUTPUT_DIR / "repeated_cv_metrics.csv", index=False)

    # --- HOLDOUT EVALUATION AND PREDICTIONS ---
    print("Evaluating models on Holdout Test Split...")
    holdout_metrics_rows = []
    
    # For Row Channel (Holdout)
    row_X_train, row_y_train, row_X_val, row_y_val, row_X_test, row_y_test, row_X_full, row_y_full = _get_data_splits(row_X_cv, row_y_cv)
    scaler_r = StandardScaler()
    row_X_tr_s = scaler_r.fit_transform(row_X_train)
    row_X_te_s = scaler_r.transform(row_X_test)
    row_model.fit(row_X_tr_s, row_y_train)
    row_prob_te = row_model.predict_proba(row_X_te_s)[:, 1]
    
    row_te_m = compute_metrics(row_y_test, row_prob_te)
    pos_prevalence_row = float(row_y_test.mean())
    holdout_metrics_rows.append({
        "model": "row_channel", "feature_set": "row_channel_presence", "split": "Test",
        "roc_auc": row_te_m["roc_auc"], "pr_auc": row_te_m["pr_auc"], "accuracy": row_te_m["accuracy"],
        "balanced_accuracy": row_te_m["balanced_accuracy"], "precision": row_te_m["precision"],
        "recall": row_te_m["recall"], "specificity": row_te_m["specificity"], "f1": row_te_m["f1"],
        "brier_score": row_te_m["brier_score"], "log_loss": row_te_m["log_loss"],
        "n_samples": len(row_y_test), "positive_rate": pos_prevalence_row,
        "positive_prevalence": pos_prevalence_row,
        "pr_auc_baseline": pos_prevalence_row,
        "pr_auc_improvement_over_baseline": row_te_m["pr_auc"] - pos_prevalence_row,
        "analysis_level": "touchpoint"
    })
    
    holdout_preds_list = []
    row_pred_def = (row_prob_te >= 0.5).astype(int)
    for i, user_id in enumerate(touchpoints.loc[row_y_test.index, "user_id"]):
        holdout_preds_list.append({
            "model": "row_channel", "user_id": user_id, "split": "Test", "y_true": int(row_y_test.iloc[i]),
            "y_probability": float(row_prob_te[i]), "y_pred_default_threshold": int(row_pred_def[i]),
            "y_pred_selected_threshold": int(row_pred_def[i]), "selected_threshold": 0.5
        })
        
    user_test_probs = {}
    for m_name, m_info in models.items():
        feats = m_info["features"]
        prep = m_info["preprocessor"]
        clf = m_info["model"]
        
        X_tr_p = prep.fit_transform(X_train[feats])
        X_te_p = prep.transform(X_test[feats])
        X_val_p = prep.transform(X_valid[feats])
        
        clf.fit(X_tr_p, y_train)
        y_prob_te = clf.predict_proba(X_te_p)[:, 1]
        user_test_probs[m_name] = y_prob_te
        
        y_prob_val = clf.predict_proba(X_val_p)[:, 1]
        best_th = 0.5
        best_f1 = -1.0
        for th in np.arange(0.05, 0.95, 0.05):
            val_f1 = f1_score(y_valid, (y_prob_val >= th).astype(int), zero_division=0)
            if val_f1 > best_f1:
                best_f1 = val_f1
                best_th = th
                
        y_pred_def = (y_prob_te >= 0.5).astype(int)
        y_pred_sel = (y_prob_te >= best_th).astype(int)
        
        te_m = compute_metrics(y_test, y_prob_te)
        pos_prevalence_user = float(y_test.mean())
        holdout_metrics_rows.append({
            "model": m_name, "feature_set": m_info["feature_set_name"], "split": "Test",
            "roc_auc": te_m["roc_auc"], "pr_auc": te_m["pr_auc"], "accuracy": te_m["accuracy"],
            "balanced_accuracy": te_m["balanced_accuracy"], "precision": te_m["precision"],
            "recall": te_m["recall"], "specificity": te_m["specificity"], "f1": te_m["f1"],
            "brier_score": te_m["brier_score"], "log_loss": te_m["log_loss"],
            "n_samples": len(y_test), "positive_rate": pos_prevalence_user,
            "positive_prevalence": pos_prevalence_user,
            "pr_auc_baseline": pos_prevalence_user,
            "pr_auc_improvement_over_baseline": te_m["pr_auc"] - pos_prevalence_user,
            "analysis_level": "user"
        })
        
        for i in range(len(y_test)):
            holdout_preds_list.append({
                "model": m_name, "user_id": int(users_merged.loc[y_test.index[i], "user_id"]), "split": "Test",
                "y_true": int(y_test.iloc[i]), "y_probability": float(y_prob_te[i]),
                "y_pred_default_threshold": int(y_pred_def[i]), "y_pred_selected_threshold": int(y_pred_sel[i]),
                "selected_threshold": float(best_th)
            })

    pd.DataFrame(holdout_metrics_rows).to_csv(OUTPUT_DIR / "holdout_model_metrics.csv", index=False)
    pd.DataFrame(holdout_preds_list).to_csv(OUTPUT_DIR / "holdout_predictions.csv", index=False)

    cv_preds_rows = []
    print("Saving cross-validation predictions...")
    for rep_fold_idx, (train_idx, test_idx) in enumerate(cv.split(X_model, y_model)):
        rep_id = rep_fold_idx // 5
        fold_id = rep_fold_idx % 5
        
        X_tr_f, y_tr_f = X_model.iloc[train_idx], y_model.iloc[train_idx]
        X_te_f, y_te_f = X_model.iloc[test_idx], y_model.iloc[test_idx]
        
        for m_name, m_info in models.items():
            feats = m_info["features"]
            prep = m_info["preprocessor"]
            clf = m_info["model"]
            
            X_tr_f_p = prep.fit_transform(X_tr_f[feats])
            X_te_f_p = prep.transform(X_te_f[feats])
            clf.fit(X_tr_f_p, y_tr_f)
            y_prob_f = clf.predict_proba(X_te_f_p)[:, 1]
            
            for i in range(len(test_idx)):
                cv_preds_rows.append({
                    "model": m_name, "repeat": rep_id, "fold": fold_id,
                    "user_id": int(users_merged.loc[y_model.index[test_idx[i]], "user_id"]),
                    "y_true": int(y_te_f.iloc[i]), "y_probability": float(y_prob_f[i])
                })
    pd.DataFrame(cv_preds_rows).to_csv(OUTPUT_DIR / "cross_validation_predictions.csv", index=False)

    # --- FEATURE ABLATION STUDY ---
    print("Running feature ablation study...")
    ablation_sets = {
        "channel_presence_only": CHANNEL_FEATURES,
        "journey_length_only": ["n_touchpoints"],
        "channel_presence_plus_length": CHANNEL_FEATURES + ["n_touchpoints"],
        "channel_counts_only": [c for c in num_features if "count_" in c and "first_half" not in c and "second_half" not in c],
        "channel_proportions_only": [c for c in num_features if "prop_" in c and "first_half" not in c and "second_half" not in c],
        "channel_counts_plus_proportions": [c for c in num_features if ("count_" in c or "prop_" in c) and "first_half" not in c and "second_half" not in c],
        "journey_structure_only": [
            "n_touchpoints", "n_unique_channels", "journey_duration_hours", "repeat_touchpoint_count",
            "repeat_touchpoint_ratio", "mean_time_between_touchpoints", "median_time_between_touchpoints",
            "max_time_gap", "n_channel_transitions", "n_unique_transitions", "channel_switch_rate", "journey_entropy"
        ],
        "journey_position_only": cat_features + ["prop_touchpoints_first_half", "prop_touchpoints_second_half"] + [c for c in num_features if "first_half" in c or "second_half" in c],
        "sequence_summary_only": ["n_consecutive_same", "n_consecutive_diff", "prop_paid_to_organic", "prop_organic_to_paid", "first_last_same", "first_touch_repeated"],
        "full_enhanced_features": all_features
    }

    ref_cv_auc = cv_summary_df[cv_summary_df["model"] == "journey_length_only"]["mean_roc_auc"].values[0]
    ref_cv_pr = cv_summary_df[cv_summary_df["model"] == "journey_length_only"]["mean_pr_auc"].values[0]

    ablation_results = []
    for set_name, feats in ablation_sets.items():
        feats = list(dict.fromkeys(feats))
        print(f" Evaluating ablation set: {set_name}...")
        sub_cat = [c for c in feats if not is_numeric_dtype(users_merged[c])]
        sub_num = [c for c in feats if is_numeric_dtype(users_merged[c])]
        
        prep = build_preprocessing_pipeline(sub_num, sub_cat)
        
        X_tr_p = prep.fit_transform(X_train[feats])
        X_te_p = prep.transform(X_test[feats])
        X_val_p = prep.transform(X_valid[feats])
        
        clf, best_c = tune_and_fit_logistic(set_name, X_tr_p, y_train, X_val_p, y_valid)
        y_prob_te = clf.predict_proba(X_te_p)[:, 1]
        te_metrics = compute_metrics(y_test, y_prob_te)
        
        fold_aucs = []
        fold_prs = []
        ablation_preds_rows = []
        rep_fold_idx = 0
        for train_idx, test_idx in cv.split(X_model, y_model):
            rep_id = rep_fold_idx // 5
            fold_id = rep_fold_idx % 5
            
            X_tr_f, y_tr_f = X_model.iloc[train_idx], y_model.iloc[train_idx]
            X_te_f, y_te_f = X_model.iloc[test_idx], y_model.iloc[test_idx]
            
            X_tr_f_p = prep.fit_transform(X_tr_f[feats])
            X_te_f_p = prep.transform(X_te_f[feats])
            
            clf_cv = LogisticRegression(C=best_c, solver="liblinear", random_state=42)
            clf_cv.fit(X_tr_f_p, y_tr_f)
            y_prob_f = clf_cv.predict_proba(X_te_f_p)[:, 1]
            
            for i in range(len(test_idx)):
                ablation_preds_rows.append({
                    "model": set_name, "repeat": rep_id, "fold": fold_id,
                    "user_id": int(users_merged.loc[y_model.index[test_idx[i]], "user_id"]),
                    "y_true": int(y_te_f.iloc[i]), "y_probability": float(y_prob_f[i])
                })
                
            m_f = compute_metrics(y_te_f, y_prob_f)
            fold_aucs.append(m_f["roc_auc"])
            fold_prs.append(m_f["pr_auc"])
            rep_fold_idx += 1
            
        mean_cv_auc = float(np.mean(fold_aucs))
        std_cv_auc = float(np.std(fold_aucs))
        se = std_cv_auc / np.sqrt(len(fold_aucs))
        ci_lower = mean_cv_auc - 1.96 * se
        ci_upper = mean_cv_auc + 1.96 * se
        
        n_raw = len(feats)
        n_enc = prep.fit_transform(X_model[feats]).shape[1]
        
        # Compute paired user-level bootstrap CI for difference vs journey_length_only
        if set_name == "journey_length_only":
            ci_lower_inc = 0.0
            ci_upper_inc = 0.0
            mean_diff = 0.0
        else:
            df_ablation = pd.DataFrame(ablation_preds_rows)
            df_journey_preds = pd.DataFrame([r for r in cv_preds_rows if r["model"] == "journey_length_only"])
            df_comp = pd.concat([df_ablation, df_journey_preds])
            mean_diff, ci_lower_inc, ci_upper_inc = compute_paired_bootstrap_cv(df_comp, set_name, "journey_length_only", n_bootstraps=1000, random_seed=42)
            
        ablation_results.append({
            "feature_set": set_name,
            "n_raw_features": n_raw,
            "n_encoded_features": n_enc,
            "mean_cv_roc_auc": mean_cv_auc,
            "std_cv_roc_auc": std_cv_auc,
            "ci_lower_95": ci_lower,
            "ci_upper_95": ci_upper,
            "mean_cv_pr_auc": float(np.mean(fold_prs)),
            "holdout_test_roc_auc": te_metrics["roc_auc"],
            "holdout_test_pr_auc": te_metrics["pr_auc"],
            "brier_score": te_metrics["brier_score"],
            "incremental_auc_over_length_only": mean_diff,
            "ci_lower_incremental_auc": ci_lower_inc,
            "ci_upper_incremental_auc": ci_upper_inc,
            "incremental_pr_auc_over_length_only": float(np.mean(fold_prs)) - ref_cv_pr
        })
    pd.DataFrame(ablation_results).to_csv(OUTPUT_DIR / "feature_ablation_results.csv", index=False)

    # --- NONLINEAR ROBUSTNESS BENCHMARKS METRICS (NO SEPARATE CSV) ---
    nl_models = ["random_forest", "extra_trees", "gradient_boosting"]
    nl_aucs = [cv_summary_df[cv_summary_df["model"] == m]["mean_roc_auc"].values[0] for m in nl_models]
    best_nl_idx = np.argmax(nl_aucs)
    best_nl_model = nl_models[best_nl_idx]

    # --- STATISTICAL COMPARISONS (Paired Bootstrap at User Level) ---
    print("Performing statistical comparisons...")
    comparisons = [
        ("channel_plus_length", "journey_length_only"),
        ("enhanced_journey_logistic", "journey_length_only"),
        (best_nl_model, "channel_plus_length")
    ]
    
    stat_comparisons = []
    df_preds = pd.DataFrame(cv_preds_rows)
    
    for m1, m2 in comparisons:
        mean_diff, ci_low, ci_high = compute_paired_bootstrap_cv(df_preds, m1, m2, n_bootstraps=1000, random_seed=42)
        
        m2_cv_auc = cv_summary_df[cv_summary_df["model"] == m2]["mean_roc_auc"].values[0]
        rel_improvement = (mean_diff / m2_cv_auc) * 100.0 if m2_cv_auc > 0 else 0.0
        
        if m1 == "channel_plus_length" and m2 == "journey_length_only":
            interpretation = "Adding channel exposure produced a small but statistically detectable increase in ROC-AUC. However, the absolute improvement was only about 0.0037, indicating minimal practical predictive value beyond journey length."
        elif m1 == "enhanced_journey_logistic" and m2 == "journey_length_only":
            interpretation = "The enhanced feature set did not improve out-of-sample discrimination and may have introduced additional noise or unnecessary complexity."
        else:
            interpretation = f"The evaluated nonlinear benchmark did not extract stable additional predictive signal from the available feature set. This result does not prove that nonlinear relationships are absent, because performance may also depend on sample size, feature quality, label construction and hyperparameter settings."
            
        stat_comparisons.append({
            "comparison": f"{m1}_vs_{m2}",
            "mean_difference": mean_diff,
            "relative_auc_improvement_pct": rel_improvement,
            "ci_lower_95": ci_low,
            "ci_upper_95": ci_high,
            "comparison_method": "paired_bootstrap_at_user_level",
            "analysis_unit": "user",
            "dependency_correction": "pooled_out_of_fold_averaging",
            "interpretation": interpretation
        })
    pd.DataFrame(stat_comparisons).to_csv(OUTPUT_DIR / "statistical_model_comparisons.csv", index=False)

    # --- COEFFICIENTS AND ODDS RATIOS OF ENHANCED LOGISTIC REGRESSION ---
    print("Fitting Enhanced Journey Logistic on Train to extract Odds Ratios...")
    prep_full = build_preprocessing_pipeline(num_features, cat_features)
    X_train_encoded = prep_full.fit_transform(X_train[all_features])
    
    try:
        encoded_feature_names = list(prep_full.get_feature_names_out())
    except AttributeError:
        encoded_feature_names = []
        for name, transformer, columns in prep_full.transformers_:
            if name == 'remainder' and transformer == 'drop':
                continue
            if hasattr(transformer, 'get_feature_names_out'):
                encoded_feature_names.extend(transformer.get_feature_names_out(columns))
            elif hasattr(transformer, 'get_feature_names'):
                encoded_feature_names.extend(transformer.get_feature_names(columns))
            else:
                encoded_feature_names.extend(columns)
                
    best_c_enhanced = models["enhanced_journey_logistic"]["model"].C
    final_clf = LogisticRegression(C=best_c_enhanced, solver="liblinear", random_state=42)
    final_clf.fit(X_train_encoded, y_train)
    
    coefs_full = final_clf.coef_[0]
    intercept_full = final_clf.intercept_[0]
    
    print("Computing bootstrap standard errors for coefficients...")
    n_boot = 100
    boot_coefs = []
    for b in range(n_boot):
        idx = np.random.choice(len(X_train_encoded), size=len(X_train_encoded), replace=True)
        m_boot = LogisticRegression(C=best_c_enhanced, solver='liblinear', random_state=b)
        if len(np.unique(y_train.iloc[idx])) < 2:
            continue
        m_boot.fit(X_train_encoded[idx], y_train.iloc[idx])
        boot_coefs.append(np.append(m_boot.intercept_[0], m_boot.coef_[0]))
        
    boot_coefs = np.array(boot_coefs)
    stderrs = np.std(boot_coefs, axis=0)
    
    if len(stderrs) != len(coefs_full) + 1:
        stderrs = np.zeros(len(coefs_full) + 1)
        
    or_list = []
    
    terms = ["intercept"] + encoded_feature_names
    coef_vals = [intercept_full] + list(coefs_full)
    
    for idx, (term, val) in enumerate(zip(terms, coef_vals)):
        se_val = stderrs[idx]
        z_val = val / se_val if se_val > 0 else 0.0
        p_val = 2 * (1 - scipy_normal_cdf(abs(z_val))) if se_val > 0 else 1.0
        
        ci_low = val - 1.96 * se_val
        ci_high = val + 1.96 * se_val
        
        odds_ratio = np.exp(val)
        or_ci_low = np.exp(ci_low)
        or_ci_high = np.exp(ci_high)
        significant = "Yes" if p_val < 0.05 else "No"
        
        or_list.append({
            "term": term, 
            "coef": val, 
            "stderr": se_val, 
            "z": z_val, 
            "p_value": p_val,
            "ci_lower": ci_low, 
            "ci_upper": ci_high,
            "odds_ratio": odds_ratio, 
            "or_ci_lower": or_ci_low, 
            "or_ci_upper": or_ci_high,
            "significant": significant
        })
        
    pd.DataFrame(or_list).to_csv(OUTPUT_DIR / "enhanced_logistic_odds_ratios.csv", index=False)

    print("Pipeline complete. CSV outputs successfully generated in outputs folder.")
    return {
        "split_summary": split_summary_df,
        "metrics_summary": metrics_summary_df,
        "model_metrics": model_metrics,
        "model_coefficients": coefficients,
        "logistic_adjusted_channel_share": adjusted_share,
        "user_model_matrix": users,
        "hyperparameter_tuning_results": tuning_results_df,
        "best_hyperparameters": best_hyperparameters_df,
    }


def build_preprocessing_pipeline(numeric_cols: list[str], categorical_cols: list[str]) -> ColumnTransformer:
    transformers = []
    if numeric_cols:
        transformers.append(('num', Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ]), numeric_cols))
    if categorical_cols:
        try:
            ohe = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        except TypeError:
            ohe = OneHotEncoder(handle_unknown='ignore', sparse=False)
        transformers.append(('cat', Pipeline([
            ('imputer', SimpleImputer(strategy='constant', fill_value='None')),
            ('onehot', ohe)
        ]), categorical_cols))
    
    return ColumnTransformer(transformers=transformers, remainder='drop')


def tune_and_fit_logistic(model_name: str, X_train: np.ndarray, y_train: pd.Series, X_val: np.ndarray, y_val: pd.Series, class_weight: str | dict | None = None) -> tuple[LogisticRegression, float]:
    best_val_auc = -1.0
    best_c = 1.0
    best_model = None
    
    for c_val in C_VALUES:
        model = LogisticRegression(
            C=c_val, solver="liblinear", max_iter=1000, 
            random_state=RANDOM_SEED, class_weight=class_weight
        )
        model.fit(X_train, y_train)
        y_prob_val = model.predict_proba(X_val)[:, 1]
        
        if len(np.unique(y_val)) > 1:
            val_auc = roc_auc_score(y_val, y_prob_val)
        else:
            val_auc = 0.5
            
        if val_auc > best_val_auc:
            best_val_auc = val_auc
            best_c = c_val
            best_model = model
            
    return best_model, best_c


def bootstrap_auc_difference(y_true: pd.Series, y_prob1: np.ndarray, y_prob2: np.ndarray, n_bootstrap: int = 1000, seed: int = 42) -> tuple[list[float], list[float], list[float]]:
    np.random.seed(seed)
    n_samples = len(y_true)
    diffs = []
    auc1s = []
    auc2s = []
    
    y_true_arr = np.array(y_true)
    y_prob1_arr = np.array(y_prob1)
    y_prob2_arr = np.array(y_prob2)
    
    for _ in range(n_bootstrap):
        boot_indices = np.random.choice(n_samples, size=n_samples, replace=True)
        y_t_boot = y_true_arr[boot_indices]
        y_p1_boot = y_prob1_arr[boot_indices]
        y_p2_boot = y_prob2_arr[boot_indices]
        
        if len(np.unique(y_t_boot)) < 2:
            continue
            
        auc1 = float(roc_auc_score(y_t_boot, y_p1_boot))
        auc2 = float(roc_auc_score(y_t_boot, y_p2_boot))
        auc1s.append(auc1)
        auc2s.append(auc2)
        diffs.append(auc1 - auc2)
        
    return auc1s, auc2s, diffs


def fast_roc_auc_score(y_true: np.ndarray, y_score: np.ndarray) -> float:
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    
    desc_score_indices = np.argsort(y_score, kind="mergesort")[::-1]
    y_true = y_true[desc_score_indices]
    y_score = y_score[desc_score_indices]
    
    distinct_value_indices = np.where(np.diff(y_score))[0]
    threshold_idxs = np.r_[distinct_value_indices, y_true.size - 1]
    
    tps = np.cumsum(y_true)[threshold_idxs]
    fps = 1 + threshold_idxs - tps
    
    tps = np.r_[0, tps]
    fps = np.r_[0, fps]
    
    fpr = fps / fps[-1]
    tpr = tps / tps[-1]
    
    return float(np.sum((fpr[1:] - fpr[:-1]) * (tpr[1:] + tpr[:-1]) / 2.0))


def compute_paired_bootstrap_cv(df_preds: pd.DataFrame, m1: str, m2: str, n_bootstraps: int = 1000, random_seed: int = 42) -> tuple[float, float, float]:
    df1 = df_preds[df_preds["model"] == m1]
    df2 = df_preds[df_preds["model"] == m2]
    
    repeats_data = []
    for rep in range(10):
        sub1 = df1[df1["repeat"] == rep].set_index("user_id")
        sub2 = df2[df2["repeat"] == rep].set_index("user_id")
        common_users = sub1.index.intersection(sub2.index)
        
        rep_df = pd.DataFrame({
            "y_true": sub1.loc[common_users, "y_true"].values,
            "prob1": sub1.loc[common_users, "y_probability"].values,
            "prob2": sub2.loc[common_users, "y_probability"].values
        }, index=common_users).reset_index()
        repeats_data.append(rep_df)
        
    N = len(repeats_data[0])
    rng = np.random.default_rng(random_seed)
    
    boot_diffs = []
    original_diffs = []
    for rep_df in repeats_data:
        auc1 = fast_roc_auc_score(rep_df["y_true"].values, rep_df["prob1"].values)
        auc2 = fast_roc_auc_score(rep_df["y_true"].values, rep_df["prob2"].values)
        original_diffs.append(auc1 - auc2)
    mean_original_diff = float(np.mean(original_diffs))
    
    repeats_arrays = [(rep_df["y_true"].values, rep_df["prob1"].values, rep_df["prob2"].values) for rep_df in repeats_data]
    
    for _ in range(n_bootstraps):
        boot_indices = rng.choice(N, size=N, replace=True)
        sample_diffs = []
        for y_t_arr, p1_arr, p2_arr in repeats_arrays:
            y_t_boot = y_t_arr[boot_indices]
            if len(np.unique(y_t_boot)) < 2:
                continue
            auc1 = fast_roc_auc_score(y_t_boot, p1_arr[boot_indices])
            auc2 = fast_roc_auc_score(y_t_boot, p2_arr[boot_indices])
            sample_diffs.append(auc1 - auc2)
            
        if len(sample_diffs) > 0:
            boot_diffs.append(np.mean(sample_diffs))
            
    boot_diffs = np.array(boot_diffs)
    ci_lower = float(np.percentile(boot_diffs, 2.5))
    ci_upper = float(np.percentile(boot_diffs, 97.5))
    
    return mean_original_diff, ci_lower, ci_upper


def scipy_normal_cdf(x: float) -> float:
    from scipy.special import erf
    return float(0.5 * (1.0 + erf(x / np.sqrt(2.0))))


def main() -> None:
    results = run()
    
    print("\n--- Logistic Regression Tuning and Cross-Validation Complete ---")
    print(f"Output files generated in: {OUTPUT_DIR}")
    print(f" - Repeated CV summary: {OUTPUT_DIR / 'repeated_cv_metrics.csv'}")
    print(f" - Repeated CV fold results: {OUTPUT_DIR / 'repeated_cv_fold_results.csv'}")
    print(f" - Holdout metrics: {OUTPUT_DIR / 'holdout_model_metrics.csv'}")
    print(f" - Feature ablation results: {OUTPUT_DIR / 'feature_ablation_results.csv'}")
    print(f" - Statistical Comparisons: {OUTPUT_DIR / 'statistical_model_comparisons.csv'}")
    print(f" - Enhanced odds ratios: {OUTPUT_DIR / 'enhanced_logistic_odds_ratios.csv'}")
    print(f" - Holdout predictions: {OUTPUT_DIR / 'holdout_predictions.csv'}")
    print(f" - Cross-validation predictions: {OUTPUT_DIR / 'cross_validation_predictions.csv'}")
    print(f" - Leakage feature check: {OUTPUT_DIR / 'leakage_feature_check.csv'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Logistic model training, CV, and tuning failed: {exc}", file=sys.stderr)
        raise
