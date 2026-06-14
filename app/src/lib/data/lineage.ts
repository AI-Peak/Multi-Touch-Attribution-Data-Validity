export type LineageKey =
  | "touchpoints"
  | "users"
  | "row-yes-rate"
  | "user-any-yes"
  | "final-touch-yes"
  | "multi-yes-users"
  | "pre-final-yes"
  | "chi-square"
  | "cramers-v"
  | "channel-auc"
  | "journey-auc"
  | "combined-auc"
  | "mcfadden-channel"
  | "mcfadden-length"
  | "markov-stability"
  | "method-weights"
  | "attribution-allocation"
  | "scenario-multiplier"
  | "threshold-lab";

export type LineageInfo = {
  title: string;
  source: string;
  transform: string;
  refresh: string;
  caveat: string;
};

export const LINEAGE: Record<LineageKey, LineageInfo> = {
  touchpoints: {
    title: "Touchpoint row count",
    source: "Raw public MTA touchpoint table after schema validation.",
    transform: "Count rows after required fields are present and channel labels are normalized.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "This proves scope, not causal quality. It does not validate the conversion label.",
  },
  users: {
    title: "Unique user journeys",
    source: "Journey identifiers from the same touchpoint table.",
    transform: "Distinct user/journey IDs counted after deduplicating invalid rows.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "User count anchors denominators; it does not imply independent causal observations.",
  },
  "row-yes-rate": {
    title: "Row-level Yes rate",
    source: "Conversion label column on 10,000 touchpoint rows.",
    transform: "Rows with label Yes divided by all touchpoint rows.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "Row labels can repeat within one journey, so this is not an outcome conversion rate.",
  },
  "user-any-yes": {
    title: "User any-Yes rate",
    source: "Journey-level aggregation of the conversion label.",
    transform: "Users with at least one Yes divided by all users.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "This is useful for saturation evidence, but still inherits label-validity risk.",
  },
  "final-touch-yes": {
    title: "Final-touch Yes rate",
    source: "Last touchpoint in each user journey.",
    transform: "Journeys whose final touch carries a Yes label divided by all journeys.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "Closer to an outcome proxy, but not independently verified against real transactions.",
  },
  "multi-yes-users": {
    title: "Multiple Yes users",
    source: "Journey-level label sequence audit.",
    transform: "Users with more than one Yes label divided by users with any Yes.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "Repeated labels are a validity warning, not multiple independent conversions.",
  },
  "pre-final-yes": {
    title: "Pre-final Yes events",
    source: "Ordered touchpoint sequences by user journey.",
    transform: "Users with a Yes before the final touch divided by all users.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "A pre-final Yes weakens outcome alignment and direct attribution claims.",
  },
  "chi-square": {
    title: "Channel x conversion chi-square",
    source: "Contingency table of normalized channel and row-level label.",
    transform: "Pearson chi-square test for channel-label independence.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "A non-significant result is evidence against channel dependence, not proof of no effect.",
  },
  "cramers-v": {
    title: "Cramer's V channel association",
    source: "Same channel x label contingency table as the chi-square test.",
    transform: "Effect-size normalization of the chi-square statistic.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "Near-zero association supports weak-signal language only for this label definition.",
  },
  "channel-auc": {
    title: "Channel-only AUC",
    source: "Logistic diagnostic using channel identity as the only predictor.",
    transform: "Out-of-sample AUC on the row-level conversion label.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "AUC near 0.50 means the channel feature does not separate this suspect label.",
  },
  "journey-auc": {
    title: "Journey-length AUC",
    source: "Logistic diagnostic using journey length as predictor.",
    transform: "Out-of-sample AUC on the row-level conversion label.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "Strong signal here suggests confounding by touch count, not channel causality.",
  },
  "combined-auc": {
    title: "Channel + journey-length AUC",
    source: "Combined logistic diagnostic with channel and journey length.",
    transform: "Out-of-sample AUC compared against length-only and channel-only baselines.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "No lift over journey length means channel adds little usable signal.",
  },
  "mcfadden-channel": {
    title: "Channel McFadden R2",
    source: "Channel-only logistic model fit diagnostic.",
    transform: "McFadden pseudo-R2 against an intercept-only baseline.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "Tiny fit supports weak explanatory value, not a causal null theorem.",
  },
  "mcfadden-length": {
    title: "Journey-length McFadden R2",
    source: "Journey-length logistic model fit diagnostic.",
    transform: "McFadden pseudo-R2 against an intercept-only baseline.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "Fit dominance points to confounding risk that must be disclosed.",
  },
  "markov-stability": {
    title: "Rank stability score",
    source: "Scenario-level ranking comparison across attribution methods.",
    transform: "Spearman-style rank stability summarized into stable/moderate/unstable bands.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "A stability score is diagnostic. It is not a recommended budget weight.",
  },
  "method-weights": {
    title: "Attribution method weights",
    source: "Precomputed method-weight table used by the simulator.",
    transform: "Weights are normalized to sum to 100% before allocation calculations.",
    refresh: "Pipeline v1.3, refreshed 2026-06-05.",
    caveat: "Weights are sensitivity inputs, not causal estimates from a validated outcome label.",
  },
  "attribution-allocation": {
    title: "Budget allocation simulation",
    source: "Method weights, scenario multiplier, channel efficiency proxy, and user-entered budget.",
    transform: "Budget is multiplied by normalized weights; conversions use efficiency proxy x scenario multiplier.",
    refresh: "Computed live in the browser from pipeline constants.",
    caveat: "This is a what-if diagnostic. It must not be presented as a real budget optimizer.",
  },
  "scenario-multiplier": {
    title: "Label scenario multiplier",
    source: "Scenario assumptions derived from label-validity corrections.",
    transform: "Raw conversion volume is shrunk under final-touch, de-dup, benchmark, or conservative settings.",
    refresh: "Computed live in the browser from pipeline constants.",
    caveat: "Scenario multipliers communicate sensitivity to label definition, not ground truth.",
  },
  "threshold-lab": {
    title: "Threshold lab simulation",
    source: "Diagnostic profiles calibrated to the documented AUC values.",
    transform: "A simple score-separation curve estimates precision, recall, F1, and row mix as threshold moves.",
    refresh: "Computed live in the browser for demo explanation.",
    caveat: "This is an explanatory stress test, not a retrained production classifier.",
  },
};
