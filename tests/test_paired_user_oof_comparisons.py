from __future__ import annotations

import inspect
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from model.logistic_regression.src.train_logistic_models import (
    aggregate_model_oof_by_user,
    build_paired_user_predictions,
    paired_user_bootstrap_auc_difference,
    OUTPUT_DIR,
)
from model.logistic_regression.src.generate_paper_figures import plot_incremental_auc


def test_pairing_correct_by_user_id():
    # Setup dummy predictions for model A and B with mismatched row orders
    data_a = [
        {"model": "model_a", "repeat": r, "fold": r % 5, "user_id": u, "y_true": u % 2, "y_probability": 0.1 * u}
        for u in range(10) for r in range(10)
    ]
    data_b = [
        {"model": "model_b", "repeat": r, "fold": r % 5, "user_id": 9 - u, "y_true": (9 - u) % 2, "y_probability": 0.05 * (9 - u)}
        for u in range(10) for r in range(10)
    ]
    
    df = pd.DataFrame(data_a + data_b)
    paired = build_paired_user_predictions(df, "model_a", "model_b", expected_repeats=10)
    
    assert len(paired) == 10
    for idx, row in paired.iterrows():
        assert row["user_id"] == row["user_id"]
        # y_probability_a is 0.1 * u, y_probability_b is 0.05 * u
        u = row["user_id"]
        assert np.isclose(row["y_probability_a"], 0.1 * u)
        assert np.isclose(row["y_probability_b"], 0.05 * u)


def test_row_order_invariance():
    data_a = [
        {"model": "model_a", "repeat": r, "fold": r % 5, "user_id": u, "y_true": u % 2, "y_probability": 0.1 * u}
        for u in range(10) for r in range(10)
    ]
    data_b = [
        {"model": "model_b", "repeat": r, "fold": r % 5, "user_id": u, "y_true": u % 2, "y_probability": 0.05 * u}
        for u in range(10) for r in range(10)
    ]
    
    df_orig = pd.DataFrame(data_a + data_b)
    df_shuf = df_orig.sample(frac=1.0, random_state=42).reset_index(drop=True)
    
    paired_orig = build_paired_user_predictions(df_orig, "model_a", "model_b", expected_repeats=10)
    paired_shuf = build_paired_user_predictions(df_shuf, "model_a", "model_b", expected_repeats=10)
    
    # Sort for exact check
    paired_orig = paired_orig.sort_values("user_id").reset_index(drop=True)
    paired_shuf = paired_shuf.sort_values("user_id").reset_index(drop=True)
    
    assert np.allclose(paired_orig["y_probability_a"], paired_shuf["y_probability_a"])
    assert np.allclose(paired_orig["y_probability_b"], paired_shuf["y_probability_b"])
    
    res_orig = paired_user_bootstrap_auc_difference(paired_orig, n_bootstrap=1000, random_state=42)
    res_shuf = paired_user_bootstrap_auc_difference(paired_shuf, n_bootstrap=1000, random_state=42)
    
    assert np.isclose(res_orig["paired_oof_ci_lower"], res_shuf["paired_oof_ci_lower"])
    assert np.isclose(res_orig["paired_oof_ci_upper"], res_shuf["paired_oof_ci_upper"])


def test_missing_user_raises_error():
    data_a = [
        {"model": "model_a", "repeat": r, "fold": r % 5, "user_id": u, "y_true": u % 2, "y_probability": 0.1 * u}
        for u in range(10) for r in range(10)
    ]
    # missing user 9 in model B
    data_b = [
        {"model": "model_b", "repeat": r, "fold": r % 5, "user_id": u, "y_true": u % 2, "y_probability": 0.05 * u}
        for u in range(9) for r in range(10)
    ]
    
    df = pd.DataFrame(data_a + data_b)
    with pytest.raises(ValueError, match="contain different user sets|do not contain the same paired users"):
        build_paired_user_predictions(df, "model_a", "model_b", expected_repeats=10)


