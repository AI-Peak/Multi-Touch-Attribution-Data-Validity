"use client";

import Link from "next/link";
import type { Route } from "next";
import { PageHead } from "@/components/primitives/PageHead";
import { Section } from "@/components/primitives/Section";
import { KpiCard } from "@/components/primitives/KpiCard";
import { ChartCard } from "@/components/primitives/ChartCard";
import { Chip } from "@/components/primitives/Chip";
import { ResetSelection } from "@/components/primitives/ResetSelection";
import { BarChart } from "@/components/charts/BarChart";
import { HBarChart } from "@/components/charts/HBarChart";
import { CHART_TOKENS } from "@/components/charts/theme";
import { CrossFilterProvider, useCrossFilter } from "@/lib/crossfilter/context";
import { OVERVIEW_LINKS } from "@/lib/crossfilter/links";
import { STUDY } from "@/lib/data/constants";
import { fmtInt, fmtPct, fmtFloat } from "@/lib/format";
import { IconArrowR } from "@/lib/icons";

type EvidenceKey = "scope" | "label" | "signal" | "sensitivity" | "safe";

type EvidenceDetail = {
  label: string;
  eyebrow: string;
  title: string;
  desc: string;
  href: Route;
  cta: string;
  metrics: ReadonlyArray<{ label: string; value: string; note: string; cfKey?: string }>;
};

const DETAILS: Record<EvidenceKey, EvidenceDetail> = {
  scope: {
    label: "Dataset scope",
    eyebrow: "Input evidence",
    title: "The app audits a fixed precomputed dataset",
    desc: "The dashboard starts from 10,000 touchpoint rows and 2,847 user journeys. The app does not retrain models or recompute SQL during the demo; it exposes the validated pipeline outputs.",
    href: "/overview",
    cta: "Stay on overview",
    metrics: [
      { label: "Touchpoints", value: fmtInt(STUDY.touchpoints), note: "Rows ingested by the analysis pipeline", cfKey: "touchpoints" },
      { label: "Users", value: fmtInt(STUDY.users), note: "Unique journeys represented in the data", cfKey: "users" },
      { label: "Pipeline refresh", value: STUDY.lastRefresh, note: "Precomputed evidence version shown in the sidebar" },
    ],
  },
  label: {
    label: "Label saturation",
    eyebrow: "RQ1 evidence",
    title: "Conversion labels are too common to behave like outcomes",
    desc: "The row-level Yes rate and user-level any-Yes rate are far above a realistic e-commerce benchmark. Multiple and pre-final Yes events suggest the label is not outcome-aligned.",
    href: "/rq1",
    cta: "Open RQ1 audit",
    metrics: [
      { label: "Row-level Yes", value: fmtPct(STUDY.rowYesRate), note: "4,944 of 10,000 rows are labelled Yes", cfKey: "row-yes-rate" },
      { label: "User any-Yes", value: fmtPct(STUDY.userAnyYes), note: "At least one Yes appears for most users", cfKey: "user-any-yes" },
      { label: "Gap vs 3% benchmark", value: "27.9x", note: "Observed user any-Yes rate is far above benchmark" },
    ],
  },
  signal: {
    label: "Weak channel signal",
    eyebrow: "RQ2 evidence",
    title: "Channel identity is close to statistically inert",
    desc: "The channel-only model is at chance, while journey length is predictive. This points to confounding rather than meaningful channel performance.",
    href: "/rq2",
    cta: "Open RQ2 diagnostics",
    metrics: [
      { label: "Row-channel AUC", value: fmtFloat(STUDY.rowChannelAUC, 4), note: "Indistinguishable from chance", cfKey: "channel-auc" },
      { label: "Cramer's V", value: fmtFloat(STUDY.cramersV, 4), note: "Near-zero channel association", cfKey: "cramers-v" },
      { label: "Journey-length AUC", value: fmtFloat(STUDY.jlenAUC, 4), note: "Length, not channel, carries predictive signal", cfKey: "journey-auc" },
    ],
  },
  sensitivity: {
    label: "Scenario fragility",
    eyebrow: "RQ3 evidence",
    title: "Attribution shares move under plausible label corrections",
    desc: "The same channel can receive materially different credit depending on the label scenario and method. Stable ranges are safer than point recommendations.",
    href: "/rq3",
    cta: "Open RQ3 simulator",
    metrics: [
      { label: "Email share", value: "20.5% → 7.1%", note: "Falls from as-labelled to conservative scenario", cfKey: "scn-as-labeled" },
      { label: "Markov stability", value: "0.43", note: "Moderate rank stability, not robust enough for a winner", cfKey: "markov-stability" },
      { label: "Benchmark scenario", value: "9.2%", note: "Calibration shrinks the apparent channel share", cfKey: "scn-bench" },
    ],
  },
  safe: {
    label: "Safe conclusion",
    eyebrow: "Recommendation boundary",
    title: "Use the dataset for audit, not direct budget attribution",
    desc: "The defensible conclusion is about data validity. The dashboard should help present why causal channel-winner claims are outside the evidence.",
    href: "/safe",
    cta: "Open safe recommendation",
    metrics: [
      { label: "Allowed claim", value: "Validity audit", note: "Use ranges, diagnostics, and limitations" },
      { label: "Avoided claim", value: "Causal winner", note: "Do not optimize budget directly from this dataset" },
      { label: "Presentation frame", value: "Conditional", note: "Resolve conversion-label validity before attribution" },
    ],
  },
};

