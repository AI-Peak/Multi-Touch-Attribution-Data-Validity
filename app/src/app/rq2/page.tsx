"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { PageHead } from "@/components/primitives/PageHead";
import { Section } from "@/components/primitives/Section";
import { Callout } from "@/components/primitives/Callout";
import { Select } from "@/components/primitives/Select";
import { Tabs } from "@/components/primitives/Tabs";
import { Chip, type ChipKind } from "@/components/primitives/Chip";
import { BarChart } from "@/components/charts/BarChart";
import { HBarChart } from "@/components/charts/HBarChart";
import { GroupedBar } from "@/components/charts/GroupedBar";
import { CHART_TOKENS } from "@/components/charts/theme";
import { STUDY } from "@/lib/data/constants";

type LensId = "signal" | "fit" | "label";
type ViewId = "channel" | "logistic" | "journey" | "markov";

type EvidenceRow = readonly [string, string, string];

type LensPanel = {
  chart: ReactNode;
  table: ReadonlyArray<EvidenceRow>;
  interp: ReactNode;
  badges: ReadonlyArray<{ label: string; value: string; kind?: ChipKind }>;
};

type DiagnosticView = {
  id: ViewId;
  tab: string;
  selectLabel: string;
  panels: Record<LensId, LensPanel>;
};

const LENSES: ReadonlyArray<{ id: LensId; label: string; hint: string }> = [
  {
    id: "signal",
    label: "Signal strength",
    hint: "Predictive and association metrics",
  },
  {
    id: "fit",
    label: "Model fit",
    hint: "How much explanatory power the model adds",
  },
  {
    id: "label",
    label: "Label risk",
    hint: "Whether the conversion label behaves like a real outcome",
  },
];

function isLensId(value: string | null): value is LensId {
  return value === "signal" || value === "fit" || value === "label";
}

function isViewId(value: string | null): value is ViewId {
  return value === "channel" || value === "logistic" || value === "journey" || value === "markov";
}

const labelRiskRows: ReadonlyArray<EvidenceRow> = [
  ["Row-level Yes rate", "49.44%", "Half of rows are labelled conversion"],
  ["User any-Yes rate", "83.63%", "Most users record at least one Yes"],
  ["Multi-Yes users", "60.8%", "Repeated conversion labels within a journey"],
  ["Yes before final touch", "52.8%", "Label fires before the journey outcome"],
];

const labelRiskChart = (
  <HBarChart
    xMax={1}
    xFmt={(v) => `${Math.round(v * 100)}%`}
    data={[
      { label: "Row Yes", value: STUDY.rowYesRate, warn: true },
      { label: "User any-Yes", value: STUDY.userAnyYes, warn: true },
      { label: "Final-touch Yes", value: 0.612 },
      { label: "Multi-Yes users", value: 0.608, warn: true },
      { label: "Yes before final", value: 0.528, warn: true },
    ]}
  />
);

const labelRiskInterp = (
  <span>
    The label is saturated and often appears before the journey outcome. That
    makes row-level conversion a weak target for direct attribution.
  </span>
);

