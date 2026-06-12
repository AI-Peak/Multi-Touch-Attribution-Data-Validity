/** Project-wide constants. Ported from the JSX prototype's data.jsx. */

export const PAGES = [
  { id: "overview", idx: "01", label: "Overview", href: "/overview", tag: null },
  { id: "rq1", idx: "02", label: "RQ1 · Validity Audit", href: "/rq1", tag: null },
  { id: "rq2", idx: "03", label: "RQ2 · Diagnostics", href: "/rq2", tag: null },
  { id: "rq3", idx: "04", label: "RQ3 · Simulator", href: "/rq3", tag: null },
  { id: "assistant", idx: "05", label: "AI Assistant", href: "/assistant", tag: "beta" },
  { id: "safe", idx: "06", label: "Safe Recommendation", href: "/safe", tag: null },
  { id: "presentation", idx: "TV", label: "Presentation Mode", href: "/presentation", tag: "demo" },
] as const;

export type PageId = (typeof PAGES)[number]["id"];

export const CHANNELS = [
  "Direct Traffic",
  "Display Ads",
  "Email",
  "Referral",
  "Search Ads",
  "Social Media",
] as const;

export type Channel = (typeof CHANNELS)[number];

export const CH_SHORT = [
  "Direct",
  "Display",
  "Email",
  "Referral",
  "Search",
  "Social",
] as const;

/** Base efficiency (conversions per $1k) — precomputed, label-suspect. */
export const CH_EFF: readonly number[] = [2.1, 0.92, 3.35, 1.78, 2.58, 1.24];

export const METHODS = [
  "Equal split",
  "Row conversion rate weighted",
  "Linear",
  "First-touch",
  "Last-touch",
  "Markov",
] as const;

export type Method = (typeof METHODS)[number];

export const METHOD_WEIGHTS: Record<Method, readonly number[]> = {
  "Equal split": [1, 1, 1, 1, 1, 1],
  "Row conversion rate weighted": [0.182, 0.121, 0.205, 0.149, 0.214, 0.129],
  Linear: [0.176, 0.15, 0.182, 0.16, 0.178, 0.154],
  "First-touch": [0.12, 0.232, 0.11, 0.15, 0.158, 0.23],
  "Last-touch": [0.238, 0.092, 0.25, 0.15, 0.19, 0.08],
  Markov: [0.205, 0.11, 0.22, 0.142, 0.205, 0.118],
};

export const METHOD_STABILITY: Record<Method, number> = {
  "Equal split": 1.0,
  "Row conversion rate weighted": 0.31,
  Linear: 0.77,
  "First-touch": -0.14,
  "Last-touch": 0.09,
  Markov: 0.43,
};

export type LabelScenario = {
  id: string;
  name: string;
  mult: number;
  note: string;
};

export const LABEL_SCENARIOS: readonly LabelScenario[] = [
  {
    id: "as-labeled",
    name: "As-labeled (row Yes = 49.44%)",
    mult: 1.0,
    note: "Raw row-level labels, no correction",
  },
  {
    id: "final-touch",
    name: "Final-touch label only",
    mult: 0.74,
    note: "Keep only the converting final touch",
  },
  {
    id: "dedup-user",
    name: "De-dup any-Yes per user (83.63%)",
    mult: 0.61,
    note: "Collapse to one outcome per user",
  },
  {
    id: "drop-pre",
    name: "Drop pre-final Yes events",
    mult: 0.55,
    note: "Remove Yes occurring before final touch",
  },
  {
    id: "bench-cal",
    name: "Benchmark-calibrated to 3%",
    mult: 0.21,
    note: "Re-scale to e-commerce prior",
  },
  {
    id: "conservative",
    name: "Conservative (labels suspect)",
    mult: 0.16,
    note: "Strong shrinkage toward null",
  },
];

/** Headline study numbers (from the pipeline). */
export const STUDY = {
  touchpoints: 10_000,
  users: 2847,
  rowYesRate: 0.4944,
  userAnyYes: 0.8363,
  rowChannelAUC: 0.4902,
  jlenAUC: 0.7549,
  jlenChAUC: 0.7536,
  chiP: 0.8598,
  cramersV: 0.0139,
  mcfaddenCh: 0.0021,
  mcfaddenJlen: 0.2604,
  pipelineVersion: "v1.3",
  lastRefresh: "2026-06-05",
} as const;
