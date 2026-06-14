"use client";

import Link from "next/link";
import type { Route } from "next";
import { useState } from "react";
import { PageHead } from "@/components/primitives/PageHead";
import { Section } from "@/components/primitives/Section";
import { KpiCard } from "@/components/primitives/KpiCard";
import { ChartCard } from "@/components/primitives/ChartCard";
import { Chip } from "@/components/primitives/Chip";
import { BarChart } from "@/components/charts/BarChart";
import { HBarChart } from "@/components/charts/HBarChart";
import { CHART_TOKENS } from "@/components/charts/theme";
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
  metrics: ReadonlyArray<readonly [string, string, string]>;
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
      ["Touchpoints", fmtInt(STUDY.touchpoints), "Rows ingested by the analysis pipeline"],
      ["Users", fmtInt(STUDY.users), "Unique journeys represented in the data"],
      ["Pipeline refresh", STUDY.lastRefresh, "Precomputed evidence version shown in the sidebar"],
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
      ["Row-level Yes", fmtPct(STUDY.rowYesRate), "4,944 of 10,000 rows are labelled Yes"],
      ["User any-Yes", fmtPct(STUDY.userAnyYes), "At least one Yes appears for most users"],
      ["Gap vs 3% benchmark", "27.9x", "Observed user any-Yes rate is far above benchmark"],
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
      ["Row-channel AUC", fmtFloat(STUDY.rowChannelAUC, 4), "Indistinguishable from chance"],
      ["Cramer's V", fmtFloat(STUDY.cramersV, 4), "Near-zero channel association"],
      ["Journey-length AUC", fmtFloat(STUDY.jlenAUC, 4), "Length, not channel, carries predictive signal"],
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
      ["Email share", "20.5% -> 7.1%", "Falls from as-labelled to conservative scenario"],
      ["Markov stability", "0.43", "Moderate rank stability, not robust enough for a winner"],
      ["Benchmark scenario", "9.2%", "Calibration shrinks the apparent channel share"],
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
      ["Allowed claim", "Validity audit", "Use ranges, diagnostics, and limitations"],
      ["Avoided claim", "Causal winner", "Do not optimize budget directly from this dataset"],
      ["Presentation frame", "Conditional", "Resolve conversion-label validity before attribution"],
    ],
  },
};

