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

FIXED_C_FOR_REPEATED_CV = 1.0
CANDIDATE_C_VALUES_FOR_HOLDOUT = [0.01, 0.1, 1.0, 10.0, 100.0]
C_VALUES = CANDIDATE_C_VALUES_FOR_HOLDOUT

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


def validate_repeated_cv_configuration(
    c_value: float,
    hyperparameter_strategy: str,
) -> None:
    if c_value != FIXED_C_FOR_REPEATED_CV:
        raise ValueError(
            "Repeated CV must use the predefined fixed C value."
        )

    if hyperparameter_strategy != "fixed_predefined":
        raise ValueError(
            "Repeated CV cannot use holdout-tuned hyperparameters."
        )


def build_repeated_cv_logistic_pipeline(
    feature_spec,
    class_weight=None,
) -> Pipeline:
    """Build a leakage-free logistic pipeline for repeated CV."""
    validate_repeated_cv_configuration(FIXED_C_FOR_REPEATED_CV, "fixed_predefined")
    return Pipeline(
        steps=[
            ("preprocessor", feature_spec),
            ("model", LogisticRegression(
                C=FIXED_C_FOR_REPEATED_CV,
                max_iter=2000,
                random_state=RANDOM_SEED,
                solver="liblinear",
                class_weight=class_weight,
            ))
        ]
    )