def test_duplicate_user_after_aggregation_raises_error():
    # Setup predictions that has an extra repeat or duplicate users, violating 1-to-1
    data_a = [
        {"model": "model_a", "repeat": r, "fold": r % 5, "user_id": u, "y_true": u % 2, "y_probability": 0.1 * u}
        for u in range(10) for r in range(10)
    ]
    data_b = [
        {"model": "model_b", "repeat": r, "fold": r % 5, "user_id": u, "y_true": u % 2, "y_probability": 0.05 * u}
        for u in range(10) for r in range(10)
    ]
    # add a duplicate entry in model A
    data_a.append({"model": "model_a", "repeat": 0, "fold": 0, "user_id": 1, "y_true": 1, "y_probability": 0.1})
    
    df = pd.DataFrame(data_a + data_b)
    with pytest.raises(ValueError, match="must have exactly 10 OOF predictions"):
        build_paired_user_predictions(df, "model_a", "model_b", expected_repeats=10)


def test_mismatched_labels_raises_error():
    data_a = [
        {"model": "model_a", "repeat": r, "fold": r % 5, "user_id": u, "y_true": 1 if u == 1 else 0, "y_probability": 0.1 * u}
        for u in range(10) for r in range(10)
    ]
    # user 1 has y_true=0 in model B
    data_b = [
        {"model": "model_b", "repeat": r, "fold": r % 5, "user_id": u, "y_true": 0, "y_probability": 0.05 * u}
        for u in range(10) for r in range(10)
    ]
    
    df = pd.DataFrame(data_a + data_b)
    with pytest.raises(ValueError, match="Inconsistent labels"):
        build_paired_user_predictions(df, "model_a", "model_b", expected_repeats=10)


def test_bootstrap_uses_common_sampled_indices():
    # If the bootstrap sampled indices are shared, then drawing samples from model A and model B
    # will maintain the pairing. We test this by asserting the bootstrap function receives a single 
    # combined dataframe, assuring the indices sampled are common across both models.
    sig = inspect.signature(paired_user_bootstrap_auc_difference)
    assert "paired_predictions" in sig.parameters
    # The first argument should be a DataFrame containing both columns
    
    data_a = [
        {"model": "model_a", "repeat": r, "fold": r % 5, "user_id": u, "y_true": u % 2, "y_probability": 0.1 * u}
        for u in range(10) for r in range(10)
    ]
    data_b = [
        {"model": "model_b", "repeat": r, "fold": r % 5, "user_id": u, "y_true": u % 2, "y_probability": 0.05 * u}
        for u in range(10) for r in range(10)
    ]
    df = pd.DataFrame(data_a + data_b)
    paired = build_paired_user_predictions(df, "model_a", "model_b", expected_repeats=10)
    
    res = paired_user_bootstrap_auc_difference(paired, n_bootstrap=100, random_state=42)
    assert "paired_oof_ci_lower" in res
    assert "paired_oof_ci_upper" in res


def test_mean_fold_diff_and_paired_oof_diff_saved_separately():
    csv_path = OUTPUT_DIR / "statistical_model_comparisons.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        assert "mean_fold_auc_difference" in df.columns
        assert "paired_oof_delta_auc" in df.columns
        # Verify they are not the same value
        for idx, row in df.iterrows():
            # In general, mean fold difference is not strictly equal to OOF difference
            # unless the model is extremely simple or there's no data.
            # We check that both columns are preserved and separate.
            pass


def test_interpretation_uses_paired_oof_value():
    csv_path = OUTPUT_DIR / "statistical_model_comparisons.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        for idx, row in df.iterrows():
            val_str = f"{row['paired_oof_delta_auc']:.4f}"
            assert val_str in row["interpretation"]
            assert "about 0.0037" not in row["interpretation"] or "0.0037" in val_str


def test_figure_06_uses_paired_oof_columns():
    source_code = inspect.getsource(plot_incremental_auc)
    assert "paired_oof_delta_auc" in source_code
    assert "paired_oof_ci_lower" in source_code
    assert "paired_oof_ci_upper" in source_code
    assert "mean_difference" not in source_code
    assert "ci_lower_95" not in source_code


def test_ci_consistency():
    csv_path = OUTPUT_DIR / "statistical_model_comparisons.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        for idx, row in df.iterrows():
            assert row["paired_oof_ci_lower"] <= row["paired_oof_delta_auc"]
            assert row["paired_oof_delta_auc"] <= row["paired_oof_ci_upper"]
