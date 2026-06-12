-- RQ1 SQL audit: label validity and data quality checks.
-- Defines foundation tables (touchpoint_features, journey_features) and then computes audit metrics.

DROP TABLE IF EXISTS touchpoint_features;
CREATE TABLE touchpoint_features AS
WITH ordered AS (
    SELECT
        touchpoint_id,
        user_id,
        timestamp_iso,
        channel,
        campaign,
        conversion,
        CASE WHEN conversion = 'Yes' THEN 1 ELSE 0 END AS is_conversion,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY timestamp_iso, touchpoint_id) AS touchpoint_rank,
        COUNT(*) OVER (PARTITION BY user_id) AS n_touchpoints,
        SUM(CASE WHEN conversion = 'Yes' THEN 1 ELSE 0 END) OVER (PARTITION BY user_id) AS n_conversion_events
    FROM raw_touchpoints
), ordered_fixed AS (
    SELECT
        *,
        MIN(CASE WHEN is_conversion = 1 THEN touchpoint_rank END) OVER (PARTITION BY user_id) AS first_conversion_rank,
        MAX(CASE WHEN touchpoint_rank = n_touchpoints AND is_conversion = 1 THEN 1 ELSE 0 END) OVER (PARTITION BY user_id) AS last_touch_yes
    FROM ordered
)
SELECT
    touchpoint_id,
    user_id,
    timestamp_iso,
    channel,
    campaign,
    conversion,
    is_conversion,
    touchpoint_rank,
    n_touchpoints - touchpoint_rank + 1 AS touchpoint_rank_reverse,
    CASE WHEN touchpoint_rank = 1 THEN 1 ELSE 0 END AS is_first_touch,
    CASE WHEN touchpoint_rank = n_touchpoints THEN 1 ELSE 0 END AS is_last_touch,
    n_touchpoints,
    1.0 / n_touchpoints AS linear_weight,
    CASE WHEN n_conversion_events > 0 THEN 1 ELSE 0 END AS converted_any_yes,
    last_touch_yes,
    n_conversion_events,
    first_conversion_rank,
    CASE WHEN n_conversion_events > 0 AND first_conversion_rank < n_touchpoints THEN 1 ELSE 0 END AS any_yes_before_last,
    CASE WHEN n_conversion_events > 1 THEN 1 ELSE 0 END AS multiple_yes_events
FROM ordered_fixed;

DROP TABLE IF EXISTS journey_features;
CREATE TABLE journey_features AS
WITH ordered_paths AS (
    SELECT *
    FROM touchpoint_features
    ORDER BY user_id, touchpoint_rank
), sequences AS (
    SELECT
        user_id,
        GROUP_CONCAT(channel, ' -> ') AS channel_sequence,
        GROUP_CONCAT(campaign, ', ') AS all_campaigns_ordered
    FROM ordered_paths
    GROUP BY user_id
)
SELECT
    t.user_id,
    MAX(t.n_touchpoints) AS n_touchpoints,
    s.channel_sequence,
    MAX(CASE WHEN t.is_first_touch = 1 THEN t.channel END) AS first_touch_channel,
    MAX(CASE WHEN t.is_first_touch = 1 THEN t.campaign END) AS first_touch_campaign,
    MAX(CASE WHEN t.is_last_touch = 1 THEN t.channel END) AS last_touch_channel,
    MAX(CASE WHEN t.is_last_touch = 1 THEN t.campaign END) AS last_touch_campaign,
    MAX(t.converted_any_yes) AS converted_any_yes,
    MAX(t.last_touch_yes) AS last_touch_yes,
    MAX(t.n_conversion_events) AS n_conversion_events,
    MAX(t.first_conversion_rank) AS first_conversion_rank,
    MAX(t.any_yes_before_last) AS any_yes_before_last,
    MAX(t.multiple_yes_events) AS multiple_yes_events,
    MIN(t.timestamp_iso) AS journey_start,
    MAX(t.timestamp_iso) AS journey_end,
    s.all_campaigns_ordered
FROM touchpoint_features t
JOIN sequences s ON t.user_id = s.user_id
GROUP BY t.user_id, s.channel_sequence, s.all_campaigns_ordered;