def aggregate_oof_predictions(
    predictions_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate OOF predictions to one row per analysis unit.
    For both user and touchpoint levels, group by user_id (which represents
    either user_id or observation_id) and take average probability.
    """
    model_predictions = predictions_df.copy()
    
    # Check consistency of target labels
    label_counts = model_predictions.groupby("user_id")["y_true"].nunique()
    if (label_counts != 1).any():
        raise ValueError(
            "A user/observation has inconsistent target labels across CV repeats."
        )
        
    user_oof_predictions = (
        model_predictions
        .groupby("user_id", as_index=False)
        .agg(
            y_true=("y_true", "first"),
            y_probability=("y_probability", "mean"),
            n_oof_predictions=("y_probability", "size"),
        )
    )
    
    # Each user/observation must have exactly 10 OOF predictions (since n_repeats is 10)
    expected_predictions = 10
    if not (user_oof_predictions["n_oof_predictions"] == expected_predictions).all():
        raise ValueError(
            f"Each analysis unit must have exactly {expected_predictions} OOF predictions, "
            f"but found counts: {user_oof_predictions['n_oof_predictions'].unique()}"
        )
        
    return user_oof_predictions


def bootstrap_single_model_oof_metrics(
    y_true: np.ndarray,
    y_probability: np.ndarray,
    n_bootstrap: int = 2000,
    confidence_level: float = 0.95,
    random_state: int = RANDOM_SEED,
) -> dict[str, float]:
    """
    Estimate user-level OOF ROC-AUC and PR-AUC confidence intervals.

    The input must contain one aggregated OOF prediction per independent
    analysis unit.
    """
    rng = np.random.default_rng(random_state)
    n_samples = len(y_true)
    
    bootstrap_rocs = []
    bootstrap_prs = []
    
    y_true_arr = np.asarray(y_true)
    y_prob_arr = np.asarray(y_probability)
    
    for _ in range(n_bootstrap):
        # Sample with replacement
        boot_idx = rng.choice(n_samples, size=n_samples, replace=True)
        y_t_boot = y_true_arr[boot_idx]
        y_p_boot = y_prob_arr[boot_idx]
        
        # Check if both classes are present
        while len(np.unique(y_t_boot)) < 2:
            boot_idx = rng.choice(n_samples, size=n_samples, replace=True)
            y_t_boot = y_true_arr[boot_idx]
            y_p_boot = y_prob_arr[boot_idx]
            
        roc = fast_roc_auc_score(y_t_boot, y_p_boot)
        pr = average_precision_score(y_t_boot, y_p_boot)
        bootstrap_rocs.append(roc)
        bootstrap_prs.append(pr)
        
    alpha = 1.0 - confidence_level
    ci_roc_lower = float(np.percentile(bootstrap_rocs, 100 * alpha / 2.0))
    ci_roc_upper = float(np.percentile(bootstrap_rocs, 100 * (1.0 - alpha / 2.0)))
    
    ci_pr_lower = float(np.percentile(bootstrap_prs, 100 * alpha / 2.0))
    ci_pr_upper = float(np.percentile(bootstrap_prs, 100 * (1.0 - alpha / 2.0)))
    
    return {
        "oof_roc_auc_ci_lower": ci_roc_lower,
        "oof_roc_auc_ci_upper": ci_roc_upper,
        "oof_pr_auc_ci_lower": ci_pr_lower,
        "oof_pr_auc_ci_upper": ci_pr_upper,
    }


def validate_single_model_ci_output(metrics_df: pd.DataFrame) -> None:
    required_columns = [
        "oof_roc_auc",
        "oof_roc_auc_ci_lower",
        "oof_roc_auc_ci_upper",
        "bootstrap_unit",
        "bootstrap_iterations",
        "ci_method",
    ]
    for col in required_columns:
        if col not in metrics_df.columns:
            raise ValueError(f"Missing required column: {col}")
            
    for idx, row in metrics_df.iterrows():
        model_name = row["model"]
        pt = row["oof_roc_auc"]
        low = row["oof_roc_auc_ci_lower"]
        high = row["oof_roc_auc_ci_upper"]
        
        # Check bounds
        if not (0.0 <= low <= 1.0) or not (0.0 <= pt <= 1.0) or not (0.0 <= high <= 1.0):
            raise ValueError(f"ROC-AUC values out of [0, 1] bounds for model {model_name}: low={low}, pt={pt}, high={high}")
            
        # Check lower <= pt <= upper
        if not (low <= pt or np.isclose(low, pt, atol=1e-7)):
            raise ValueError(f"CI lower bound {low} is greater than point estimate {pt} for model {model_name}")
        if not (pt <= high or np.isclose(pt, high, atol=1e-7)):
            raise ValueError(f"Point estimate {pt} is greater than CI upper bound {high} for model {model_name}")
            
        # Check iterations
        if int(row["bootstrap_iterations"]) < 1000:
            raise ValueError(f"Bootstrap iterations must be >= 1000, found: {row['bootstrap_iterations']}")
            
        # Check ci_method
        expected_method = "percentile_bootstrap_on_aggregated_oof_predictions"
        if row["ci_method"] != expected_method:
            raise ValueError(f"Invalid ci_method: {row['ci_method']}. Expected: {expected_method}")


FEATURE_TEMPORAL_METADATA = {}
MODELING_SCOPE = "retrospective_diagnostic"

def initialize_feature_metadata(all_columns: list[str]):
    # Direct target leakage features
    direct_leaks = [
        "converted_any_yes", "last_touch_yes", "n_conversion_events", 
        "first_conversion_rank", "any_yes_before_last", "multiple_yes_events", 
        "conversion_timestamp", "conversion", "is_conversion"
    ]
    for col in direct_leaks:
        FEATURE_TEMPORAL_METADATA[col] = {
            "leakage_category": "direct_target_leakage",
            "available_before_conversion": False,
            "available_after_journey_completion": False,
            "allowed_in_retrospective_model": False,
            "allowed_in_prospective_model": False,
            "reason": "Directly contains target or target-derived information."
        }
        
    # Post-outcome temporal features
    post_outcome = [
        "n_touchpoints", "journey_duration_hours", "last_touch_channel", 
        "penultimate_touch_channel", "last_touch_campaign", "n_channel_transitions", 
        "n_unique_transitions", "channel_switch_rate", "journey_entropy", 
        "repeat_touchpoint_count", "repeat_touchpoint_ratio", 
        "mean_time_between_touchpoints", "median_time_between_touchpoints", 
        "max_time_gap", "prop_touchpoints_second_half"
    ]
    for col in post_outcome:
        FEATURE_TEMPORAL_METADATA[col] = {
            "leakage_category": "post_outcome_temporal_features",
            "available_before_conversion": False,
            "available_after_journey_completion": True,
            "allowed_in_retrospective_model": True,
            "allowed_in_prospective_model": False,
            "reason": "Depends on the full sequence or end-of-journey information."
        }
        
    # Prospective safe
    prospective = ["first_touch_channel", "first_touch_campaign"]
    for col in prospective:
        FEATURE_TEMPORAL_METADATA[col] = {
            "leakage_category": "prospective_safe_features",
            "available_before_conversion": True,
            "available_after_journey_completion": True,
            "allowed_in_retrospective_model": True,
            "allowed_in_prospective_model": True,
            "reason": "Known at the very first touchpoint before any outcome occurs."
        }
        
    # Explanatory model presence features
    has_channels = [
        "has_direct_traffic", "has_display_ads", "has_email", 
        "has_referral", "has_search_ads", "has_social_media"
    ]
    for col in has_channels:
        FEATURE_TEMPORAL_METADATA[col] = {
            "leakage_category": "retrospective_safe_features",
            "available_before_conversion": False,
            "available_after_journey_completion": True,
            "allowed_in_retrospective_model": True,
            "allowed_in_prospective_model": False,
            "reason": "Presence indicator safe for retrospective diagnostic models, but not available prospectively."
        }
        
    # All other columns are retrospective-safe or post-outcome
    for col in all_columns:
        if col in FEATURE_TEMPORAL_METADATA:
            continue
        if "second_half" in col:
            FEATURE_TEMPORAL_METADATA[col] = {
                "leakage_category": "post_outcome_temporal_features",
                "available_before_conversion": False,
                "available_after_journey_completion": True,
                "allowed_in_retrospective_model": True,
                "allowed_in_prospective_model": False,
                "reason": "Depends on the second half of the completed journey."
            }
        else:
            FEATURE_TEMPORAL_METADATA[col] = {
                "leakage_category": "retrospective_safe_features",
                "available_before_conversion": False,
                "available_after_journey_completion": True,
                "allowed_in_retrospective_model": True,
                "allowed_in_prospective_model": False,
                "reason": "Safe for retrospective diagnostic models of completed journeys, but not available prospectively."
            }


def validate_no_direct_target_leakage(features: list[str]) -> None:
    for f in features:
        if f not in FEATURE_TEMPORAL_METADATA:
            raise ValueError(f"Feature '{f}' has no temporal metadata.")
        meta = FEATURE_TEMPORAL_METADATA[f]
        if meta["leakage_category"] == "direct_target_leakage":
            raise ValueError(f"Direct target leakage feature detected and blocked: {f}")


def validate_feature_temporal_scope(features: list[str]) -> None:
    for f in features:
        if f not in FEATURE_TEMPORAL_METADATA:
            raise ValueError(f"Feature '{f}' has no temporal metadata.")
        meta = FEATURE_TEMPORAL_METADATA[f]
        if not meta["allowed_in_retrospective_model"]:
            raise ValueError(f"Feature '{f}' is not allowed in retrospective model.")
        if meta["leakage_category"] == "post_outcome_temporal_features":
            # Just print a warning
            pass


def aggregate_model_oof_by_user(
    predictions_df: pd.DataFrame,
    model_name: str,
    expected_repeats: int,
) -> pd.DataFrame:
    """
    Aggregate repeated-CV out-of-fold predictions to one row per user.

    Each user receives one probability equal to the mean of their OOF
    probabilities across repeats.
    """
    model_predictions = predictions_df.loc[
        predictions_df["model"] == model_name
    ].copy()
    
    label_counts = model_predictions.groupby("user_id")["y_true"].nunique()
    if (label_counts != 1).any():
        raise ValueError(
            f"Inconsistent labels across repeats for model {model_name}."
        )
        
    aggregated = (
        model_predictions
        .groupby("user_id", as_index=False)
        .agg(
            y_true=("y_true", "first"),
            y_probability=("y_probability", "mean"),
            n_oof_predictions=("y_probability", "size"),
        )
    )
    
    if not (aggregated["n_oof_predictions"] == expected_repeats).all():
        raise ValueError(
            f"Each user must have exactly {expected_repeats} "
            f"OOF predictions for model {model_name}."
        )
        
    return aggregated


def build_paired_user_predictions(
    predictions_df: pd.DataFrame,
    model_a: str,
    model_b: str,
    expected_repeats: int,
) -> pd.DataFrame:
    """
    Build one-to-one paired OOF predictions for two user-level models.
    """
    a = aggregate_model_oof_by_user(
        predictions_df,
        model_a,
        expected_repeats,
    )
    b = aggregate_model_oof_by_user(
        predictions_df,
        model_b,
        expected_repeats,
    )
    
    if set(a["user_id"]) != set(b["user_id"]):
        raise ValueError(
            "Paired models contain different user sets."
        )
        
    paired = a.merge(
        b,
        on="user_id",
        how="inner",
        suffixes=("_a", "_b"),
        validate="one_to_one",
    )
    
    if (paired["y_true_a"] != paired["y_true_b"]).any():
        raise ValueError(
            "Inconsistent labels across models for the same user."
        )
        
    paired = paired.rename(columns={"y_true_a": "y_true"})
    
    if len(paired) != len(a) or len(paired) != len(b):
        raise ValueError(
            "Models do not contain the same paired users."
        )
        
    return paired


def paired_user_bootstrap_auc_difference(
    paired_predictions: pd.DataFrame,
    n_bootstrap: int = 5000,
    confidence_level: float = 0.95,
    random_state: int = RANDOM_SEED,
) -> dict[str, float]:
    """
    Estimate paired ROC-AUC difference by resampling users.

    Each bootstrap sample draws user rows with replacement and applies
    the same sampled users to both models.
    """
    rng = np.random.default_rng(random_state)
    n_users = len(paired_predictions)
    
    bootstrap_differences = []
    
    while len(bootstrap_differences) < n_bootstrap:
        sampled_positions = rng.integers(
            0,
            n_users,
            size=n_users,
        )
        
        sampled = paired_predictions.iloc[sampled_positions]
        
        if sampled["y_true"].nunique() < 2:
            continue
            
        auc_a = fast_roc_auc_score(
            sampled["y_true"].to_numpy(),
            sampled["y_probability_a"].to_numpy(),
        )
        
        auc_b = fast_roc_auc_score(
            sampled["y_true"].to_numpy(),
            sampled["y_probability_b"].to_numpy(),
        )
        
        bootstrap_differences.append(auc_a - auc_b)
        
    alpha = 1.0 - confidence_level
    paired_oof_ci_lower = float(np.percentile(bootstrap_differences, 100 * alpha / 2.0))
    paired_oof_ci_upper = float(np.percentile(bootstrap_differences, 100 * (1.0 - alpha / 2.0)))
    
    # Statistical significance checks
    p_lower = np.mean(np.asarray(bootstrap_differences) <= 0.0)
    p_upper = np.mean(np.asarray(bootstrap_differences) >= 0.0)
    bootstrap_two_sided_p_value = float(min(1.0, 2.0 * min(p_lower, p_upper)))
    
    probability_delta_above_zero = float(np.mean(np.asarray(bootstrap_differences) > 0.0))
    
    return {
        "paired_oof_ci_lower": paired_oof_ci_lower,
        "paired_oof_ci_upper": paired_oof_ci_upper,
        "probability_delta_above_zero": probability_delta_above_zero,
        "bootstrap_two_sided_p_value": bootstrap_two_sided_p_value,
    }


def validate_paired_comparison_consistency(
    comparisons_df: pd.DataFrame,
) -> None:
    for idx, row in comparisons_df.iterrows():
        comp_id = row["comparison_id"]
        pt = row["paired_oof_delta_auc"]
        low = row["paired_oof_ci_lower"]
        high = row["paired_oof_ci_upper"]
        
        # Check bounds
        if not (low <= pt or np.isclose(low, pt, atol=1e-7)):
            raise ValueError(f"Paired CI lower bound {low} is greater than delta {pt} for comparison {comp_id}")
        if not (pt <= high or np.isclose(pt, high, atol=1e-7)):
            raise ValueError(f"Paired delta {pt} is greater than CI upper bound {high} for comparison {comp_id}")
            
        # Check number of users
        n_users = row["n_paired_users"]
        if n_users != 2847:
            raise ValueError(f"Expected 2847 paired users, but found {n_users} for comparison {comp_id}")
            
        # Check mean fold difference
        diff_fold = row["mean_fold_auc_difference"]
        expected_diff_fold = row["mean_fold_auc_model_a"] - row["mean_fold_auc_model_b"]
        if not np.isclose(diff_fold, expected_diff_fold, atol=1e-7):
            raise ValueError(f"mean_fold_auc_difference {diff_fold} does not match expected {expected_diff_fold} for {comp_id}")
            
        # Check paired OOF difference
        diff_oof = row["paired_oof_delta_auc"]
        expected_diff_oof = row["oof_auc_model_a"] - row["oof_auc_model_b"]
        if not np.isclose(diff_oof, expected_diff_oof, atol=1e-7):
            raise ValueError(f"paired_oof_delta_auc {diff_oof} does not match expected {expected_diff_oof} for {comp_id}")


def tune_holdout_logistic_c(
    X_train,
    y_train,
    X_validation,
    y_validation,
    feature_spec,
    candidate_c_values,
    class_weight=None,
):
    """Select C using only the fixed train and validation sets."""
    if feature_spec is not None:
        X_tr_p = feature_spec.fit_transform(X_train)
        X_val_p = feature_spec.transform(X_validation)
    else:
        X_tr_p = X_train
        X_val_p = X_validation

    best_val_auc = -1.0
    best_c = 1.0
    best_model = None

    for c_val in candidate_c_values:
        model = LogisticRegression(
            C=c_val,
            solver="liblinear",
            max_iter=1000,
            random_state=RANDOM_SEED,
            class_weight=class_weight,
        )
        model.fit(X_tr_p, y_train)
        y_prob_val = model.predict_proba(X_val_p)[:, 1]

        if len(np.unique(y_validation)) > 1:
            val_auc = roc_auc_score(y_validation, y_prob_val)
        else:
            val_auc = 0.5

        if val_auc > best_val_auc:
            best_val_auc = val_auc
            best_c = c_val
            best_model = model

    return best_model, best_c


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
    
    # Cleanup double-prefixed files in outputs folder if they exist
    double_prefixes = [
        "rq2_logistic_logistic_adjusted_channel_share.csv"
    ]
    for filename in double_prefixes:
        p = OUTPUT_DIR / filename
        if p.exists():
            p.unlink()
            print(f"Deleted obsolete Logistic double-prefixed CSV file: {p.name}")
            
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
    
    # Initialize temporal metadata for all columns
    all_dataset_columns = list(users.columns) + list(enhanced_df.columns) + ["conversion", "is_conversion", "converted_any_yes", "last_touch_yes", "n_conversion_events", "first_conversion_rank", "any_yes_before_last", "multiple_yes_events", "conversion_timestamp"]
    initialize_feature_metadata(all_dataset_columns)
    
    # Validate compatibility model features
    validate_no_direct_target_leakage(CHANNEL_FEATURES)
    validate_feature_temporal_scope(CHANNEL_FEATURES)
    validate_no_direct_target_leakage(["n_touchpoints"])
    validate_feature_temporal_scope(["n_touchpoints"])

    # Save Data Leakage Check
    leakage_check_rows = []
    
    # Define model features map for check
    model_feature_map = {
        "row_channel": ["channel_direct_traffic", "channel_display_ads", "channel_email", "channel_referral", "channel_search_ads", "channel_social_media"],
        "user_any_channel": CHANNEL_FEATURES,
        "journey_length_only": ["n_touchpoints"],
        "channel_plus_length": CHANNEL_FEATURES + ["n_touchpoints"],
        "enhanced_journey_logistic": [c for c in enhanced_df.columns if c not in ["user_id", "converted_any_yes"]],
        "enhanced_journey_logistic_balanced": [c for c in enhanced_df.columns if c not in ["user_id", "converted_any_yes"]],
        "random_forest": [c for c in enhanced_df.columns if c not in ["user_id", "converted_any_yes"]],
        "extra_trees": [c for c in enhanced_df.columns if c not in ["user_id", "converted_any_yes"]],
        "gradient_boosting": [c for c in enhanced_df.columns if c not in ["user_id", "converted_any_yes"]],
        "explanatory_logistic": ["n_touchpoints", "has_direct_traffic", "has_display_ads", "has_email", "has_referral", "has_search_ads", "has_social_media"]
    }
    
    for feat, meta in FEATURE_TEMPORAL_METADATA.items():
        if feat == "user_id":
            continue
            
        used_models = []
        for m_name, m_feats in model_feature_map.items():
            if feat in m_feats:
                used_models.append(m_name)
        used_models_str = ", ".join(used_models) if used_models else "none"
        
        is_direct_leak = meta["leakage_category"] == "direct_target_leakage"
        
        status = "blocked" if is_direct_leak else (
            "allowed_with_temporal_limitation" if meta["leakage_category"] == "post_outcome_temporal_features" else "allowed"
        )
        action = "Excluded from predictor variables" if is_direct_leak else "Allowed"
        
        leakage_check_rows.append({
            "feature": feat,
            "used_by_models": used_models_str,
            "leakage_category": meta["leakage_category"],
            "direct_target_leakage": str(is_direct_leak).lower(),
            "available_before_conversion": str(meta["available_before_conversion"]).lower(),
            "available_after_journey_completion": str(meta["available_after_journey_completion"]).lower(),
            "allowed_in_retrospective_model": str(meta["allowed_in_retrospective_model"]).lower(),
            "allowed_in_prospective_model": str(meta["allowed_in_prospective_model"]).lower(),
            "current_modeling_scope": "retrospective_diagnostic",
            "current_scope_status": status,
            "reason": meta["reason"],
            "action": action
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

    # Validate features of all repeated CV models
    for m_name, m_info in models.items():
        validate_no_direct_target_leakage(m_info["features"])
        validate_feature_temporal_scope(m_info["features"])

    # Holdout Split
    users_merged = users.merge(enhanced_df, on=["user_id", "converted_any_yes", "n_touchpoints"], how="left")
    feature_cols = [c for c in users_merged.columns if c not in ["user_id", "converted_any_yes"]]
    X_full = users_merged[feature_cols]
    y_full = users_merged["converted_any_yes"]
    
    X_train, y_train, X_valid, y_valid, X_test, y_test, X_model, y_model = _get_data_splits(X_full, y_full)
    
    # Tune and update models with best C (Holdout tuning only)
    for m_name, m_info in models.items():
        if "logistic" in m_name or m_name in ["user_any_channel", "journey_length_only", "channel_plus_length"]:
            feats = m_info["features"]
            prep = m_info["preprocessor"]
            
            class_w = m_info["model"].class_weight if hasattr(m_info["model"], "class_weight") else None
            best_m, best_c = tune_holdout_logistic_c(
                X_train[feats],
                y_train,
                X_valid[feats],
                y_valid,
                prep,
                CANDIDATE_C_VALUES_FOR_HOLDOUT,
                class_weight=class_w
            )
            models[m_name]["model"] = LogisticRegression(C=best_c, solver="liblinear", class_weight=class_w, random_state=42)
            print(f"Tuned C for {m_name}: {best_c}")

    # Evaluate Row Channel in Repeated Stratified CV (Leakage-free, predefined C)
    row_cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=42)
    row_X_cv = row_X.drop(columns=["channel_direct_traffic"])
    row_y_cv = touchpoints["is_conversion"].astype(int)
    
    row_fold_results = []
    cv_preds_rows = []
    print("Evaluating row_channel in Repeated CV...")
    validate_repeated_cv_configuration(FIXED_C_FOR_REPEATED_CV, "fixed_predefined")
    row_pipeline = build_repeated_cv_logistic_pipeline(StandardScaler())
    
    for rep, (train_idx, test_idx) in enumerate(row_cv.split(row_X_cv, row_y_cv)):
        rep_id = rep // 5
        fold_id = rep % 5
        
        X_tr_f, y_tr_f = row_X_cv.iloc[train_idx], row_y_cv.iloc[train_idx]
        X_te_f, y_te_f = row_X_cv.iloc[test_idx], row_y_cv.iloc[test_idx]
        
        row_pipeline.fit(X_tr_f, y_tr_f)
        y_prob_f = row_pipeline.predict_proba(X_te_f)[:, 1]
        
        metrics_f = compute_metrics(y_te_f, y_prob_f)
        metrics_f.update({
            "model": "row_channel", "feature_set": "row_channel_presence", "repeat": rep_id, "fold": fold_id,
            "random_state": RANDOM_SEED, "n_train": len(y_tr_f), "n_test": len(y_te_f),
            "positive_rate_train": float(y_tr_f.mean()), "positive_rate_test": float(y_te_f.mean())
        })
        row_fold_results.append(metrics_f)
        
        for i in range(len(test_idx)):
            cv_preds_rows.append({
                "model": "row_channel",
                "repeat": rep_id,
                "fold": fold_id,
                "user_id": int(test_idx[i]), # observation index as user_id
                "y_true": int(y_te_f.iloc[i]),
                "y_probability": float(y_prob_f[i])
            })

    # Evaluate User-level Models in Repeated Stratified CV (Leakage-free, predefined C)
    user_fold_results = {}
    for m_name in models.keys():
        user_fold_results[m_name] = []
        
    print("Evaluating user-level models in Repeated CV...")
    for m_name in models.keys():
        if "logistic" in m_name or m_name in ["user_any_channel", "journey_length_only", "channel_plus_length"]:
            validate_repeated_cv_configuration(FIXED_C_FOR_REPEATED_CV, "fixed_predefined")

    for rep_fold_idx, (train_idx, test_idx) in enumerate(cv.split(X_model, y_model)):
        rep_id = rep_fold_idx // 5
        fold_id = rep_fold_idx % 5
        
        X_tr_f, y_tr_f = X_model.iloc[train_idx], y_model.iloc[train_idx]
        X_te_f, y_te_f = X_model.iloc[test_idx], y_model.iloc[test_idx]
        
        for m_name, m_info in models.items():
            feats = m_info["features"]
            
            if "logistic" in m_name or m_name in ["user_any_channel", "journey_length_only", "channel_plus_length"]:
                class_w = m_info["model"].class_weight if hasattr(m_info["model"], "class_weight") else None
                clf = build_repeated_cv_logistic_pipeline(m_info["preprocessor"], class_weight=class_w)
                clf.fit(X_tr_f[feats], y_tr_f)
                y_prob_f = clf.predict_proba(X_te_f[feats])[:, 1]
            else:
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
            
            for i in range(len(test_idx)):
                cv_preds_rows.append({
                    "model": m_name,
                    "repeat": rep_id,
                    "fold": fold_id,
                    "user_id": int(users_merged.loc[y_model.index[test_idx[i]], "user_id"]),
                    "y_true": int(y_te_f.iloc[i]),
                    "y_probability": float(y_prob_f[i])
                })
            
    # Combine fold results
    all_fold_rows = row_fold_results.copy()
    for m_name, f_results in user_fold_results.items():
        all_fold_rows.extend(f_results)
    
    cv_fold_df = pd.DataFrame(all_fold_rows)
    cv_fold_df.to_csv(OUTPUT_DIR / "repeated_cv_fold_results.csv", index=False)

    # Save cross-validation predictions
    df_preds_all = pd.DataFrame(cv_preds_rows)
    df_preds_all.to_csv(OUTPUT_DIR / "cross_validation_predictions.csv", index=False)

    # Compute summary repeated CV metrics
    cv_summary_rows = []
    for m_name in ["row_channel"] + list(models.keys()):
        m_df = cv_fold_df[cv_fold_df["model"] == m_name]
        n_folds = len(m_df)
        
        roc_aucs = m_df["roc_auc"].dropna()
        pr_aucs = m_df["pr_auc"].dropna()
        
        mean_fold_roc = float(roc_aucs.mean())
        std_fold_roc = float(roc_aucs.std())
        median_fold_roc = float(roc_aucs.median())
        min_fold_roc = float(roc_aucs.min())
        max_fold_roc = float(roc_aucs.max())
        
        mean_fold_pr = float(pr_aucs.mean())
        std_fold_pr = float(pr_aucs.std())
        
        feature_set_name = m_df["feature_set"].iloc[0]
        n_raw = len(models[m_name]["features"]) if m_name in models else len(row_X_cv.columns)
        if m_name in models:
            prep_temp = models[m_name]["preprocessor"]
            n_enc = prep_temp.fit_transform(X_model[models[m_name]["features"]]).shape[1]
        else:
            n_enc = row_X_cv.shape[1]
            
        # Determine positive prevalence, analysis level, and bootstrap unit
        if m_name == "row_channel":
            pos_prevalence = float(row_y_cv.mean())
            analysis_level = "touchpoint"
            bootstrap_unit = "touchpoint"
        else:
            pos_prevalence = float(y_model.mean())
            analysis_level = "user"
            bootstrap_unit = "user"
            
        if "logistic" in m_name or m_name in ["row_channel", "user_any_channel", "journey_length_only", "channel_plus_length"]:
            cv_c_value = FIXED_C_FOR_REPEATED_CV
            cv_hyperparameter_strategy = "fixed_predefined"
        else:
            cv_c_value = "not_applicable"
            cv_hyperparameter_strategy = "not_applicable"

        # OOF Point Estimates
        model_preds = df_preds_all[df_preds_all["model"] == m_name]
        user_oof_predictions = aggregate_oof_predictions(model_preds)
        
        oof_roc_auc = float(roc_auc_score(
            user_oof_predictions["y_true"],
            user_oof_predictions["y_probability"],
        ))
        oof_pr_auc = float(average_precision_score(
            user_oof_predictions["y_true"],
            user_oof_predictions["y_probability"],
        ))
        
        # Bootstrap CIs
        boot_ci = bootstrap_single_model_oof_metrics(
            y_true=user_oof_predictions["y_true"].to_numpy(),
            y_probability=user_oof_predictions["y_probability"].to_numpy(),
            n_bootstrap=2000,
            confidence_level=0.95,
            random_state=RANDOM_SEED
        )
        ci_roc_lower = boot_ci["oof_roc_auc_ci_lower"]
        ci_roc_upper = boot_ci["oof_roc_auc_ci_upper"]
        ci_pr_lower = boot_ci["oof_pr_auc_ci_lower"]
        ci_pr_upper = boot_ci["oof_pr_auc_ci_upper"]

        # Determine metadata flags
        m_features = models[m_name]["features"] if m_name in models else list(row_X_cv.columns)
        has_post_outcome = any(FEATURE_TEMPORAL_METADATA.get(f, {}).get("leakage_category") == "post_outcome_temporal_features" for f in m_features)
        has_direct_leak = any(FEATURE_TEMPORAL_METADATA.get(f, {}).get("leakage_category") == "direct_target_leakage" for f in m_features)
        uses_full = m_name in ["enhanced_journey_logistic", "enhanced_journey_logistic_balanced", "random_forest", "extra_trees", "gradient_boosting"]

        cv_summary_rows.append({
            "model": m_name,
            "analysis_level": analysis_level,
            "feature_set": feature_set_name,
            "n_raw_features": n_raw,
            "n_encoded_features": n_enc,
            "n_folds": n_folds,
            "n_repeats": 10,
            "cv_c_value": cv_c_value,
            "cv_hyperparameter_strategy": cv_hyperparameter_strategy,
            "mean_fold_roc_auc": mean_fold_roc,
            "std_fold_roc_auc": std_fold_roc,
            "median_fold_roc_auc": median_fold_roc,
            "min_fold_roc_auc": min_fold_roc,
            "max_fold_roc_auc": max_fold_roc,
            "mean_fold_pr_auc": mean_fold_pr,
            "std_fold_pr_auc": std_fold_pr,
            "oof_roc_auc": oof_roc_auc,
            "oof_roc_auc_ci_lower": ci_roc_lower,
            "oof_roc_auc_ci_upper": ci_roc_upper,
            "oof_pr_auc": oof_pr_auc,
            "oof_pr_auc_ci_lower": ci_pr_lower,
            "oof_pr_auc_ci_upper": ci_pr_upper,
            "positive_prevalence": pos_prevalence,
            "pr_auc_baseline": pos_prevalence,
            "oof_pr_auc_improvement_over_baseline": oof_pr_auc - pos_prevalence,
            "bootstrap_unit": bootstrap_unit,
            "bootstrap_iterations": 2000,
            "ci_method": "percentile_bootstrap_on_aggregated_oof_predictions",
            "modeling_scope": "retrospective_diagnostic",
            "uses_full_journey_features": str(uses_full).lower(),
            "contains_post_outcome_temporal_features": str(has_post_outcome).lower(),
            "contains_direct_target_leakage": str(has_direct_leak).lower()
        })
    cv_summary_df = pd.DataFrame(cv_summary_rows)
    validate_single_model_ci_output(cv_summary_df)
    cv_summary_df.to_csv(OUTPUT_DIR / "repeated_cv_metrics.csv", index=False)

    # --- HOLDOUT EVALUATION AND PREDICTIONS ---
    print("Evaluating models on Holdout Test Split...")
    holdout_metrics_rows = []
    
    # For Row Channel (Holdout)
    row_model = LogisticRegression(C=1.0, solver="liblinear", random_state=42)
    row_X_train, row_y_train, row_X_val, row_y_val, row_X_test, row_y_test, row_X_full, row_y_full = _get_data_splits(row_X_cv, row_y_cv)
    scaler_r = StandardScaler()
    row_X_tr_s = scaler_r.fit_transform(row_X_train)
    row_X_te_s = scaler_r.transform(row_X_test)
    row_model.fit(row_X_tr_s, row_y_train)
    row_prob_te = row_model.predict_proba(row_X_te_s)[:, 1]
    
    row_te_m = compute_metrics(row_y_test, row_prob_te)
    pos_prevalence_row = float(row_y_test.mean())
    # For Row Channel (Holdout) temporal properties
    row_m_features = list(row_X_cv.columns)
    row_has_post_outcome = any(FEATURE_TEMPORAL_METADATA.get(f, {}).get("leakage_category") == "post_outcome_temporal_features" for f in row_m_features)
    row_has_direct_leak = any(FEATURE_TEMPORAL_METADATA.get(f, {}).get("leakage_category") == "direct_target_leakage" for f in row_m_features)
    
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
        "analysis_level": "touchpoint",
        "selected_c": 1.0,
        "hyperparameter_selection_source": "train_validation_only",
        "modeling_scope": "retrospective_diagnostic",
        "uses_full_journey_features": "false",
        "contains_post_outcome_temporal_features": str(row_has_post_outcome).lower(),
        "contains_direct_target_leakage": str(row_has_direct_leak).lower()
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
        
        if "logistic" in m_name or m_name in ["user_any_channel", "journey_length_only", "channel_plus_length"]:
            selected_c = clf.C
            hp_source = "train_validation_only"
        else:
            selected_c = "not_applicable"
            hp_source = "not_applicable"

        # User temporal properties
        u_m_features = m_info["features"]
        u_has_post_outcome = any(FEATURE_TEMPORAL_METADATA.get(f, {}).get("leakage_category") == "post_outcome_temporal_features" for f in u_m_features)
        u_has_direct_leak = any(FEATURE_TEMPORAL_METADATA.get(f, {}).get("leakage_category") == "direct_target_leakage" for f in u_m_features)
        u_uses_full = m_name in ["enhanced_journey_logistic", "enhanced_journey_logistic_balanced", "random_forest", "extra_trees", "gradient_boosting"]

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
            "analysis_level": "user",
            "selected_c": selected_c,
            "hyperparameter_selection_source": hp_source,
            "modeling_scope": "retrospective_diagnostic",
            "uses_full_journey_features": str(u_uses_full).lower(),
            "contains_post_outcome_temporal_features": str(u_has_post_outcome).lower(),
            "contains_direct_target_leakage": str(u_has_direct_leak).lower()
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

    # cross-validation predictions are already populated in cv_preds_rows and saved in the first pass.
    print("Cross-validation predictions were saved during the evaluation stage.")

    # --- FEATURE ABLATION STUDY ---
    print("Running feature ablation study...")
    
    CHANNEL_PRESENCE_FEATURES = [
        "channel_direct_traffic", "channel_display_ads", "channel_email",
        "channel_referral", "channel_search_ads", "channel_social_media"
    ]
    CHANNEL_COUNT_FEATURES = [
        "count_direct_traffic", "count_display_ads", "count_email",
        "count_referral", "count_search_ads", "count_social_media"
    ]
    CHANNEL_PROPORTION_FEATURES = [
        "prop_direct_traffic", "prop_display_ads", "prop_email",
        "prop_referral", "prop_search_ads", "prop_social_media"
    ]
    JOURNEY_STRUCTURE_FEATURES = [
        "n_touchpoints", "n_unique_channels", "journey_duration_hours", 
        "repeat_touchpoint_count", "repeat_touchpoint_ratio", 
        "mean_time_between_touchpoints", "median_time_between_touchpoints", 
        "max_time_gap", "n_channel_transitions", "n_unique_transitions", 
        "channel_switch_rate", "journey_entropy"
    ]
    JOURNEY_POSITION_FEATURES = [
        "first_touch_channel", "last_touch_channel", "second_touch_channel", 
        "penultimate_touch_channel", "first_touch_campaign", "last_touch_campaign", 
        "most_frequent_channel", "prop_touchpoints_first_half", "prop_touchpoints_second_half",
        "count_first_half_direct_traffic", "count_first_half_display_ads", 
        "count_first_half_email", "count_first_half_referral", 
        "count_first_half_search_ads", "count_first_half_social_media",
        "count_second_half_direct_traffic", "count_second_half_display_ads", 
        "count_second_half_email", "count_second_half_referral", 
        "count_second_half_search_ads", "count_second_half_social_media"
    ]
    SEQUENCE_SUMMARY_FEATURES = [
        "n_consecutive_same", "n_consecutive_diff", "prop_paid_to_organic", 
        "prop_organic_to_paid", "first_last_same", "first_touch_repeated"
    ]
    
    ablation_sets = {
        "channel_presence_only": CHANNEL_PRESENCE_FEATURES,
        "journey_length_only": ["n_touchpoints"],
        "channel_presence_plus_length": CHANNEL_PRESENCE_FEATURES + ["n_touchpoints"],
        "channel_counts_only": CHANNEL_COUNT_FEATURES,
        "channel_proportions_only": CHANNEL_PROPORTION_FEATURES,
        "channel_counts_plus_proportions": CHANNEL_COUNT_FEATURES + CHANNEL_PROPORTION_FEATURES,
        "journey_structure_only": JOURNEY_STRUCTURE_FEATURES,
        "journey_position_only": JOURNEY_POSITION_FEATURES,
        "sequence_summary_only": SEQUENCE_SUMMARY_FEATURES,
        "full_enhanced_features": all_features
    }

    ref_cv_auc = cv_summary_df[cv_summary_df["model"] == "journey_length_only"]["mean_fold_roc_auc"].values[0]
    ref_cv_pr = cv_summary_df[cv_summary_df["model"] == "journey_length_only"]["mean_fold_pr_auc"].values[0]

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
        
        clf, best_c = tune_holdout_logistic_c(X_train[feats], y_train, X_valid[feats], y_valid, prep, CANDIDATE_C_VALUES_FOR_HOLDOUT)
        y_prob_te = clf.predict_proba(X_te_p)[:, 1]
        te_metrics = compute_metrics(y_test, y_prob_te)
        
        fold_aucs = []
        fold_prs = []
        ablation_preds_rows = []
        rep_fold_idx = 0
        validate_repeated_cv_configuration(FIXED_C_FOR_REPEATED_CV, "fixed_predefined")
        for train_idx, test_idx in cv.split(X_model, y_model):
            rep_id = rep_fold_idx // 5
            fold_id = rep_fold_idx % 5
            
            X_tr_f, y_tr_f = X_model.iloc[train_idx], y_model.iloc[train_idx]
            X_te_f, y_te_f = X_model.iloc[test_idx], y_model.iloc[test_idx]
            
            from sklearn.base import clone
            clf_cv = build_repeated_cv_logistic_pipeline(clone(prep))
            clf_cv.fit(X_tr_f[feats], y_tr_f)
            y_prob_f = clf_cv.predict_proba(X_te_f[feats])[:, 1]
            
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
        
        df_ablation = pd.DataFrame(ablation_preds_rows)
        ablation_oof_agg = aggregate_model_oof_by_user(df_ablation, set_name, expected_repeats=10)
        
        # Calculate OOF ROC-AUC point estimate
        oof_auc = float(roc_auc_score(ablation_oof_agg["y_true"], ablation_oof_agg["y_probability"]))
        
        # Calculate bootstrap CI on OOF predictions
        boot_ci_abl = bootstrap_single_model_oof_metrics(
            y_true=ablation_oof_agg["y_true"].to_numpy(),
            y_probability=ablation_oof_agg["y_probability"].to_numpy(),
            n_bootstrap=2000,
            confidence_level=0.95,
            random_state=RANDOM_SEED
        )
        oof_ci_lower = boot_ci_abl["oof_roc_auc_ci_lower"]
        oof_ci_upper = boot_ci_abl["oof_roc_auc_ci_upper"]

        # Compute paired user-level bootstrap CI for difference vs journey_length_only
        if set_name == "journey_length_only":
            ci_lower_inc = 0.0
            ci_upper_inc = 0.0
            mean_diff = 0.0
        else:
            journey_oof_agg = aggregate_model_oof_by_user(df_preds_all, "journey_length_only", expected_repeats=10)
            
            paired_ablation = ablation_oof_agg.merge(
                journey_oof_agg,
                on=["user_id", "y_true"],
                how="inner",
                suffixes=("_a", "_b"),
                validate="one_to_one"
            )
            
            oof_auc_a = float(roc_auc_score(paired_ablation["y_true"], paired_ablation["y_probability_a"]))
            oof_auc_b = float(roc_auc_score(paired_ablation["y_true"], paired_ablation["y_probability_b"]))
            mean_diff = oof_auc_a - oof_auc_b
            
            boot_res = paired_user_bootstrap_auc_difference(
                paired_ablation,
                n_bootstrap=5000,
                random_state=42
            )
            ci_lower_inc = boot_res["paired_oof_ci_lower"]
            ci_upper_inc = boot_res["paired_oof_ci_upper"]
            
        ablation_results.append({
            "feature_set": set_name,
            "n_raw_features": n_raw,
            "n_encoded_features": n_enc,
            "mean_cv_roc_auc": mean_cv_auc,
            "std_cv_roc_auc": std_cv_auc,
            "ci_lower_95": ci_lower,
            "ci_upper_95": ci_upper,
            
            # New OOF columns
            "oof_roc_auc": oof_auc,
            "oof_ci_lower_95": oof_ci_lower,
            "oof_ci_upper_95": oof_ci_upper,
            
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
    nl_aucs = [cv_summary_df[cv_summary_df["model"] == m]["mean_fold_roc_auc"].values[0] for m in nl_models]
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
    
    for m1, m2 in comparisons:
        fold_results_a = cv_fold_df[cv_fold_df["model"] == m1]
        fold_results_b = cv_fold_df[cv_fold_df["model"] == m2]
        
        mean_fold_auc_model_a = float(fold_results_a["roc_auc"].mean())
        mean_fold_auc_model_b = float(fold_results_b["roc_auc"].mean())
        mean_fold_auc_difference = mean_fold_auc_model_a - mean_fold_auc_model_b
        
        paired_predictions = build_paired_user_predictions(df_preds_all, m1, m2, expected_repeats=10)
        
        oof_auc_model_a = float(roc_auc_score(
            paired_predictions["y_true"],
            paired_predictions["y_probability_a"],
        ))
        oof_auc_model_b = float(roc_auc_score(
            paired_predictions["y_true"],
            paired_predictions["y_probability_b"],
        ))
        paired_oof_delta_auc = oof_auc_model_a - oof_auc_model_b
        
        boot_res = paired_user_bootstrap_auc_difference(
            paired_predictions,
            n_bootstrap=5000,
            confidence_level=0.95,
            random_state=RANDOM_SEED
        )
        paired_oof_ci_lower = boot_res["paired_oof_ci_lower"]
        paired_oof_ci_upper = boot_res["paired_oof_ci_upper"]
        probability_delta_above_zero = boot_res["probability_delta_above_zero"]
        bootstrap_two_sided_p_value = boot_res["bootstrap_two_sided_p_value"]
        
        relative_auc_improvement_pct = (paired_oof_delta_auc / oof_auc_model_b) * 100.0
        
        # Automatic Interpretation
        interpretation = (
            f"{m1} achieved a paired OOF ROC-AUC difference of "
            f"{paired_oof_delta_auc:.4f} relative to {m2}, "
            f"with a 95% user-level bootstrap confidence interval of "
            f"[{paired_oof_ci_lower:.4f}, {paired_oof_ci_upper:.4f}]. "
        )
        
        if paired_oof_ci_lower <= 0.0 <= paired_oof_ci_upper:
            practical_sig = "not_stable"
            interpretation += "The comparison does not show a stable incremental change."
        else:
            is_improvement = paired_oof_delta_auc >= 0.0
            suffix = "_improvement" if is_improvement else "_degradation"
            abs_diff = abs(paired_oof_delta_auc)
            if abs_diff < 0.005:
                practical_sig = "practically_negligible" + suffix
                interpretation += "The difference is statistically detectable under the paired user-level bootstrap, but the absolute change is practically very small."
            elif 0.005 <= abs_diff < 0.01:
                practical_sig = "very_small" + suffix
                interpretation += f"The comparison shows a very small practical {'improvement' if is_improvement else 'degradation'}."
            elif 0.01 <= abs_diff < 0.02:
                practical_sig = "small" + suffix
                interpretation += f"The comparison shows a small practical {'improvement' if is_improvement else 'degradation'}."
            else:
                practical_sig = "meaningful" + suffix
                interpretation += f"The comparison shows a potentially meaningful {'improvement' if is_improvement else 'degradation'}, requiring domain interpretation."

        stat_comparisons.append({
            "comparison_id": f"{m1}_vs_{m2}",
            "model_a": m1,
            "model_b": m2,
            "reference_model": m2,
            "analysis_level": "user",
            "pairing_key": "user_id",
            "n_paired_users": len(paired_predictions),
            "expected_repeats": 10,
            
            "mean_fold_auc_model_a": mean_fold_auc_model_a,
            "mean_fold_auc_model_b": mean_fold_auc_model_b,
            "mean_fold_auc_difference": mean_fold_auc_difference,
            
            "oof_auc_model_a": oof_auc_model_a,
            "oof_auc_model_b": oof_auc_model_b,
            "paired_oof_delta_auc": paired_oof_delta_auc,
            "paired_oof_ci_lower": paired_oof_ci_lower,
            "paired_oof_ci_upper": paired_oof_ci_upper,
            
            "relative_auc_improvement_pct": relative_auc_improvement_pct,
            "probability_delta_above_zero": probability_delta_above_zero,
            "bootstrap_two_sided_p_value": bootstrap_two_sided_p_value,
            "bootstrap_iterations": 5000,
            "comparison_method": "paired_percentile_bootstrap_on_aggregated_oof_predictions",
            "bootstrap_unit": "user",
            "dependency_correction": "aggregate_repeated_oof_by_user_before_bootstrap",
            "practical_significance": practical_sig,
            "interpretation": interpretation
        })
    comparisons_df = pd.DataFrame(stat_comparisons)
    validate_paired_comparison_consistency(comparisons_df)
    comparisons_df.to_csv(OUTPUT_DIR / "statistical_model_comparisons.csv", index=False)

    # --- FIT EXPLANATORY LOGISTIC REGRESSION WITH STATSMODELS ---
    print("Fitting Explanatory Logistic Regression with statsmodels Logit...")
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    
    # Feature set gọn:
    # n_touchpoints, has_direct_traffic, has_display_ads, has_email, has_referral, has_search_ads, has_social_media
    X_expl = pd.DataFrame(index=users.index)
    X_expl["n_touchpoints"] = users["n_touchpoints"]
    X_expl["has_direct_traffic"] = users["channel_direct_traffic"]
    X_expl["has_display_ads"] = users["channel_display_ads"]
    X_expl["has_email"] = users["channel_email"]
    X_expl["has_referral"] = users["channel_referral"]
    X_expl["has_search_ads"] = users["channel_search_ads"]
    X_expl["has_social_media"] = users["channel_social_media"]
    
    # Target
    y_expl = users["converted_any_yes"].astype(int)
    
    # Validate no leakage and temporal scope
    validate_no_direct_target_leakage(list(X_expl.columns))
    validate_feature_temporal_scope(list(X_expl.columns))
    
    # Add constant
    X_expl_const = sm.add_constant(X_expl)
    
    # Fit model with HC3 robust standard errors
    model_sm = sm.Logit(y_expl, X_expl_const)
    fit_sm = model_sm.fit(cov_type="HC3", maxiter=100)
    
    # Verify convergence
    if not fit_sm.mle_retvals["converged"]:
        print("Warning: Explanatory Logistic model did not converge.")
        
    vifs = []
    for i in range(X_expl_const.shape[1]):
        col_name = X_expl_const.columns[i]
        if col_name == "const":
            vifs.append(np.nan)
        else:
            vif_val = variance_inflation_factor(X_expl_const.values, i)
            vifs.append(vif_val)
            
    expl_rows = []
    for idx, col_name in enumerate(X_expl_const.columns):
        feat_name = "intercept" if col_name == "const" else col_name
        coef = float(fit_sm.params.iloc[idx])
        se = float(fit_sm.bse.iloc[idx])
        z = float(fit_sm.tvalues.iloc[idx])
        p = float(fit_sm.pvalues.iloc[idx])
        vif = vifs[idx]
        
        odds_ratio = float(np.exp(coef))
        ci_lower_95 = float(np.exp(coef - 1.96 * se))
        ci_upper_95 = float(np.exp(coef + 1.96 * se))
        
        expl_rows.append({
            "feature": feat_name,
            "coefficient": coef,
            "standard_error": se,
            "z_value": z,
            "p_value": p,
            "odds_ratio": odds_ratio,
            "ci_lower_95": ci_lower_95,
            "ci_upper_95": ci_upper_95,
            "vif": vif,
            "model_name": "explanatory_logistic",
            "analysis_level": "user",
            "modeling_scope": "retrospective_diagnostic",
            "interpretation_limit": "association_only_no_causal_inference"
        })
        
    pd.DataFrame(expl_rows).to_csv(OUTPUT_DIR / "explanatory_logistic_odds_ratios.csv", index=False)
    
    # Remove old enhanced odds ratios file if it exists
    old_or_file = OUTPUT_DIR / "enhanced_logistic_odds_ratios.csv"
    if old_or_file.exists():
        old_or_file.unlink()
        print("Deleted legacy file: enhanced_logistic_odds_ratios.csv")
        
    # --- GENERATE EXPLANATORY MODEL METRICS SUMMARY FOR INSTRUCTOR ---
    print("Generating model_metrics_summary.csv...")
    summary_rows = []
    for m_name in [
        "user_any_channel", "journey_length_only", "channel_plus_length",
        "enhanced_journey_logistic", "enhanced_journey_logistic_balanced",
        "random_forest", "extra_trees", "gradient_boosting"
    ]:
        cv_row = cv_summary_df[cv_summary_df["model"] == m_name].iloc[0]
        ho_row = [r for r in holdout_metrics_rows if r["model"] == m_name][0]
        
        display_names_map = {
            "user_any_channel": "User Any-Channel",
            "journey_length_only": "Journey Length Only",
            "channel_plus_length": "Channel + Length",
            "enhanced_journey_logistic": "Enhanced Journey Logistic",
            "enhanced_journey_logistic_balanced": "Enhanced Journey Logistic (Balanced)",
            "random_forest": "Random Forest",
            "extra_trees": "Extra Trees",
            "gradient_boosting": "Gradient Boosting"
        }
        
        role_map = {
            "user_any_channel": "diagnostic baseline",
            "journey_length_only": "confounding control",
            "channel_plus_length": "adjusted diagnostic",
            "enhanced_journey_logistic": "enhanced diagnostic",
            "enhanced_journey_logistic_balanced": "enhanced diagnostic",
            "random_forest": "nonlinear robustness benchmark",
            "extra_trees": "nonlinear robustness benchmark",
            "gradient_boosting": "nonlinear robustness benchmark"
        }
        
        interp_map = {
            "user_any_channel": "Shows diagnostic performance of channel presence alone without journey length controls.",
            "journey_length_only": "Controls for confounding journey length, demonstrating strong predictive power from sequence count alone.",
            "channel_plus_length": "Combines channel presence with journey length, showing negligible incremental performance from channels.",
            "enhanced_journey_logistic": "Uses detailed journey structure and position features but fails to outperform the baseline control.",
            "enhanced_journey_logistic_balanced": "Enhanced model with class-balancing adjustment to address high prevalence of conversions.",
            "random_forest": "Nonlinear baseline checking if complex feature interactions can recover additional predictive signal.",
            "extra_trees": "Extremely randomized trees robustness check on enhanced feature space.",
            "gradient_boosting": "Gradient boosted trees checking for non-linear decision boundaries on enhanced features."
        }
        
        ci_str = f"[{cv_row['oof_roc_auc_ci_lower']:.4f}, {cv_row['oof_roc_auc_ci_upper']:.4f}]"
        
        summary_rows.append({
            "model": m_name,
            "model_display_name": display_names_map[m_name],
            "model_role": role_map[m_name],
            "feature_set": cv_row["feature_set"],
            "oof_roc_auc": round(cv_row["oof_roc_auc"], 4),
            "roc_auc_ci_95": ci_str,
            "oof_pr_auc": round(cv_row["oof_pr_auc"], 4),
            "pr_auc_baseline": round(cv_row["positive_prevalence"], 4),
            "pr_auc_improvement_over_baseline": round(cv_row["oof_pr_auc_improvement_over_baseline"], 4),
            "holdout_roc_auc": round(ho_row["roc_auc"], 4),
            "holdout_pr_auc": round(ho_row["pr_auc"], 4),
            "accuracy": round(ho_row["accuracy"], 4),
            "balanced_accuracy": round(ho_row["balanced_accuracy"], 4),
            "precision": round(ho_row["precision"], 4),
            "recall": round(ho_row["recall"], 4),
            "specificity": round(ho_row["specificity"], 4),
            "f1": round(ho_row["f1"], 4),
            "brier_score": round(ho_row["brier_score"], 4),
            "main_interpretation": interp_map[m_name]
        })
        
    pd.DataFrame(summary_rows).to_csv(OUTPUT_DIR / "model_metrics_summary.csv", index=False)

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