const diagnosticViews: ReadonlyArray<DiagnosticView> = [
  {
    id: "channel",
    tab: "Channel signal test",
    selectLabel: "Channel signal",
    panels: {
      signal: {
        chart: (
          <HBarChart
            xMax={1}
            xFmt={(v) => v.toFixed(3)}
            data={[
              { label: "Cramer's V", value: STUDY.cramersV, warn: true },
              { label: "Channel AUC", value: STUDY.rowChannelAUC, warn: true },
              { label: "Chance line", value: 0.5, color: CHART_TOKENS.grey },
            ]}
          />
        ),
        table: [
          ["Chi-square p-value", "0.8598", "Channel x conversion independence not rejected"],
          ["Cramer's V", "0.0139", "Effect size is near zero"],
          ["Row-channel AUC", "0.4902", "Indistinguishable from chance"],
        ],
        badges: [
          { label: "AUC", value: "0.4902", kind: "high" },
          { label: "p-value", value: "0.8598", kind: "neutral" },
          { label: "Effect size", value: "near zero", kind: "high" },
        ],
        interp: (
          <span>
            Channel identity carries essentially <b>no predictive signal</b> for
            the row-level label. The statistical test does not support channel
            dependence.
          </span>
        ),
      },
      fit: {
        chart: (
          <HBarChart
            xMax={0.3}
            xFmt={(v) => v.toFixed(4)}
            data={[
              { label: "Channel R2", value: STUDY.mcfaddenCh, warn: true },
              { label: "Journey length R2", value: STUDY.mcfaddenJlen },
            ]}
          />
        ),
        table: [
          ["Channel McFadden R2", "0.0021", "Channel explains almost nothing"],
          ["Length McFadden R2", "0.2604", "Journey length explains much more"],
          ["Fit ratio", "124x", "Length dominates channel as explanatory signal"],
        ],
        badges: [
          { label: "Channel fit", value: "0.0021", kind: "high" },
          { label: "Length fit", value: "0.2604", kind: "neutral" },
          { label: "Gap", value: "124x", kind: "high" },
        ],
        interp: (
          <span>
            Under a fit lens, channel remains inert. Journey length supplies the
            explanatory power, so channel rankings are likely confounded.
          </span>
        ),
      },
      label: {
        chart: labelRiskChart,
        table: labelRiskRows,
        badges: [
          { label: "Row Yes", value: "49.44%", kind: "high" },
          { label: "Any-Yes", value: "83.63%", kind: "high" },
          { label: "Multi-Yes", value: "60.8%", kind: "high" },
        ],
        interp: labelRiskInterp,
      },
    },
  },
  {
    id: "logistic",
    tab: "Logistic regression comparison",
    selectLabel: "Logistic comparison",
    panels: {
      signal: {
        chart: (
          <GroupedBar
            height={196}
            yMax={1}
            yFmt={(v) => v.toFixed(2)}
            groups={[
              { label: "Channel only" },
              { label: "Length only" },
              { label: "Channel + length" },
            ]}
            series={[
              { name: "AUC", color: CHART_TOKENS.navy, values: [0.4902, 0.7549, 0.7536] },
            ]}
          />
        ),
        table: [
          ["Channel-only AUC", "0.4902", "Baseline channel model at chance"],
          ["Length-only AUC", "0.7549", "Journey length is strongly predictive"],
          ["Channel + length AUC", "0.7536", "Adding channel does not improve AUC"],
        ],
        badges: [
          { label: "Channel AUC", value: "0.4902", kind: "high" },
          { label: "Length AUC", value: "0.7549", kind: "neutral" },
          { label: "Channel lift", value: "-0.0013", kind: "high" },
        ],
        interp: (
          <span>
            Adding channel to a length-only model <b>slightly reduces AUC</b>
            rather than improving it. The useful signal lives in journey length.
          </span>
        ),
      },
      fit: {
        chart: (
          <BarChart
            height={184}
            yMax={0.3}
            yFmt={(v) => v.toFixed(3)}
            data={[
              { label: "Channel", value: STUDY.mcfaddenCh, warn: true },
              { label: "Length", value: STUDY.mcfaddenJlen, color: CHART_TOKENS.navy },
              { label: "Added channel", value: 0.0013, warn: true },
            ]}
          />
        ),
        table: [
          ["Channel McFadden R2", "0.0021", "Tiny model fit"],
          ["Length McFadden R2", "0.2604", "Substantive model fit"],
          ["Incremental channel value", "~0", "No practical improvement after length"],
        ],
        badges: [
          { label: "Added value", value: "none", kind: "high" },
          { label: "Fit driver", value: "length", kind: "neutral" },
        ],
        interp: (
          <span>
            The fit view tells the same story as AUC: channel does not add a
            meaningful explanatory layer once journey length is present.
          </span>
        ),
      },
      label: {
        chart: labelRiskChart,
        table: labelRiskRows,
        badges: [
          { label: "Target issue", value: "saturated", kind: "high" },
          { label: "Outcome alignment", value: "weak", kind: "high" },
        ],
        interp: labelRiskInterp,
      },
    },
  },
  {
    id: "journey",
    tab: "Journey-length confounding",
    selectLabel: "Journey length confounding",
    panels: {
      signal: {
        chart: (
          <BarChart
            height={184}
            yMax={1}
            yFmt={(v) => v.toFixed(2)}
            threshold={{ value: 0.5, label: "chance" }}
            data={[
              { label: "Channel", value: STUDY.rowChannelAUC, warn: true },
              { label: "Journey length", value: STUDY.jlenAUC, color: CHART_TOKENS.navy },
              { label: "Combined", value: STUDY.jlenChAUC, color: CHART_TOKENS.navyLight },
            ]}
          />
        ),
        table: [
          ["Channel AUC", "0.4902", "No better than chance"],
          ["Journey-length AUC", "0.7549", "Length predicts labels strongly"],
          ["Combined AUC", "0.7536", "Channel adds no signal"],
        ],
        badges: [
          { label: "Confounder", value: "journey length", kind: "high" },
          { label: "AUC gap", value: "+0.2647", kind: "neutral" },
        ],
        interp: (
          <span>
            Longer journeys naturally contain more touches and more Yes labels.
            That can masquerade as channel performance if not separated.
          </span>
        ),
      },
      fit: {
        chart: (
          <HBarChart
            xMax={0.3}
            xFmt={(v) => v.toFixed(4)}
            data={[
              { label: "Length R2", value: STUDY.mcfaddenJlen },
              { label: "Channel R2", value: STUDY.mcfaddenCh, warn: true },
              { label: "Residual channel gain", value: 0.0013, warn: true },
            ]}
          />
        ),
        table: [
          ["Length McFadden R2", "0.2604", "Dominant explanatory variable"],
          ["Channel McFadden R2", "0.0021", "Almost no explanatory value"],
          ["Confounding pattern", "present", "Length drives touch count and labels"],
        ],
        badges: [
          { label: "Length fit", value: "dominant", kind: "neutral" },
          { label: "Channel fit", value: "minimal", kind: "high" },
        ],
        interp: (
          <span>
            Fit metrics make the confound visible: journey length absorbs the
            predictive structure that channel attribution would otherwise claim.
          </span>
        ),
      },
      label: {
        chart: labelRiskChart,
        table: labelRiskRows,
        badges: [
          { label: "Long-journey bias", value: "likely", kind: "high" },
          { label: "Repeated labels", value: "60.8%", kind: "high" },
        ],
        interp: (
          <span>
            Label repetition amplifies the length problem: longer journeys have
            more chances to collect suspect Yes events.
          </span>
        ),
      },
    },
  },
  {
    id: "markov",
    tab: "Markov removal effect",
    selectLabel: "Markov removal effect",
    panels: {
      signal: {
        chart: (
          <HBarChart
            xMax={0.08}
            xFmt={(v) => v.toFixed(3)}
            data={[
              { label: "Email", value: 0.061 },
              { label: "Search", value: 0.058 },
              { label: "Direct", value: 0.054 },
              { label: "Referral", value: 0.041 },
              { label: "Social", value: 0.033 },
              { label: "Display", value: 0.028 },
            ]}
          />
        ),
        table: [
          ["Removal-effect spread", "0.028-0.061", "Narrow band across channels"],
          ["Max / min ratio", "2.18x", "No channel dominates removal effect"],
          ["Stability Spearman", "0.43", "Ranking changes across scenarios"],
        ],
        badges: [
          { label: "Spread", value: "0.033", kind: "medium" },
          { label: "Stability", value: "0.43", kind: "medium" },
        ],
        interp: (
          <span>
            Removal effects are tightly clustered. That makes the channel order
            fragile rather than a robust budget signal.
          </span>
        ),
      },
      fit: {
        chart: (
          <HBarChart
            xMax={1}
            xFmt={(v) => v.toFixed(2)}
            data={[
              { label: "Linear stability", value: 0.77 },
              { label: "Markov stability", value: 0.43, warn: true },
              { label: "Row-weight stability", value: 0.31, warn: true },
              { label: "Last-touch stability", value: 0.09, warn: true },
            ]}
          />
        ),
        table: [
          ["Markov Spearman", "0.43", "Only moderate rank stability"],
          ["Last-touch Spearman", "0.09", "Ranking nearly collapses"],
          ["First-touch Spearman", "-0.14", "Ranking reverses under scenarios"],
        ],
        badges: [
          { label: "Markov", value: "moderate", kind: "medium" },
          { label: "Rank risk", value: "high", kind: "high" },
        ],
        interp: (
          <span>
            Even the more sophisticated method is not stable enough to support
            a channel-winner claim from this dataset.
          </span>
        ),
      },
      label: {
        chart: (
          <BarChart
            height={184}
            yMax={0.3}
            yFmt={(v) => `${Math.round(v * 100)}%`}
            data={[
              { label: "As-lbl", value: 0.205 },
              { label: "Final", value: 0.171 },
              { label: "Dedup", value: 0.151, dim: true },
              { label: "Drop-pre", value: 0.118, dim: true },
              { label: "Bench", value: 0.092, warn: true },
              { label: "Cons.", value: 0.071, warn: true },
            ]}
          />
        ),
        table: [
          ["Email share range", "7.1%-20.5%", "Share contracts under label correction"],
          ["Benchmark-calibrated share", "9.2%", "Much lower than as-labelled"],
          ["Conservative share", "7.1%", "Strong shrinkage under suspect labels"],
        ],
        badges: [
          { label: "Share swing", value: "13.4 pts", kind: "high" },
          { label: "Scenario risk", value: "high", kind: "high" },
        ],
        interp: (
          <span>
            Label corrections move attribution shares materially. The method is
            therefore sensitive to the exact label definition.
          </span>
        ),
      },
    },
  },
];

