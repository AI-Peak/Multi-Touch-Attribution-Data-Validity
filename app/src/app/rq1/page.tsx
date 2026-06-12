"use client";

import { useEffect, useState } from "react";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { PageHead } from "@/components/primitives/PageHead";
import { Section } from "@/components/primitives/Section";
import { KpiCard } from "@/components/primitives/KpiCard";
import { Callout } from "@/components/primitives/Callout";
import { Chip, type ChipKind } from "@/components/primitives/Chip";
import { SliderControl } from "@/components/primitives/SliderControl";
import { Table, type TableCol } from "@/components/primitives/Table";
import { IconWarn } from "@/lib/icons";
import { STUDY } from "@/lib/data/constants";

type EvidenceRow = {
  __key: string;
  metric: React.ReactNode;
  value: React.ReactNode;
  detail: React.ReactNode;
  flag: React.ReactNode;
};

const EVIDENCE: ReadonlyArray<{
  metric: string;
  value: string;
  detail: string;
  flag: ChipKind;
  flagLabel: string;
}> = [
  {
    metric: "Row-level Yes rate",
    value: "49.44%",
    detail: "4,944 of 10,000 touchpoint rows labelled Yes",
    flag: "high",
    flagLabel: "High",
  },
  {
    metric: "Final-touch Yes rate",
    value: "61.20%",
    detail: "Share of journeys with a Yes on the final touch",
    flag: "medium",
    flagLabel: "Medium",
  },
  {
    metric: "Users with multiple Yes events",
    value: "1,731 (60.8%)",
    detail: "A single user records several “conversions”",
    flag: "high",
    flagLabel: "High",
  },
  {
    metric: "Users with Yes before final touch",
    value: "1,502 (52.8%)",
    detail: "Label fires mid-journey, not at outcome",
    flag: "high",
    flagLabel: "High",
  },
];

function readBenchmark(params: URLSearchParams): number {
  const raw = Number.parseFloat(params.get("benchmark") ?? "3");
  if (!Number.isFinite(raw)) return 3;
  return Math.min(10, Math.max(1, raw));
}

export default function RQ1Page() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [bench, setBench] = useState(() => readBenchmark(searchParams));

  useEffect(() => {
    const value = bench.toFixed(1);
    if (searchParams.get("benchmark") === value) return;
    const next = new URLSearchParams(searchParams.toString());
    next.set("benchmark", value);
    router.replace(`${pathname}?${next.toString()}` as Route, { scroll: false });
  }, [bench, pathname, router, searchParams]);

  const observed = STUDY.userAnyYes * 100;
  const gap = observed / bench;
  const band: ChipKind = gap >= 20 ? "high" : gap >= 10 ? "medium" : "low";
  const bandLabel = band === "low" ? "Low" : band === "medium" ? "Medium" : "High";

  const cols: TableCol<EvidenceRow>[] = [
    { key: "metric", label: "Evidence metric" },
    { key: "value", label: "Value", align: "r" },
    { key: "detail", label: "Interpretation" },
    { key: "flag", label: "Concern", align: "r" },
  ];

  const rows: EvidenceRow[] = EVIDENCE.map((r) => ({
    __key: r.metric,
    metric: r.metric,
    value: <span className="num">{r.value}</span>,
    detail: (
      <span className="muted" style={{ fontSize: 12 }}>
        {r.detail}
      </span>
    ),
    flag: <Chip kind={r.flag}>{r.flagLabel}</Chip>,
  }));

  return (
    <div className="page">
      <PageHead
        eyebrow="RQ1 · Validity audit"
        title="Is the dataset valid enough for direct multi-touch attribution?"
        desc="Compare the observed conversion signal against a realistic e-commerce benchmark to quantify label saturation."
      />

      <Section title="Benchmark control">
        <div className="card card-pad" style={{ maxWidth: 620 }}>
          <SliderControl
            label="Expected e-commerce conversion benchmark (%)"
            hint="Typical online retail user-level conversion sits near 2–4%."
            min={1}
            max={10}
            step={0.5}
            value={bench}
            onChange={setBench}
            fmt={(v) => `${v.toFixed(1)}%`}
            marks={[1, 3, 5, 10]}
          />
          <div className="share-link-hint">
            Shareable demo state: <span className="mono">/rq1?benchmark={bench.toFixed(1)}</span>
          </div>
        </div>
      </Section>

      <Section title="Computed results">
        <div className="grid-3">
          <KpiCard
            label="Observed user any-Yes rate"
            value={`${observed.toFixed(2)}%`}
            caption="fixed — from dataset"
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
              {gap.toFixed(1)}×
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
      >
        <div className="card">
          <Table cols={cols} rows={rows} />
        </div>
      </Section>

      <div style={{ marginTop: 18 }}>
        <Callout title="Conclusion — RQ1">
          <span>
            At a <b>{bench.toFixed(1)}%</b> benchmark, the observed{" "}
            <b>83.63%</b> user any-Yes rate is <b>{gap.toFixed(1)}×</b> higher
            than expected. Combined with mid-journey and multi-Yes labelling,
            this indicates the conversion label is{" "}
            <b>saturated and not outcome-aligned</b>. The dataset is{" "}
            <b>not valid for direct multi-touch attribution</b>; treat it as a
            validity-audit artefact instead.
          </span>
        </Callout>
      </div>
    </div>
  );
}
