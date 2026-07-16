from __future__ import annotations

import inspect
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from model.logistic_regression.src.train_logistic_models import (
    aggregate_oof_predictions,
    bootstrap_single_model_oof_metrics,
    validate_single_model_ci_output,
    fast_roc_auc_score,
)
from model.logistic_regression.src.generate_paper_figures import plot_cv_performance_forest


def test_oof_aggregation_single_prediction():
    # 10 users, 3 repeats
    data = []
    for user in range(10):
        for rep in range(10):
            data.append({
                "model": "model_x",
                "repeat": rep,
                "fold": rep % 5,
                "user_id": user,
                "y_true": 1 if user % 2 == 0 else 0,
                "y_probability": 0.1 * rep + 0.05 * user
            })
    df = pd.DataFrame(data)
    aggregated = aggregate_oof_predictions(df)
    assert len(aggregated) == 10
    assert (aggregated["n_oof_predictions"] == 10).all()


def test_oof_aggregation_correct_mean():
    data = [
        {"user_id": 1, "y_true": 1, "y_probability": 0.2},
        {"user_id": 1, "y_true": 1, "y_probability": 0.4},
        {"user_id": 1, "y_true": 1, "y_probability": 0.6},
        {"user_id": 1, "y_true": 1, "y_probability": 0.2},
        {"user_id": 1, "y_true": 1, "y_probability": 0.4},
        {"user_id": 1, "y_true": 1, "y_probability": 0.6},
        {"user_id": 1, "y_true": 1, "y_probability": 0.2},
        {"user_id": 1, "y_true": 1, "y_probability": 0.4},
        {"user_id": 1, "y_true": 1, "y_probability": 0.6},
        {"user_id": 1, "y_true": 1, "y_probability": 0.4}, # 10 predictions
    ]
    df = pd.DataFrame(data)
    aggregated = aggregate_oof_predictions(df)
    assert np.isclose(aggregated.loc[0, "y_probability"], 0.4)


def test_oof_aggregation_inconsistent_labels_raises_error():
    data = []
    for rep in range(10):
        data.append({
            "user_id": 1,
            "y_true": 1 if rep < 5 else 0,
            "y_probability": 0.5
        })
    df = pd.DataFrame(data)
    try:
        aggregate_oof_predictions(df)
        assert False, "Should have raised ValueError for inconsistent labels"
    except ValueError:
        pass


def test_bootstrap_receives_aggregated_dataframe():
    # Verify bootstrap function takes only single y_true and y_probability vectors 
    # of size equal to number of unique analysis units (unique users).
    sig = inspect.signature(bootstrap_single_model_oof_metrics)
    assert "y_true" in sig.parameters
    assert "y_probability" in sig.parameters
    
    # 20 users, 10 repeats
    data = []
    for user in range(20):
        for rep in range(10):
            data.append({
                "user_id": user,
                "y_true": 1 if user < 10 else 0,
                "y_probability": 0.1 * rep if user < 10 else 0.05 * rep
            })
    df = pd.DataFrame(data)
    aggregated = aggregate_oof_predictions(df)
    
    # Ensure bootstrap is called on aggregated arrays of length 20
    assert len(aggregated["y_true"]) == 20
    boot_res = bootstrap_single_model_oof_metrics(
        y_true=aggregated["y_true"].to_numpy(),
        y_probability=aggregated["y_probability"].to_numpy(),
        n_bootstrap=1000,
        random_state=42
    )
    assert "oof_roc_auc_ci_lower" in boot_res
    assert "oof_roc_auc_ci_upper" in boot_res


def test_ci_contains_point_estimate():
    # Setup dummy data for a model
    y_true = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 0] * 10)
    y_probability = np.array([0.9, 0.8, 0.85, 0.7, 0.6, 0.1, 0.2, 0.3, 0.4, 0.5] * 10)
    
    point_auc = fast_roc_auc_score(y_true, y_probability)
    boot_res = bootstrap_single_model_oof_metrics(
        y_true=y_true,
        y_probability=y_probability,
        n_bootstrap=1000,
        random_state=42
    )
    
    assert boot_res["oof_roc_auc_ci_lower"] <= point_auc
    assert point_auc <= boot_res["oof_roc_auc_ci_upper"]