export default function OverviewPage() {
  const [active, setActive] = useState<EvidenceKey>("label");
  const [activeBar, setActiveBar] = useState<string | null>("User any-Yes");
  const detail = DETAILS[active];

  function focusEvidence(next: EvidenceKey, bar: string | null = null) {
    setActive(next);
    setActiveBar(bar);
  }

  const kpis: ReadonlyArray<{
    label: string;
    value: string;
    caption?: string;
    valueSmall?: boolean;
    warn?: boolean;
    evidence: EvidenceKey;
  }> = [
    {
      label: "Total touchpoints",
      value: fmtInt(STUDY.touchpoints),
      caption: "rows ingested",
      evidence: "scope",
    },
    {
      label: "Users",
      value: fmtInt(STUDY.users),
      caption: "unique journeys",
      evidence: "scope",
    },
    {
      label: "Row-level Yes rate",
      value: fmtPct(STUDY.rowYesRate),
      caption: "4,944 / 10,000 rows",
      evidence: "label",
    },
    {
      label: "User any-Yes conversion",
      value: fmtPct(STUDY.userAnyYes),
      caption: ">=1 Yes per user",
      evidence: "label",
    },
    {
      label: "Row-channel AUC",
      value: fmtFloat(STUDY.rowChannelAUC, 4),
      caption: "approx chance (0.50)",
      evidence: "signal",
    },
    {
      label: "Main conclusion",
      value: "Not safe for direct attribution",
      valueSmall: true,
      warn: true,
      evidence: "safe",
    },
  ];

  return (
    <div className="page">
      <PageHead
        eyebrow="Overview - Data validity audit"
        title="Dataset validity at a glance"
        desc="Summary metrics for the Multi-Touch Attribution dataset under audit. Select any KPI or diagnostic chart to inspect the evidence behind the conclusion."
      />

      <div className="kpi-row">
        {kpis.map((k) => (
          <KpiCard
            key={k.label}
            label={k.label}
            value={k.value}
            caption={k.caption}
            valueSmall={k.valueSmall}
            warn={k.warn}
            active={active === k.evidence}
            onClick={() => focusEvidence(k.evidence, k.label)}
          />
        ))}
      </div>

      <Section
        title="Evidence drill-down"
        note="The selected evidence path updates from KPI and chart clicks"
        right={<Chip kind={active === "safe" ? "high" : "neutral"}>{detail.label}</Chip>}
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
                  onClick={() => setActive(key as EvidenceKey)}
                  type="button"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
          <div className="drilldown-metrics">
            {detail.metrics.map(([metric, value, note]) => (
              <div className="drilldown-metric" key={metric}>
                <span>{metric}</span>
                <b className="num">{value}</b>
                <small>{note}</small>
              </div>
            ))}
          </div>
          <Link className="drilldown-link" href={detail.href}>
            {detail.cta}
            <IconArrowR size={15} />
          </Link>

        </div>
      </Section>

      <Section
        title="Diagnostic panels"
        note="Four evidence views supporting the conclusion"
      >
        <div className="grid-2">
          <ChartCard
            title="Conversion rate gap"
            caption="Observed rates vs. a typical e-commerce benchmark (3%)."
            tag="RQ1"
            active={active === "label"}
            onClick={() => focusEvidence("label")}
          >
            <BarChart
              height={172}
              yMax={1}
              yFmt={(v) => `${Math.round(v * 100)}%`}
              threshold={{ value: 0.03, label: "3% benchmark" }}
              activeLabel={active === "label" ? activeBar : null}
              onDatumClick={(datum) => focusEvidence("label", datum.label)}
              data={[
                { label: "Benchmark", value: 0.03, color: CHART_TOKENS.grey },
                { label: "Row Yes", value: STUDY.rowYesRate, warn: true },
                { label: "User any-Yes", value: STUDY.userAnyYes, warn: true },
              ]}
            />
          </ChartCard>

          <ChartCard
            title="Label-event audit"
            caption="Where conversion labels concentrate across the journey."
            tag="RQ2"
            active={active === "label"}
            onClick={() => focusEvidence("label")}
          >
            <HBarChart
              xMax={1}
              xFmt={(v) => `${Math.round(v * 100)}%`}
              activeLabel={active === "label" ? activeBar : null}
              onDatumClick={(datum) => focusEvidence("label", datum.label)}
              data={[
                { label: "Row-level Yes", value: 0.4944, warn: true },
                { label: "Final-touch Yes", value: 0.612 },
                { label: "Multi-Yes users", value: 0.608, warn: true },
                { label: "Yes before final", value: 0.528, warn: true },
              ]}
            />
          </ChartCard>

          <ChartCard
            title="Model comparison"
            caption="Predictive AUC: channel signal vs. journey-length signal."
            tag="RQ2"
            active={active === "signal"}
            onClick={() => focusEvidence("signal")}
          >
            <BarChart
              height={172}
              yMax={1}
              yFmt={(v) => v.toFixed(2)}
              threshold={{ value: 0.5, label: "chance" }}
              activeLabel={active === "signal" ? activeBar : null}
              onDatumClick={(datum) => focusEvidence("signal", datum.label)}
              data={[
                { label: "Channel", value: STUDY.rowChannelAUC, warn: true },
                { label: "Journey len", value: STUDY.jlenAUC, color: CHART_TOKENS.navy },
                { label: "Chan+len", value: STUDY.jlenChAUC, color: CHART_TOKENS.navyLight },
              ]}
            />
          </ChartCard>

          <ChartCard
            title="Sensitivity stability"
            caption="Attribution share for Email across 6 label scenarios."
            tag="RQ3"
            active={active === "sensitivity"}
            onClick={() => focusEvidence("sensitivity")}
          >
            <BarChart
              height={172}
              yMax={0.3}
              yFmt={(v) => `${Math.round(v * 100)}%`}
              activeLabel={active === "sensitivity" ? activeBar : null}
              onDatumClick={(datum) => focusEvidence("sensitivity", datum.label)}
              data={[
                { label: "As-lbl", value: 0.205 },
                { label: "Final", value: 0.171 },
                { label: "Dedup", value: 0.151, dim: true },
                { label: "Drop-pre", value: 0.118, dim: true },
                { label: "Bench", value: 0.092, warn: true },
                { label: "Cons.", value: 0.071, warn: true },
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
