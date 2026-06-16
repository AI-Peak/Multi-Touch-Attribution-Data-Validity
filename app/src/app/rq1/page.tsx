"use client";

import { Suspense, useEffect, useState } from "react";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { PageHead } from "@/components/primitives/PageHead";
import { PageSkeleton } from "@/components/primitives/PageSkeleton";
import { Section } from "@/components/primitives/Section";
import { KpiCard } from "@/components/primitives/KpiCard";
import { Callout } from "@/components/primitives/Callout";
import { Chip, type ChipKind } from "@/components/primitives/Chip";
import { SliderControl } from "@/components/primitives/SliderControl";
import { LineageButton } from "@/components/primitives/LineageButton";
import { ResetSelection } from "@/components/primitives/ResetSelection";
import { BarChart } from "@/components/charts/BarChart";
import { CHART_TOKENS } from "@/components/charts/theme";
import { CrossFilterProvider, useCrossFilter } from "@/lib/crossfilter/context";
import { RQ1_LINKS } from "@/lib/crossfilter/links";
import { IconWarn } from "@/lib/icons";
import { STUDY } from "@/lib/data/constants";
import type { LineageKey } from "@/lib/data/lineage";

type SignalKey = "user" | "row" | "final";


const SIGNALS: Record<SignalKey, { label: string; rate: number; note: string }> = {
  user: {
    label: "User any-Yes",
    rate: STUDY.userAnyYes,
    note: "At least one Yes per user journey",
  },
  row: {
    label: "Row-level Yes",
    rate: STUDY.rowYesRate,
    note: "Touchpoint rows labelled Yes",
  },
  final: {
    label: "Final-touch Yes",
    rate: 0.612,
    note: "Journeys with a Yes on the final touch",
  },
};

const EVIDENCE: ReadonlyArray<{
  metric: string;
  value: string;
  detail: string;
  flag: ChipKind;
  flagLabel: string;
  lineage: LineageKey;
}> = [
  {
    metric: "Row-level Yes rate",
    value: "49.44%",
    detail: "4,944 of 10,000 touchpoint rows labelled Yes",
    flag: "high",
    flagLabel: "High",
    lineage: "row-yes-rate",
  },
  {
    metric: "Final-touch Yes rate",
    value: "61.20%",
    detail: "Share of journeys with a Yes on the final touch",
    flag: "medium",
    flagLabel: "Medium",
    lineage: "final-touch-yes",
  },
  {
    metric: "Users with multiple Yes events",
    value: "1,731 (60.8%)",
    detail: "A single user records several conversion labels",
    flag: "high",
    flagLabel: "High",
    lineage: "multi-yes-users",
  },
  {
    metric: "Users with Yes before final touch",
    value: "1,502 (52.8%)",
    detail: "Label fires mid-journey, not at outcome",
    flag: "high",
    flagLabel: "High",
    lineage: "pre-final-yes",
  },
];

function readBenchmark(params: URLSearchParams): number {
  const raw = Number.parseFloat(params.get("benchmark") ?? "3");
  if (!Number.isFinite(raw)) return 3;
  return Math.min(10, Math.max(1, raw));
}

function isSignalKey(value: string | null): value is SignalKey {
  return value === "user" || value === "row" || value === "final";
}

