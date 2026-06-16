function symmetric(groups: string[][]): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const group of groups) {
    for (const key of group) {
      const peers = group.filter((k) => k !== key);
      out[key] = [...(out[key] ?? []), ...peers];
    }
  }
  for (const key of Object.keys(out)) {
    out[key] = [...new Set(out[key])];
  }
  return out;
}

// ── Overview ────────────────────────────────────────────────────────────────
// label-group: all saturation evidence
// signal-group: AUC / Cramer / chi
// scope-group: dataset size
// scenario-group: sensitivity bars

// Precise column-to-column threads — clicking a chart column lights ONLY the
// genuinely related columns in other cards (see the overview relationship map):
//   row-Yes (49.44%) is the same metric in Card 1 & 2, and seeds the As-labeled
//   scenario; user any-Yes (83.63%) seeds De-dup; final-touch, pre-final and the
//   3% benchmark each map to their Card 4 scenario. Card 3 (AUC) stays internal.
const OVERVIEW_COLUMN_THREADS = symmetric([
  ["row-yes-rate", "scn-as-labeled"],
  ["user-any-yes", "multi-yes-users", "scn-dedup"],
  ["final-touch-yes", "scn-final"],
  ["pre-final-yes", "scn-droppre"],
  ["benchmark-3pct", "scn-bench"],
  ["channel-auc", "journey-auc", "combined-auc"],
  ["touchpoints", "users"],
]);

// Cluster / evidence-switcher selections light the whole theme (broad, one-way).
const OVERVIEW_CLUSTER_LINKS: Record<string, string[]> = {
  "scope-cluster": ["touchpoints", "users"],
  "label-cluster": ["row-yes-rate", "user-any-yes", "final-touch-yes", "multi-yes-users", "pre-final-yes"],
  "signal-cluster": ["channel-auc", "journey-auc", "combined-auc", "cramers-v"],
  "sensitivity-cluster": ["scn-as-labeled", "scn-final", "scn-dedup", "scn-droppre", "scn-bench", "scn-cons", "markov-stability"],
  "safe-cluster": ["label-cluster", "signal-cluster"],
};

export const OVERVIEW_LINKS: Record<string, string[]> = {
  ...OVERVIEW_COLUMN_THREADS,
  ...OVERVIEW_CLUSTER_LINKS,
};

// ── RQ1 ──────────────────────────────────────────────────────────────────────
// link evidence rows ↔ benchmark chart bars ↔ KPI cards
export const RQ1_LINKS = symmetric([
  ["row-yes-rate", "multi-yes-users", "pre-final-yes", "final-touch-yes", "user-any-yes"],
  ["benchmark-chart-row-yes", "row-yes-rate"],
  ["benchmark-chart-user-any-yes", "user-any-yes"],
]);

// ── RQ2 ──────────────────────────────────────────────────────────────────────
// channel signal group
// model fit group
// label risk group
// stability/markov group
export const RQ2_LINKS = symmetric([
  ["channel-auc", "cramers-v", "chi-square", "mcfadden-channel"],
  ["journey-auc", "combined-auc", "mcfadden-length"],
  ["row-yes-rate", "user-any-yes", "multi-yes-users", "pre-final-yes", "final-touch-yes"],
  ["markov-stability", "ch-email", "ch-search", "ch-direct", "ch-referral", "ch-social", "ch-display"],
]);

// ── RQ3 ──────────────────────────────────────────────────────────────────────
// each channel links its allocation row ↔ heatmap row
// scenario keys link scenario sensitivity in overview
export const RQ3_LINKS = symmetric([
  ["ch-email", "ch-email-heatmap"],
  ["ch-search", "ch-search-heatmap"],
  ["ch-direct", "ch-direct-heatmap"],
  ["ch-referral", "ch-referral-heatmap"],
  ["ch-social", "ch-social-heatmap"],
  ["ch-display", "ch-display-heatmap"],
  ["scn-as-labeled", "scn-final", "scn-dedup", "scn-droppre", "scn-bench", "scn-cons"],
]);

// ── Labels for Reset chip ───────────────────────────────────────────────────
export const KEY_LABELS: Record<string, string> = {
  "row-yes-rate": "Row Yes rate",
  "user-any-yes": "User any-Yes",
  "final-touch-yes": "Final-touch Yes",
  "multi-yes-users": "Multi-Yes users",
  "pre-final-yes": "Yes before final",
  "channel-auc": "Channel AUC",
  "journey-auc": "Journey-length AUC",
  "combined-auc": "Channel+length AUC",
  "cramers-v": "Cramer's V",
  "chi-square": "Chi-square",
  "mcfadden-channel": "Channel R²",
  "mcfadden-length": "Length R²",
  "markov-stability": "Rank stability",
  touchpoints: "Touchpoints",
  users: "Users",
  "label-cluster": "Label saturation",
  "signal-cluster": "Channel signal",
  "scope-cluster": "Dataset scope",
  "safe-cluster": "Safe conclusion",
  "sensitivity-cluster": "Scenario sensitivity",
  "scn-as-labeled": "As-labelled",
  "scn-final": "Final-touch",
  "scn-dedup": "De-duplicated",
  "scn-droppre": "Drop-pre-final",
  "scn-bench": "Benchmark-cal.",
  "scn-cons": "Conservative",
  "ch-email": "Email",
  "ch-search": "Search Ads",
  "ch-direct": "Direct Traffic",
  "ch-referral": "Referral",
  "ch-social": "Social Media",
  "ch-display": "Display Ads",
};
