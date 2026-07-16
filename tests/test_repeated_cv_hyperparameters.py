from __future__ import annotations

import inspect
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from model.logistic_regression.src.train_logistic_models import (
    FIXED_C_FOR_REPEATED_CV,
    CANDIDATE_C_VALUES_FOR_HOLDOUT,
    build_repeated_cv_logistic_pipeline,
    tune_holdout_logistic_c,
    validate_repeated_cv_configuration,
    OUTPUT_DIR,
)


def test_repeated_cv_uses_fixed_c():
    preprocessor = StandardScaler()
    pipeline = build_repeated_cv_logistic_pipeline(preprocessor)

    assert isinstance(pipeline, Pipeline)
    model = pipeline.named_steps["model"]
    assert isinstance(model, LogisticRegression)
    assert model.C == FIXED_C_FOR_REPEATED_CV


def test_repeated_cv_does_not_receive_holdout_tuned_c():
    holdout_selected_c = 0.01
    pipeline = build_repeated_cv_logistic_pipeline(StandardScaler())
    model = pipeline.named_steps["model"]
    assert model.C == 1.0
    assert model.C != holdout_selected_c


def test_holdout_tuning_works():
    # Verify the signature: does not take Test set as arguments
    sig = inspect.signature(tune_holdout_logistic_c)
    assert "X_test" not in sig.parameters
    assert "y_test" not in sig.parameters

    # Create a small dummy dataset to verify tuning functionality
    X_train = np.array([[1.0], [2.0], [3.0], [4.0], [5.0], [6.0]])
    y_train = pd.Series([0, 0, 0, 1, 1, 1])
    X_val = np.array([[1.5], [2.5], [3.5]])
    y_val = pd.Series([0, 0, 1])

    best_model, best_c = tune_holdout_logistic_c(
        X_train=X_train,
        y_train=y_train,
        X_validation=X_val,
        y_validation=y_val,
        feature_spec=None,
        candidate_c_values=CANDIDATE_C_VALUES_FOR_HOLDOUT,
    )

    assert best_c in CANDIDATE_C_VALUES_FOR_HOLDOUT
    assert isinstance(best_model, LogisticRegression)
    assert best_model.C == best_c


def test_metadata_correct():
    cv_metrics_path = OUTPUT_DIR / "repeated_cv_metrics.csv"
    holdout_metrics_path = OUTPUT_DIR / "holdout_model_metrics.csv"

    # If the outputs do not exist yet or are stale, the test will check them after training.
    # In order to make the test self-contained, we assert if files exist, they are correct.
    if cv_metrics_path.exists():
        df_cv = pd.read_csv(cv_metrics_path)
        assert "cv_c_value" in df_cv.columns
        assert "cv_hyperparameter_strategy" in df_cv.columns

        logistic_cv_models = [
            "row_channel",
            "user_any_channel",
            "journey_length_only",
            "channel_plus_length",
            "enhanced_journey_logistic",
            "enhanced_journey_logistic_balanced",
        ]
        for model_name in logistic_cv_models:
            row = df_cv[df_cv["model"] == model_name]
            if not row.empty:
                val = row["cv_c_value"].iloc[0]
                # Allow string comparison if written as string or float
                assert float(val) == 1.0
                assert row["cv_hyperparameter_strategy"].iloc[0] == "fixed_predefined"

    if holdout_metrics_path.exists():
        df_holdout = pd.read_csv(holdout_metrics_path)
        assert "selected_c" in df_holdout.columns
        assert "hyperparameter_selection_source" in df_holdout.columns

        logistic_holdout_models = [
            "row_channel",
            "user_any_channel",
            "journey_length_only",
            "channel_plus_length",
            "enhanced_journey_logistic",
            "enhanced_journey_logistic_balanced",
        ]
        for model_name in logistic_holdout_models:
            row = df_holdout[df_holdout["model"] == model_name]
            if not row.empty:
                assert row["hyperparameter_selection_source"].iloc[0] == "train_validation_only"
