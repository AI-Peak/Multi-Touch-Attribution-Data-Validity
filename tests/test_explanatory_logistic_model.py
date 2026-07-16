import numpy as np
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "model" / "logistic_regression" / "outputs"

def test_explanatory_logistic_output():
    or_file = OUTPUT_DIR / "explanatory_logistic_odds_ratios.csv"
    assert or_file.exists(), f"Explanatory odds ratios file does not exist: {or_file}"
    
    df = pd.read_csv(or_file)
    
    # Check schema
    expected_cols = {
        "feature", "coefficient", "standard_error", "z_value", "p_value", 
        "odds_ratio", "ci_lower_95", "ci_upper_95", "vif", 
        "model_name", "analysis_level", "modeling_scope", "interpretation_limit"
    }
    assert expected_cols.issubset(df.columns), f"Columns missing in {or_file}. Found: {df.columns}"
    
    # Check features are the expected ones
    features = set(df["feature"])
    expected_features = {
        "intercept", "n_touchpoints", "has_direct_traffic", "has_display_ads", 
        "has_email", "has_referral", "has_search_ads", "has_social_media"
    }
    assert expected_features.issubset(features), f"Features mismatch: {features}"
    
    # Check odds ratio calculations and CI bounds
    for idx, row in df.iterrows():
        coef = row["coefficient"]
        stderr = row["standard_error"]
        odds_ratio = row["odds_ratio"]
        ci_lower = row["ci_lower_95"]
        ci_upper = row["ci_upper_95"]
        
        # Verify odds ratio is exp(coef)
        assert abs(odds_ratio - np.exp(coef)) < 1e-5, f"Odds ratio not matching exp(coef) for {row['feature']}"
        
        # Verify lower <= odds_ratio <= upper
        assert ci_lower <= odds_ratio <= ci_upper, f"CI bounds invalid for {row['feature']}: {ci_lower} <= {odds_ratio} <= {ci_upper}"
        
        # intercept VIF is nan, others should be numeric and positive
        if row["feature"] != "intercept":
            assert row["vif"] > 0, f"VIF should be positive for {row['feature']}, found {row['vif']}"
            
        assert row["modeling_scope"] == "retrospective_diagnostic"
        assert row["interpretation_limit"] == "association_only_no_causal_inference"