function RQ1Content() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const cf = useCrossFilter();
  const [bench, setBench] = useState(() => readBenchmark(searchParams));
  const [signalKey, setSignalKey] = useState<SignalKey>(() => {
    const value = searchParams.get("signal");
    return isSignalKey(value) ? value : "user";
  });

  useEffect(() => {
    const value = bench.toFixed(1);
    if (searchParams.get("benchmark") === value && searchParams.get("signal") === signalKey) return;
    const next = new URLSearchParams(searchParams.toString());
    next.set("benchmark", value);
    next.set("signal", signalKey);
    router.replace(`${pathname}?${next.toString()}` as Route, { scroll: false });
  }, [bench, pathname, router, searchParams, signalKey]);

  const selectedSignal = SIGNALS[signalKey];
  const observed = selectedSignal.rate * 100;
  const gap = observed / bench;
  const band: ChipKind = gap >= 20 ? "high" : gap >= 10 ? "medium" : "low";
  const bandLabel = band === "low" ? "Low" : band === "medium" ? "Medium" : "High";
  const formula = `${observed.toFixed(2)} / ${bench.toFixed(1)} = ${gap.toFixed(1)}x`;

  return (
    <div className="page">
      <PageHead
        eyebrow="RQ1 - Validity audit"
        title="Is the dataset valid enough for direct multi-touch attribution?"
        desc="Compare multiple conversion-label signals against a realistic e-commerce benchmark to quantify label saturation."
      />


      <Section
        title="Benchmark lab"
        note="Change the benchmark and conversion signal to see why the gap remains material"
      >
        <div className="benchmark-lab card card-pad">
          <div className="benchmark-controls">
            <div className="benchmark-presets">
              <span className="field-label">Benchmark preset</span>
              <div className="segmented">
                {[1, 3, 5, 10].map((value) => (
                  <button
                    className={Math.abs(bench - value) < 0.01 ? "active" : ""}
                    key={value}
                    onClick={() => setBench(value)}
                    type="button"
                  >
                    {value}%
                  </button>
                ))}
              </div>
            </div>
            <div className="benchmark-presets">
              <span className="field-label">Conversion signal</span>
              <div className="segmented">
                {Object.entries(SIGNALS).map(([key, signal]) => (
                  <button
                    className={signalKey === key ? "active" : ""}
                    key={key}
                    onClick={() => setSignalKey(key as SignalKey)}
                    type="button"
                  >
                    {signal.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <SliderControl
            label="Expected e-commerce conversion benchmark (%)"
            hint="Typical online retail user-level conversion sits near 2-4%."
            min={1}
            max={10}
            step={0.5}
            value={bench}
            onChange={setBench}
            fmt={(v) => `${v.toFixed(1)}%`}
            marks={[1, 3, 5, 10]}
          />

          <div className="benchmark-compare">
            <div>
              <div className="eyebrow-mono">Formula</div>
              <div className="formula-box num">{formula}</div>
              <p>
                {selectedSignal.note}. Even under a generous benchmark, the
                observed signal remains too large for direct attribution.
              </p>
            </div>
            <BarChart
              height={168}
              yMax={1}
              yFmt={(v) => `${Math.round(v * 100)}%`}
              threshold={{ value: bench / 100, label: `${bench.toFixed(1)}% benchmark` }}
              getStatus={(d) => cf.status(d.cfKey)}
              onDatumClick={(d) => { if (d.cfKey) cf.select(d.cfKey, d.label); }}
              data={[
                { label: "Benchmark", value: bench / 100, color: CHART_TOKENS.grey },
                {
                  label: selectedSignal.label,
                  value: selectedSignal.rate,
                  warn: true,
                  cfKey: signalKey === "user" ? "user-any-yes" : signalKey === "row" ? "row-yes-rate" : "final-touch-yes",
                },
              ]}
            />
          </div>

          <div className="share-link-hint">
            Shareable demo state: <span className="mono">/rq1?benchmark={bench.toFixed(1)}&amp;signal={signalKey}</span>
          </div>
        </div>
      </Section>

      <Section title="Computed results">
        <div className="grid-3">
          <KpiCard
            label={`Observed ${selectedSignal.label} rate`}
            value={`${observed.toFixed(2)}%`}
            caption="selected signal"
            active={cf.status(signalKey === "user" ? "user-any-yes" : "row-yes-rate") === "focus"}
            muted={cf.status(signalKey === "user" ? "user-any-yes" : "row-yes-rate") === "muted"}
          />
          <KpiCard
            label="Selected benchmark threshold"
            value={`${bench.toFixed(1)}%`}
            caption="slider input"
          />
          <div className={"kpi" + (band === "high" ? " warn" : "")}>
            <div className="kpi-label">
              {band === "high" ? <IconWarn size={13} /> : null}
              Gap multiplier
            </div>
            <div
              className="kpi-value num"
              style={band === "high" ? { color: "var(--amber)" } : undefined}
            >
              {gap.toFixed(1)}x
            </div>
            <div style={{ marginTop: 8 }}>
              <Chip kind={band}>{bandLabel} saturation</Chip>
            </div>
          </div>
        </div>
      </Section>

      <Section
        title="Label-validity evidence"
        note="Four checks on where and how the Yes label fires"
        right={<ResetSelection />}
      >
        <div className="card">
          <table className="tbl">
            <thead>
              <tr>
                <th>Evidence metric</th>
                <th className="r">Value</th>
                <th>Interpretation</th>
                <th className="r">Concern</th>
              </tr>
            </thead>
            <tbody>
              {EVIDENCE.map((r) => (
                <tr
                  key={r.metric}
                  className={cf.cls(r.lineage)}
                  style={{ cursor: "pointer" }}
                  onClick={() => cf.select(r.lineage, r.metric)}
                >
                  <td><LineageButton metricKey={r.lineage}>{r.metric}</LineageButton></td>
                  <td className="r"><span className="num">{r.value}</span></td>
                  <td><span className="muted" style={{ fontSize: 12 }}>{r.detail}</span></td>
                  <td className="r"><Chip kind={r.flag}>{r.flagLabel}</Chip></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <div style={{ marginTop: 18 }}>
        <Callout title="Conclusion - RQ1">
          <span>
            At a <b>{bench.toFixed(1)}%</b> benchmark, the observed{" "}
            <b>{observed.toFixed(2)}%</b> {selectedSignal.label} rate is{" "}
            <b>{gap.toFixed(1)}x</b> higher than expected. Combined with
            mid-journey and multi-Yes labelling, this indicates the conversion
            label is <b>saturated and not outcome-aligned</b>. The dataset is{" "}
            <b>not valid for direct multi-touch attribution</b>; treat it as a
            validity-audit artefact instead.
          </span>
        </Callout>
      </div>
    </div>
  );
}

export default function RQ1Page() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <CrossFilterProvider links={RQ1_LINKS}>
        <RQ1Content />
      </CrossFilterProvider>
    </Suspense>
  );
}