// Which EvidenceKey each cluster cfKey maps to (for drill-down switching)
const CLUSTER_KEY_TO_EVIDENCE: Record<string, EvidenceKey> = {
  "scope-cluster": "scope",
  touchpoints: "scope",
  users: "scope",
  "label-cluster": "label",
  "row-yes-rate": "label",
  "user-any-yes": "label",
  "final-touch-yes": "label",
  "multi-yes-users": "label",
  "pre-final-yes": "label",
  "signal-cluster": "signal",
  "channel-auc": "signal",
  "journey-auc": "signal",
  "combined-auc": "signal",
  "cramers-v": "signal",
  "sensitivity-cluster": "sensitivity",
  "scn-as-labeled": "sensitivity",
  "scn-final": "sensitivity",
  "scn-dedup": "sensitivity",
  "scn-droppre": "sensitivity",
  "scn-bench": "sensitivity",
  "scn-cons": "sensitivity",
  "safe-cluster": "safe",
};

// Evidence key → the cfKey to select from the drill-down switcher.
// (sensitivity has no KPI cluster, so a CLUSTERS lookup would miss it.)
const EVIDENCE_TO_CFKEY: Record<EvidenceKey, string> = {
  scope: "scope-cluster",
  label: "label-cluster",
  signal: "signal-cluster",
  sensitivity: "sensitivity-cluster",
  safe: "safe-cluster",
};

const CLUSTERS: ReadonlyArray<{
  cfKey: string;
  evidenceKey: EvidenceKey;
  label: string;
  kpiDefs: ReadonlyArray<{ label: string; value: string; caption?: string; valueSmall?: boolean; warn?: boolean; cfKey: string }>;
  warn: boolean;
}> = [
  {
    cfKey: "scope-cluster",
    evidenceKey: "scope",
    label: "Dataset scope",
    warn: false,
    kpiDefs: [
      { label: "Total touchpoints", value: fmtInt(STUDY.touchpoints), caption: "rows ingested", cfKey: "touchpoints" },
      { label: "Users", value: fmtInt(STUDY.users), caption: "unique journeys", cfKey: "users" },
    ],
  },
  {
    cfKey: "label-cluster",
    evidenceKey: "label",
    label: "Label saturation",
    warn: true,
    kpiDefs: [
      { label: "Row-level Yes rate", value: fmtPct(STUDY.rowYesRate), caption: "4,944 / 10,000 rows", cfKey: "row-yes-rate" },
      { label: "User any-Yes conversion", value: fmtPct(STUDY.userAnyYes), caption: "≥1 Yes per user", cfKey: "user-any-yes" },
    ],
  },
  {
    cfKey: "signal-cluster",
    evidenceKey: "signal",
    label: "Channel signal",
    warn: false,
    kpiDefs: [
      { label: "Row-channel AUC", value: fmtFloat(STUDY.rowChannelAUC, 4), caption: "approx chance (0.50)", cfKey: "channel-auc" },
    ],
  },
  {
    cfKey: "safe-cluster",
    evidenceKey: "safe",
    label: "Safe conclusion",
    warn: true,
    kpiDefs: [
      { label: "Main conclusion", value: "Not safe for direct attribution", valueSmall: true, warn: true, cfKey: "safe-cluster" },
    ],
  },
];