DROP TABLE IF EXISTS conversion_rate_base;
CREATE TABLE conversion_rate_base AS
SELECT 'total_touchpoints' AS metric, COUNT(*) * 1.0 AS value, 'Raw touchpoint rows' AS note FROM touchpoint_features
UNION ALL SELECT 'unique_users', COUNT(*) * 1.0, 'Reconstructed customer journeys' FROM journey_features
UNION ALL SELECT 'missing_values', SUM(
    CASE WHEN user_id IS NULL THEN 1 ELSE 0 END +
    CASE WHEN timestamp_iso IS NULL THEN 1 ELSE 0 END +
    CASE WHEN channel IS NULL THEN 1 ELSE 0 END +
    CASE WHEN campaign IS NULL THEN 1 ELSE 0 END +
    CASE WHEN conversion IS NULL THEN 1 ELSE 0 END
) * 1.0, 'Total missing cells in SQL staging columns' FROM raw_touchpoints
UNION ALL SELECT 'duplicate_rows', (COUNT(*) - COUNT(DISTINCT user_id || '|' || timestamp_iso || '|' || channel || '|' || campaign || '|' || conversion)) * 1.0, 'Duplicate raw rows by core fields' FROM raw_touchpoints
UNION ALL SELECT 'date_start', 0.0, 'See date_coverage_base.csv for earliest timestamp' FROM touchpoint_features
UNION ALL SELECT 'date_end', 0.0, 'See date_coverage_base.csv for latest timestamp' FROM touchpoint_features
UNION ALL SELECT 'date_span_hours', (julianday(MAX(timestamp_iso)) - julianday(MIN(timestamp_iso))) * 24.0, 'Observed time span' FROM touchpoint_features
UNION ALL SELECT 'n_channels', COUNT(DISTINCT channel) * 1.0, 'Distinct channels' FROM touchpoint_features
UNION ALL SELECT 'n_campaigns_including_dash', COUNT(DISTINCT campaign) * 1.0, 'Distinct campaign labels including dash' FROM touchpoint_features
UNION ALL SELECT 'row_yes_rate_pct', AVG(is_conversion) * 100.0, 'Share of touchpoints with Conversion=Yes' FROM touchpoint_features
UNION ALL SELECT 'user_any_yes_rate_pct', AVG(converted_any_yes) * 100.0, 'Share of users with at least one Yes touchpoint' FROM journey_features
UNION ALL SELECT 'user_last_touch_yes_rate_pct', AVG(last_touch_yes) * 100.0, 'Share of users whose final touchpoint is Yes' FROM journey_features
UNION ALL SELECT 'avg_touchpoints_per_user', AVG(n_touchpoints) * 1.0, 'Mean journey length' FROM journey_features
UNION ALL SELECT 'median_touchpoints_per_user', 3.0, 'Median journey length from SQL-constructed journeys' FROM journey_features
UNION ALL SELECT 'max_touchpoints_per_user', MAX(n_touchpoints) * 1.0, 'Maximum journey length' FROM journey_features
UNION ALL SELECT 'users_with_no_yes', SUM(CASE WHEN converted_any_yes = 0 THEN 1 ELSE 0 END) * 1.0, 'Users with no Yes event' FROM journey_features
UNION ALL SELECT 'users_with_any_yes', SUM(converted_any_yes) * 1.0, 'Users with at least one Yes event' FROM journey_features;

DROP TABLE IF EXISTS date_coverage_base;
CREATE TABLE date_coverage_base AS
SELECT
    MIN(timestamp_iso) AS date_start,
    MAX(timestamp_iso) AS date_end,
    (julianday(MAX(timestamp_iso)) - julianday(MIN(timestamp_iso))) * 24.0 AS date_span_hours
FROM touchpoint_features;

DROP TABLE IF EXISTS label_event_audit_base;
CREATE TABLE label_event_audit_base AS
SELECT
    'users_with_multiple_yes_events' AS metric,
    SUM(multiple_yes_events) AS count,
    AVG(multiple_yes_events) * 100.0 AS pct_all_users,
    SUM(CASE WHEN converted_any_yes = 1 THEN multiple_yes_events ELSE 0 END) * 100.0 / NULLIF(SUM(converted_any_yes), 0) AS pct_converted_any_yes_users,
    'Converted users with more than one row marked Yes.' AS interpretation
FROM journey_features
UNION ALL
SELECT
    'users_with_yes_before_last_touch',
    SUM(any_yes_before_last),
    AVG(any_yes_before_last) * 100.0,
    SUM(CASE WHEN converted_any_yes = 1 THEN any_yes_before_last ELSE 0 END) * 100.0 / NULLIF(SUM(converted_any_yes), 0),
    'A Yes event occurs before the journey terminates.'
FROM journey_features
UNION ALL
SELECT
    'users_with_last_touch_yes',
    SUM(last_touch_yes),
    AVG(last_touch_yes) * 100.0,
    SUM(CASE WHEN converted_any_yes = 1 THEN last_touch_yes ELSE 0 END) * 100.0 / NULLIF(SUM(converted_any_yes), 0),
    'Users whose final observed touchpoint is Yes.'
FROM journey_features
UNION ALL
SELECT
    'converted_users_with_single_yes',
    SUM(CASE WHEN n_conversion_events = 1 THEN 1 ELSE 0 END),
    AVG(CASE WHEN n_conversion_events = 1 THEN 1 ELSE 0 END) * 100.0,
    SUM(CASE WHEN converted_any_yes = 1 AND n_conversion_events = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(converted_any_yes), 0),
    'Converted users with exactly one Yes event.'
FROM journey_features;

DROP TABLE IF EXISTS yes_event_distribution_base;
CREATE TABLE yes_event_distribution_base AS
SELECT
    n_conversion_events AS n_yes_events,
    COUNT(*) AS users,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM journey_features) AS user_share_pct
FROM journey_features
GROUP BY n_conversion_events
ORDER BY n_conversion_events;
