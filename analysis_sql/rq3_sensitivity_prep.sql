-- RQ3 SQL baseline: scenario metadata and user-label base for sensitivity analysis.
-- Python analysis performs downsampling and rank-stability tests from these SQL outputs.

DROP TABLE IF EXISTS sensitivity_base;
CREATE TABLE sensitivity_base AS
SELECT 'Current any-Yes label' AS scenario, NULL AS target_rate_pct, 'converted_any_yes' AS source_label, 'Use SQL any-Yes user label directly' AS rule
UNION ALL SELECT 'Stricter final-touch Yes label', NULL, 'last_touch_yes', 'Use SQL final-touch Yes user label directly'
UNION ALL SELECT 'Downsampled current positives to 1%', 1.0, 'converted_any_yes', 'Python samples SQL any-Yes positives to target rate'
UNION ALL SELECT 'Downsampled current positives to 3%', 3.0, 'converted_any_yes', 'Python samples SQL any-Yes positives to target rate'
UNION ALL SELECT 'Downsampled current positives to 5%', 5.0, 'converted_any_yes', 'Python samples SQL any-Yes positives to target rate'
UNION ALL SELECT 'Downsampled current positives to 10%', 10.0, 'converted_any_yes', 'Python samples SQL any-Yes positives to target rate';

DROP TABLE IF EXISTS scenario_user_label_base;
CREATE TABLE scenario_user_label_base AS
SELECT
    user_id,
    converted_any_yes,
    last_touch_yes,
    n_touchpoints,
    n_conversion_events,
    any_yes_before_last,
    multiple_yes_events
FROM journey_features;

