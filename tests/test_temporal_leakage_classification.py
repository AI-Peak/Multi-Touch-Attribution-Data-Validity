import pytest
from model.logistic_regression.src.train_logistic_models import (
    FEATURE_TEMPORAL_METADATA,
    validate_no_direct_target_leakage,
    validate_feature_temporal_scope,
    initialize_feature_metadata
)

def test_temporal_metadata_initialization():
    cols = ["n_touchpoints", "converted_any_yes", "prop_direct_traffic", "first_touch_channel", "count_second_half_email"]
    initialize_feature_metadata(cols)
    
    # Check direct target leakage
    assert FEATURE_TEMPORAL_METADATA["converted_any_yes"]["leakage_category"] == "direct_target_leakage"
    assert FEATURE_TEMPORAL_METADATA["converted_any_yes"]["allowed_in_retrospective_model"] is False
    assert FEATURE_TEMPORAL_METADATA["converted_any_yes"]["allowed_in_prospective_model"] is False

    # Check post-outcome temporal features
    assert FEATURE_TEMPORAL_METADATA["n_touchpoints"]["leakage_category"] == "post_outcome_temporal_features"
    assert FEATURE_TEMPORAL_METADATA["n_touchpoints"]["allowed_in_retrospective_model"] is True
    assert FEATURE_TEMPORAL_METADATA["n_touchpoints"]["allowed_in_prospective_model"] is False
    
    # Check prospective safe
    assert FEATURE_TEMPORAL_METADATA["first_touch_channel"]["leakage_category"] == "prospective_safe_features"
    assert FEATURE_TEMPORAL_METADATA["first_touch_channel"]["allowed_in_retrospective_model"] is True
    assert FEATURE_TEMPORAL_METADATA["first_touch_channel"]["allowed_in_prospective_model"] is True

    # Check retrospective safe
    assert FEATURE_TEMPORAL_METADATA["prop_direct_traffic"]["leakage_category"] == "retrospective_safe_features"
    assert FEATURE_TEMPORAL_METADATA["prop_direct_traffic"]["allowed_in_retrospective_model"] is True
    assert FEATURE_TEMPORAL_METADATA["prop_direct_traffic"]["allowed_in_prospective_model"] is False

def test_leakage_validations():
    cols = ["n_touchpoints", "converted_any_yes", "prop_direct_traffic", "first_touch_channel", "count_second_half_email"]
    initialize_feature_metadata(cols)
    
    # Safe features should not raise error
    validate_no_direct_target_leakage(["n_touchpoints", "prop_direct_traffic"])
    validate_feature_temporal_scope(["n_touchpoints", "prop_direct_traffic"])
    
    # Direct target leakage must raise ValueError
    with pytest.raises(ValueError, match="Direct target leakage feature detected and blocked"):
        validate_no_direct_target_leakage(["converted_any_yes"])
        
    # Feature not in metadata must raise ValueError
    with pytest.raises(ValueError, match="has no temporal metadata"):
        validate_no_direct_target_leakage(["non_existent_feature"])
