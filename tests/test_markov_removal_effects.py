import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "model" / "markov_chain" / "outputs"

def test_markov_removal_effects_output():
    file_path = OUTPUT_DIR / "rq2_markov_removal_effects.csv"
    assert file_path.exists(), f"File does not exist: {file_path}"
    
    df = pd.read_csv(file_path)
    
    # Check schema
    expected_cols = {
        "channel", "baseline_conversion_probability", "probability_without_channel", 
        "absolute_removal_effect", "relative_removal_effect", 
        "positive_absolute_effect", "positive_normalized_share_pct"
    }
    assert expected_cols.issubset(df.columns), f"Columns missing in {file_path}. Found: {df.columns}"
    
    # Check calculations
    for idx, row in df.iterrows():
        base = row["baseline_conversion_probability"]
        without = row["probability_without_channel"]
        abs_eff = row["absolute_removal_effect"]
        rel_eff = row["relative_removal_effect"]
        pos_abs = row["positive_absolute_effect"]
        
        # Absolute effect is base - without
        assert abs(abs_eff - (base - without)) < 1e-5
        
        # Relative effect is absolute / base
        if base > 0:
            assert abs(rel_eff - (abs_eff / base)) < 1e-5
        else:
            assert rel_eff == 0.0
            
        # Positive absolute effect is max(absolute_removal_effect, 0)
        assert abs(pos_abs - max(abs_eff, 0.0)) < 1e-5
        
    # Check normalized sum of positive share is 100% (or 0% if all negative)
    pos_sum = df["positive_absolute_effect"].sum()
    share_sum = df["positive_normalized_share_pct"].sum()
    if pos_sum > 0:
        assert abs(share_sum - 100.0) < 1e-5
    else:
        assert share_sum == 0.0
        
    # Verify no double-prefixed files exist
    double_prefixes = [
        "rq2_markov_markov_attribution_share.csv",
        "rq2_markov_markov_removal_effects.csv",
        "rq2_markov_markov_transition_counts.csv",
        "rq2_markov_markov_transition_matrix.csv"
    ]
    for filename in double_prefixes:
        p = OUTPUT_DIR / filename
        assert not p.exists(), f"Stale double-prefixed file {p.name} still exists!"