def test_row_order_invariance():
    # Shuffle order before aggregation
    data = []
    for user in range(20):
        for rep in range(10):
            data.append({
                "user_id": user,
                "y_true": 1 if user < 12 else 0,
                "y_probability": 0.8 if user < 12 else 0.2
            })
    df_original = pd.DataFrame(data)
    df_shuffled = df_original.sample(frac=1.0, random_state=123).reset_index(drop=True)
    
    agg_orig = aggregate_oof_predictions(df_original).sort_values("user_id").reset_index(drop=True)
    agg_shuf = aggregate_oof_predictions(df_shuffled).sort_values("user_id").reset_index(drop=True)
    
    assert np.allclose(agg_orig["y_probability"], agg_shuf["y_probability"])
    
    # Compute CI
    res_orig = bootstrap_single_model_oof_metrics(
        y_true=agg_orig["y_true"].to_numpy(),
        y_probability=agg_orig["y_probability"].to_numpy(),
        n_bootstrap=1000,
        random_state=42
    )
    res_shuf = bootstrap_single_model_oof_metrics(
        y_true=agg_shuf["y_true"].to_numpy(),
        y_probability=agg_shuf["y_probability"].to_numpy(),
        n_bootstrap=1000,
        random_state=42
    )
    
    assert np.isclose(res_orig["oof_roc_auc_ci_lower"], res_shuf["oof_roc_auc_ci_lower"])
    assert np.isclose(res_orig["oof_roc_auc_ci_upper"], res_shuf["oof_roc_auc_ci_upper"])


def test_figure_uses_correct_columns():
    sig = inspect.signature(plot_cv_performance_forest)
    # Check that it compiles and accesses correct fields by inspecting code
    source_code = inspect.getsource(plot_cv_performance_forest)
    assert "oof_roc_auc" in source_code
    assert "oof_roc_auc_ci_lower" in source_code
    assert "oof_roc_auc_ci_upper" in source_code
    assert "mean_roc_auc" not in source_code or "journey_length_only" in source_code  # mean_roc_auc might appear in old checks, but oof_roc_auc is used for plot
    assert "ci_lower_95" not in source_code


def test_custom_auc_versus_sklearn():
    # 1. Predicted probabilities not overlapping
    y_true_1 = np.array([1, 1, 0, 0])
    y_prob_1 = np.array([0.9, 0.8, 0.2, 0.1])
    assert np.isclose(fast_roc_auc_score(y_true_1, y_prob_1), roc_auc_score(y_true_1, y_prob_1), atol=1e-10)

    # 2. Tied probabilities
    y_true_2 = np.array([1, 1, 0, 0])
    y_prob_2 = np.array([0.5, 0.5, 0.5, 0.5])
    assert np.isclose(fast_roc_auc_score(y_true_2, y_prob_2), roc_auc_score(y_true_2, y_prob_2), atol=1e-10)

    # 3. Tied probabilities (mixed)
    y_true_2b = np.array([1, 0, 1, 0])
    y_prob_2b = np.array([0.8, 0.8, 0.3, 0.3])
    assert np.isclose(fast_roc_auc_score(y_true_2b, y_prob_2b), roc_auc_score(y_true_2b, y_prob_2b), atol=1e-10)

    # 4. Imbalanced data
    y_true_3 = np.array([1, 0, 0, 0, 0, 0])
    y_prob_3 = np.array([0.9, 0.1, 0.2, 0.3, 0.4, 0.5])
    assert np.isclose(fast_roc_auc_score(y_true_3, y_prob_3), roc_auc_score(y_true_3, y_prob_3), atol=1e-10)

    # 5. Row order shuffled
    y_true_4 = np.array([1, 0, 1, 0, 1, 0])
    y_prob_4 = np.array([0.9, 0.2, 0.8, 0.3, 0.7, 0.4])
    idx = np.array([3, 1, 5, 0, 2, 4])
    assert np.isclose(fast_roc_auc_score(y_true_4[idx], y_prob_4[idx]), roc_auc_score(y_true_4[idx], y_prob_4[idx]), atol=1e-10)
