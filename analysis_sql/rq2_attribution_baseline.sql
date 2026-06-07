-- RQ2 SQL baseline: channel conversion rates and first/last/linear attribution.
-- These are baseline tables; Python analysis consumes them instead of recomputing them.

DROP TABLE IF EXISTS channel_conversion_rates_base;
CREATE TABLE channel_conversion_rates_base AS
SELECT
    channel,
    COUNT(*) AS touchpoints,
    SUM(is_conversion) AS conversion_touchpoints,
    AVG(is_conversion) * 100.0 AS conversion_rate_pct
FROM touchpoint_features
GROUP BY channel
ORDER BY channel;

DROP TABLE IF EXISTS attribution_baseline;
CREATE TABLE attribution_baseline AS
WITH scenarios AS (
    SELECT 'any_yes' AS label_scenario, user_id, converted_any_yes AS is_positive FROM journey_features
    UNION ALL
    SELECT 'last_touch_yes' AS label_scenario, user_id, last_touch_yes AS is_positive FROM journey_features
), positives AS (
    SELECT label_scenario, COUNT(*) AS positive_users
    FROM scenarios
    WHERE is_positive = 1
    GROUP BY label_scenario
), first_credit AS (
    SELECT
        s.label_scenario,
        j.first_touch_channel AS channel,
        COUNT(*) * 100.0 / p.positive_users AS first_touch_pct
    FROM scenarios s
    JOIN journey_features j ON s.user_id = j.user_id
    JOIN positives p ON s.label_scenario = p.label_scenario
    WHERE s.is_positive = 1
    GROUP BY s.label_scenario, j.first_touch_channel, p.positive_users
), last_credit AS (
    SELECT
        s.label_scenario,
        j.last_touch_channel AS channel,
        COUNT(*) * 100.0 / p.positive_users AS last_touch_pct
    FROM scenarios s
    JOIN journey_features j ON s.user_id = j.user_id
    JOIN positives p ON s.label_scenario = p.label_scenario
    WHERE s.is_positive = 1
    GROUP BY s.label_scenario, j.last_touch_channel, p.positive_users
), linear_credit AS (
    SELECT
        s.label_scenario,
        t.channel,
        SUM(t.linear_weight) AS channel_credit
    FROM scenarios s
    JOIN touchpoint_features t ON s.user_id = t.user_id
    WHERE s.is_positive = 1
    GROUP BY s.label_scenario, t.channel
), linear_total AS (
    SELECT label_scenario, SUM(channel_credit) AS total_credit
    FROM linear_credit
    GROUP BY label_scenario
), linear_share AS (
    SELECT
        l.label_scenario,
        l.channel,
        l.channel_credit * 100.0 / lt.total_credit AS linear_pct
    FROM linear_credit l
    JOIN linear_total lt ON l.label_scenario = lt.label_scenario
), channels AS (
    SELECT DISTINCT channel FROM touchpoint_features
), scenario_channels AS (
    SELECT s.label_scenario, c.channel
    FROM (SELECT DISTINCT label_scenario FROM scenarios) s
    CROSS JOIN channels c
)
SELECT
    sc.label_scenario,
    sc.channel,
    COALESCE(f.first_touch_pct, 0.0) AS first_touch_pct,
    COALESCE(l.last_touch_pct, 0.0) AS last_touch_pct,
    COALESCE(ls.linear_pct, 0.0) AS linear_pct
FROM scenario_channels sc
LEFT JOIN first_credit f ON sc.label_scenario = f.label_scenario AND sc.channel = f.channel
LEFT JOIN last_credit l ON sc.label_scenario = l.label_scenario AND sc.channel = l.channel
LEFT JOIN linear_share ls ON sc.label_scenario = ls.label_scenario AND sc.channel = ls.channel
ORDER BY sc.label_scenario, sc.channel;