function OverviewContent() {
  const cf = useCrossFilter();

  // Derive active EvidenceKey from cf.selected
  const active: EvidenceKey =
    (cf.selected ? CLUSTER_KEY_TO_EVIDENCE[cf.selected] : null) ?? "label";
  const detail = DETAILS[active];

  // Cross-card highlight: which diagnostic charts relate to the current selection.
  const isFocus = (key: string) => cf.status(key) === "focus";
  const convFocus = isFocus("row-yes-rate") || isFocus("user-any-yes") || isFocus("benchmark-3pct");
  const labelEventFocus =
    isFocus("row-yes-rate") || isFocus("final-touch-yes") || isFocus("multi-yes-users") || isFocus("pre-final-yes");
  const modelFocus = isFocus("channel-auc") || isFocus("journey-auc") || isFocus("combined-auc");
  const sensitivityFocus =
    isFocus("scn-as-labeled") || isFocus("scn-final") || isFocus("scn-dedup") ||
    isFocus("scn-droppre") || isFocus("scn-bench") || isFocus("scn-cons");
  // Only recede other cards when the selection actually lights up a chart
  // (a "dataset scope" selection hits no chart, so nothing should fade).
  const selectionHitsCharts = convFocus || labelEventFocus || modelFocus || sensitivityFocus;

  return (
    <div className="page">
      <PageHead
        eyebrow="Overview - Data validity audit"
        title="Dataset validity at a glance"
        desc="Summary metrics for the Multi-Touch Attribution dataset under audit. Select any KPI or diagnostic chart to inspect the evidence behind the conclusion."
      />

      {/* KPI clusters */}
      <div className="kpi-clusters">
        {CLUSTERS.map((cluster) => {
          const clusterStatus = cf.status(cluster.cfKey);
          return (
            <div
              key={cluster.cfKey}
              className={
                "kpi-cluster" +
                (cluster.warn ? " warn" : "") +
                (clusterStatus === "focus" ? " active cross-focus" : "")
              }
              style={{ flex: cluster.kpiDefs.length }}
            >
              <div className="kpi-cluster-label">{cluster.label}</div>
              <div className="kpi-cluster-cards">
                {cluster.kpiDefs.map((kpi) => (
                  <KpiCard
                    key={kpi.label}
                    label={kpi.label}
                    value={kpi.value}
                    caption={kpi.caption}
                    valueSmall={kpi.valueSmall}
                    warn={kpi.warn}
                    active={cf.status(kpi.cfKey) === "focus"}
                    onClick={() => cf.select(kpi.cfKey, kpi.label)}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Drill-down */}
      <Section
        title="Evidence drill-down"
        note="The selected evidence path updates from KPI and chart clicks"
        right={
          cf.isActive ? (
            <ResetSelection />
          ) : (
            <Chip kind={active === "safe" ? "high" : "neutral"}>{detail.label}</Chip>
          )
        }
      >
        <div className="drilldown-card">
          <div className="drilldown-copy">
            <div className="eyebrow-mono">{detail.eyebrow}</div>
            <h2>{detail.title}</h2>
            <p>{detail.desc}</p>
            <div className="evidence-switcher" aria-label="Evidence path selector">
              {Object.entries(DETAILS).map(([key, item]) => (
                <button
                  className={"mini-switch" + (active === key ? " active" : "")}
                  key={key}
                  onClick={() => cf.select(EVIDENCE_TO_CFKEY[key as EvidenceKey], item.label)}
                  type="button"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
          <div className="drilldown-metrics">
            {detail.metrics.map((m) => (
              <div
                className={"drilldown-metric" + (cf.status(m.cfKey) === "focus" ? " cross-focus" : "")}
                key={m.label}
              >
                <span>{m.label}</span>
                <b className="num">{m.value}</b>
                <small>{m.note}</small>
              </div>
            ))}
          </div>
          <Link className="drilldown-link" href={detail.href}>
            {detail.cta}
            <IconArrowR size={15} />
          </Link>
        </div>
      </Section>

      {/* Diagnostic charts */}
      <Section title="Diagnostic panels" note="Four evidence views supporting the conclusion">
        <div className="grid-2">
          <ChartCard
            title="Conversion rate gap"
            caption="Observed rates vs. a typical e-commerce benchmark (3%)."
            tag="RQ1"
            active={convFocus}
            muted={selectionHitsCharts && !convFocus}
            onClick={() => cf.select("label-cluster", "Label saturation")}
          >
            <BarChart
              height={172}
              yMax={1}
              yFmt={(v) => `${Math.round(v * 100)}%`}
              xAxisPadding={{ left: 64, right: 64 }}
              threshold={{
                value: 0.03,
                label: "3% benchmark",
                color: CHART_TOKENS.navy,
                labelPosition: "start",
              }}
              getStatus={(d) => cf.status(d.cfKey)}
              onDatumClick={(d) => { if (d.cfKey) cf.select(d.cfKey, d.label); }}
              data={[
                { label: "Benchmark", value: 0.03, color: CHART_TOKENS.navy, cfKey: "benchmark-3pct" },
                { label: "Row Yes", value: STUDY.rowYesRate, warn: true, cfKey: "row-yes-rate" },
                { label: "User any-Yes", value: STUDY.userAnyYes, warn: true, cfKey: "user-any-yes" },
              ]}
            />
          </ChartCard>

          <ChartCard
            title="Label-event audit"
            caption="Where conversion labels concentrate across the journey."
            tag="RQ2"
            active={labelEventFocus}
            muted={selectionHitsCharts && !labelEventFocus}
            onClick={() => cf.select("label-cluster", "Label saturation")}
          >
            <HBarChart
              xMax={1}
              xFmt={(v) => `${Math.round(v * 100)}%`}
              getStatus={(d) => cf.status(d.cfKey)}
              onDatumClick={(d) => { if (d.cfKey) cf.select(d.cfKey, d.label); }}
              data={[
                { label: "Row-level Yes", value: 0.4944, warn: true, cfKey: "row-yes-rate" },
                { label: "Final-touch Yes", value: 0.612, cfKey: "final-touch-yes" },
                { label: "Multi-Yes users", value: 0.608, warn: true, cfKey: "multi-yes-users" },
                { label: "Yes before final", value: 0.528, warn: true, cfKey: "pre-final-yes" },
              ]}
            />
          </ChartCard>

          <ChartCard
            title="Model comparison"
            caption="Predictive AUC: channel signal vs. journey-length signal."
            tag="RQ2"
            active={modelFocus}
            muted={selectionHitsCharts && !modelFocus}
            onClick={() => cf.select("signal-cluster", "Channel signal")}
          >
            <BarChart
              height={172}
              yMax={1}
              yFmt={(v) => v.toFixed(2)}
              threshold={{ value: 0.5, label: "chance" }}
              getStatus={(d) => cf.status(d.cfKey)}
              onDatumClick={(d) => { if (d.cfKey) cf.select(d.cfKey, d.label); }}
              data={[
                { label: "Channel", value: STUDY.rowChannelAUC, warn: true, cfKey: "channel-auc" },
                { label: "Journey len", value: STUDY.jlenAUC, color: CHART_TOKENS.navy, cfKey: "journey-auc" },
                { label: "Chan+len", value: STUDY.jlenChAUC, color: CHART_TOKENS.navyLight, cfKey: "combined-auc" },
              ]}
            />
          </ChartCard>

          <ChartCard
            title="Sensitivity stability"
            caption="Email's attributed credit as label corrections get stricter — its share falls 21% → 7%."
            tag="RQ3"
            active={sensitivityFocus}
            muted={selectionHitsCharts && !sensitivityFocus}
            onClick={() => cf.select("sensitivity-cluster", "Scenario sensitivity")}
          >
            <div className="chart-legend" aria-hidden="true">
              <span className="chart-legend-item"><i style={{ background: CHART_TOKENS.navy }} />Lenient (trust labels)</span>
              <span className="chart-legend-item"><i style={{ background: CHART_TOKENS.navyLight }} />Moderate fix</span>
              <span className="chart-legend-item"><i style={{ background: CHART_TOKENS.amber }} />Strict correction</span>
            </div>
            <BarChart
              height={158}
              yMax={0.3}
              yFmt={(v) => `${Math.round(v * 100)}%`}
              getStatus={(d) => cf.status(d.cfKey)}
              onDatumClick={(d) => { if (d.cfKey) cf.select(d.cfKey, d.label); }}
              data={[
                { label: "Raw labels", value: 0.205, cfKey: "scn-as-labeled" },
                { label: "Final-touch", value: 0.171, cfKey: "scn-final" },
                { label: "Per user", value: 0.151, color: CHART_TOKENS.navyLight, cfKey: "scn-dedup" },
                { label: "Drop early", value: 0.118, color: CHART_TOKENS.navyLight, cfKey: "scn-droppre" },
                { label: "Benchmark", value: 0.092, warn: true, cfKey: "scn-bench" },
                { label: "Conservative", value: 0.071, warn: true, cfKey: "scn-cons" },
              ]}
            />
          </ChartCard>
        </div>
      </Section>

      <div className="footnote">
        All panels derive from the same precomputed pipeline. Charts are
        diagnostic, not prescriptive; no channel is endorsed as a winner.
      </div>
    </div>
  );
}

export default function OverviewPage() {
  return (
    <CrossFilterProvider links={OVERVIEW_LINKS}>
      <OverviewContent />
    </CrossFilterProvider>
  );
}
