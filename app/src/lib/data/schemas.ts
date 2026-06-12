import { z } from "zod";

const num = z.number().nullable();

const MetricRow = z.object({
  metric: z.string(),
  value: num,
  note: z.string().nullable().optional(),
});
export type MetricRow = z.infer<typeof MetricRow>;

const LabelEventRow = z.object({
  metric: z.string(),
  count: num,
  pct_all_users: num,
  pct_converted_any_yes_users: num,
  interpretation: z.string().nullable().optional(),
});
export type LabelEventRow = z.infer<typeof LabelEventRow>;

const BenchmarkRow = z.object({
  source: z.string(),
  period: z.string().nullable().optional(),
  rate_pct: num,
  denominator: z.string().nullable().optional(),
  url: z.string().nullable().optional(),
  note: z.string().nullable().optional(),
});
export type BenchmarkRow = z.infer<typeof BenchmarkRow>;

export const AuditSchema = z.object({
  conversion_rates: z.array(MetricRow),
  label_event_audit: z.array(LabelEventRow),
  benchmark_conversion_rates: z.array(BenchmarkRow),
  data_validity_summary: z.array(MetricRow),
});
export type AuditData = z.infer<typeof AuditSchema>;

const AttributionRow = z.object({
  label_scenario: z.string(),
  channel: z.string(),
  first_touch_pct: num,
  last_touch_pct: num,
  linear_pct: num,
});
export type AttributionRow = z.infer<typeof AttributionRow>;

const ChannelRateRow = z.object({
  channel: z.string(),
  touchpoints: num,
  conversion_touchpoints: num,
  conversion_rate_pct: num,
});
export type ChannelRateRow = z.infer<typeof ChannelRateRow>;

export const AttributionSchema = z.object({
  attribution_baseline: z.array(AttributionRow),
  channel_conversion_rates: z.array(ChannelRateRow),
});
export type AttributionData = z.infer<typeof AttributionSchema>;

const LogisticMetricRow = z.object({
  model: z.string(),
  n_obs: num,
  n_train: num,
  n_test: num,
  positive_rate_pct: num,
  pseudo_r2_mcfadden: num,
  auc_test: num,
});
export type LogisticMetricRow = z.infer<typeof LogisticMetricRow>;

const LogisticCoefRow = z.object({
  model: z.string(),
  term: z.string(),
  coef: num,
  odds_ratio: num,
  or_ci_low: num,
  or_ci_high: num,
  p_value: num,
});
export type LogisticCoefRow = z.infer<typeof LogisticCoefRow>;

const LogisticAdjShareRow = z.object({
  channel: z.string(),
  logistic_adjusted_share_pct: num,
  coef: num,
  odds_ratio: num,
  p_value: num,
});
export type LogisticAdjShareRow = z.infer<typeof LogisticAdjShareRow>;

const MarkovRemovalRow = z.object({
  channel: z.string(),
  baseline_conversion_probability: num,
  probability_without_channel: num,
  removal_effect: num,
  positive_removal_effect: num,
  markov_positive_share_pct: num,
});
export type MarkovRemovalRow = z.infer<typeof MarkovRemovalRow>;

const MarkovShareRow = z.object({
  channel: z.string(),
  markov_positive_share_pct: num,
  removal_effect: num,
  positive_removal_effect: num,
});
export type MarkovShareRow = z.infer<typeof MarkovShareRow>;

export const ModelSchema = z.object({
  logistic_metrics: z.array(LogisticMetricRow),
  logistic_coefficients: z.array(LogisticCoefRow),
  logistic_adjusted_share: z.array(LogisticAdjShareRow),
  markov_removal_effects: z.array(MarkovRemovalRow),
  markov_attribution_share: z.array(MarkovShareRow),
});
export type ModelData = z.infer<typeof ModelSchema>;

const RankStabilityRow = z.object({
  scenario: z.string(),
  target_rate_pct: num,
  positive_users: num,
  positive_rate_pct: num,
  spearman_linear_share_vs_current: num,
  top_channel_linear: z.string().nullable().optional(),
  top_channel_linear_share_pct: num,
});
export type RankStabilityRow = z.infer<typeof RankStabilityRow>;

const ChannelShareRow = z.object({
  scenario: z.string(),
  channel: z.string(),
  first_touch_pct: num,
  last_touch_pct: num,
  linear_pct: num,
});
export type ChannelShareRow = z.infer<typeof ChannelShareRow>;

export const SensitivitySchema = z.object({
  rank_stability: z.array(RankStabilityRow),
  channel_shares: z.array(ChannelShareRow),
});
export type SensitivityData = z.infer<typeof SensitivitySchema>;

const SimulationRow = z.object({
  scenario: z.string(),
  conversions: num,
  revenue: num,
  budget: num,
  revenue_per_conversion: num,
  delta_conversions_vs_s0: num,
  delta_revenue_vs_s0: num,
  delta_revenue_pct_vs_s0: num,
});
export type SimulationRow = z.infer<typeof SimulationRow>;

export const SimulationSchema = z.object({
  simulation_results: z.array(SimulationRow),
});
export type SimulationData = z.infer<typeof SimulationSchema>;
