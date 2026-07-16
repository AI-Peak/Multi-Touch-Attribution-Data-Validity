import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "model" / "logistic_regression" / "outputs"

def test_feature_ablation_results():
    ablation_file = OUTPUT_DIR / "feature_ablation_results.csv"
    assert ablation_file.exists(), f"Ablation file does not exist: {ablation_file}"
    
    df = pd.read_csv(ablation_file)
    
    # Check expected sets exist
    expected_sets = {
        "channel_presence_only", "journey_length_only", "channel_presence_plus_length",
        "channel_counts_only", "channel_proportions_only", "channel_counts_plus_proportions",
        "journey_structure_only", "journey_position_only", "sequence_summary_only",
        "full_enhanced_features"
    }
    assert expected_sets.issubset(set(df["feature_set"])), f"Ablation sets mismatch: {set(df['feature_set'])}"
    
    # Check proportion set has exactly 6 features
    prop_row = df[df["feature_set"] == "channel_proportions_only"].iloc[0]
    assert int(prop_row["n_raw_features"]) == 6, f"Proportions set should have exactly 6 features, found {prop_row['n_raw_features']}"
    
    # Check presence set has exactly 6 features
    pres_row = df[df["feature_set"] == "channel_presence_only"].iloc[0]
    assert int(pres_row["n_raw_features"]) == 6, f"Presence set should have exactly 6 features, found {pres_row['n_raw_features']}"
    
    # Check that OOF metrics and bootstrap CI columns exist
    assert "oof_roc_auc" in df.columns
    assert "oof_ci_lower_95" in df.columns
    assert "oof_ci_upper_95" in df.columns
    
    # Validate lower <= oof_auc <= upper
    for idx, row in df.iterrows():
        auc = row["oof_roc_auc"]
        low = row["oof_ci_lower_95"]
        high = row["oof_ci_upper_95"]
        assert 0.0 <= low <= auc <= high <= 1.0, f"OOF CI bounds invalid for {row['feature_set']}: {low} <= {auc} <= {high}"