export default function RQ2Page() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [lens, setLens] = useState<LensId>(() => {
    const value = searchParams.get("lens");
    return isLensId(value) ? value : "signal";
  });
  const [viewId, setViewId] = useState<ViewId>(() => {
    const value = searchParams.get("view");
    return isViewId(value) ? value : "channel";
  });

  useEffect(() => {
    if (searchParams.get("lens") === lens && searchParams.get("view") === viewId) return;
    const next = new URLSearchParams(searchParams.toString());
    next.set("lens", lens);
    next.set("view", viewId);
    router.replace(`${pathname}?${next.toString()}` as Route, { scroll: false });
  }, [lens, pathname, router, searchParams, viewId]);

  const activeIndex = useMemo(
    () => Math.max(0, diagnosticViews.findIndex((view) => view.id === viewId)),
    [viewId],
  );
  const view = diagnosticViews[activeIndex] ?? diagnosticViews[0]!;
  const panel = view.panels[lens];
  const lensMeta = LENSES.find((item) => item.id === lens) ?? LENSES[0]!;

  return (
    <div className="page">
      <PageHead
        eyebrow="RQ2 - Model diagnostics"
        title="What evidence shows label bias, weak channel signal, or confounding?"
        desc="Statistical and model-based diagnostics testing whether channel identity carries usable predictive signal. The controls below change the evidence lens, not just the label."
      />

      <Section title="View controls">
        <div className="card card-pad control-grid">
          <Select
            label="Diagnostic lens"
            value={lens}
            onChange={(value) => setLens(value as LensId)}
            hint={lensMeta.hint}
            options={LENSES.map((item) => ({ value: item.id, label: item.label }))}
          />
          <Select
            label="Diagnostic view"
            value={viewId}
            onChange={(value) => setViewId(value as ViewId)}
            hint="This stays synced with the tab row below."
            options={diagnosticViews.map((item) => ({ value: item.id, label: item.selectLabel }))}
          />
        </div>
        <div className="share-link-hint">
          Shareable demo state: <span className="mono">/rq2?lens={lens}&amp;view={viewId}</span>
        </div>
      </Section>

      <Section title="Diagnostic tabs">
        <Tabs
          tabs={diagnosticViews.map((item) => item.tab)}
          active={activeIndex}
          onChange={(index) => setViewId(diagnosticViews[index]?.id ?? "channel")}
        />
        <div className="card" style={{ borderTopLeftRadius: 0, marginTop: 0 }}>
          <div className="diagnostic-panel">
            <div className="diagnostic-chart-pane">
              <div className="eyebrow-mono" style={{ marginBottom: 10 }}>
                {lensMeta.label} - {view.tab}
              </div>
              {panel.chart}
              <div
                className="chart-foot"
                style={{ borderTop: "none", padding: "8px 0 0" }}
              >
                <span>Source: model pipeline</span>
                <span className="tag-mini">n = 10,000</span>
              </div>
            </div>
            <div className="diagnostic-table-pane">
              <div className="evidence-badges">
                {panel.badges.map((badge) => (
                  <div className="evidence-badge" key={`${badge.label}-${badge.value}`}>
                    <span>{badge.label}</span>
                    <Chip kind={badge.kind ?? "neutral"}>{badge.value}</Chip>
                  </div>
                ))}
              </div>
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th className="r">Value</th>
                    <th>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {panel.table.map((row) => (
                    <tr key={`${view.id}-${lens}-${row[0]}`}>
                      <td>{row[0]}</td>
                      <td className="r">
                        <span className="num">{row[1]}</span>
                      </td>
                      <td>
                        <span className="muted" style={{ fontSize: 11.5 }}>
                          {row[2]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </Section>

      <div style={{ marginTop: 18 }}>
        <Callout variant="info" title={`Interpretation - ${view.tab}`}>
          <span>
            {panel.interp}{" "}
            <span style={{ color: "var(--amber)", fontWeight: 600 }}>Net:</span>{" "}
            the evidence remains diagnostic, not prescriptive; it does not
            justify a causal channel winner.
          </span>
        </Callout>
      </div>
    </div>
  );
}
