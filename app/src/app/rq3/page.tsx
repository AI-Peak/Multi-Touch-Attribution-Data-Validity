"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { LayoutGroup, motion } from "framer-motion";
import { PageHead } from "@/components/primitives/PageHead";
import { PageSkeleton } from "@/components/primitives/PageSkeleton";
import { Callout } from "@/components/primitives/Callout";
import { Select } from "@/components/primitives/Select";
import { NumberInput } from "@/components/primitives/NumberInput";
import { RadioGroup } from "@/components/primitives/RadioGroup";
import { StabilityBadge } from "@/components/primitives/StabilityBadge";
import { Chip, type ChipKind } from "@/components/primitives/Chip";
import { EvidenceActions } from "@/components/primitives/EvidenceActions";
import { LineageButton } from "@/components/primitives/LineageButton";
import {
  CHANNELS,
  LABEL_SCENARIOS,
  METHODS,
  METHOD_STABILITY,
  METHOD_WEIGHTS,
  type Channel,
  type Method,
} from "@/lib/data/constants";
import {
  computeSimulation,
  type SimulatorInputs,
  type SimulatorOutputs,
} from "@/lib/simulator/compute";
import {
  fmtInt,
  fmtMoney,
  normalize,
  fmtSignedInt,
  fmtSignedMoney,
} from "@/lib/format";

type Mode = "auto" | "manual";
type CompareState = "off" | "on";

type RankCell = {
  method: Method;
  rank: number;
  weight: number;
};

type RankHeatmapRow = {
  channel: Channel;
  cells: RankCell[];
  spread: number;
};

const DEFAULT_MANUAL = [20, 10, 25, 15, 20, 10];

function isMethod(value: string | null): value is Method {
  return METHODS.includes(value as Method);
}

function isScenarioId(value: string | null): value is string {
  return LABEL_SCENARIOS.some((scenario) => scenario.id === value);
}

function readNumber(params: URLSearchParams, key: string, fallback: number): number {
  const value = Number.parseFloat(params.get(key) ?? "");
  return Number.isFinite(value) && value >= 0 ? value : fallback;
}

function readMode(value: string | null): Mode {
  return value === "manual" ? "manual" : "auto";
}

function readManual(params: URLSearchParams): number[] {
  const raw = params.get("manual");
  if (!raw) return DEFAULT_MANUAL;
  const values = raw.split(",").map((part) => Number.parseFloat(part));
  if (values.length !== CHANNELS.length || values.some((value) => !Number.isFinite(value) || value < 0)) {
    return DEFAULT_MANUAL;
  }
  return values;
}

function fmtPts(value: number) {
  const pts = value * 100;
  return `${pts > 0 ? "+" : ""}${pts.toFixed(1)} pts`;
}

function stabilityKind(score: number): ChipKind {
  if (score >= 0.7) return "low";
  if (score >= 0.3) return "medium";
  return "high";
}

function rankBand(rank: number) {
  if (rank <= 2) return "rank-top";
  if (rank <= 4) return "rank-mid";
  return "rank-low";
}

function spreadBand(spread: number) {
  if (spread >= 3) return "rank-spread-high";
  if (spread >= 2) return "rank-spread-mid";
  return "rank-spread-low";
}

function rankWeights(methodName: Method): Map<Channel, { rank: number; weight: number }> {
  const weights = normalize([...METHOD_WEIGHTS[methodName]]);
  const sorted = CHANNELS.map((channel, index) => ({
    channel,
    weight: weights[index] ?? 0,
  })).sort((a, b) => b.weight - a.weight);

  let lastWeight = Number.NaN;
  let lastRank = 1;
  return new Map(
    sorted.map((item, index) => {
      const rank = Math.abs(item.weight - lastWeight) < 0.0001 ? lastRank : index + 1;
      lastWeight = item.weight;
      lastRank = rank;
      return [item.channel, { rank, weight: item.weight }];
    }),
  );
}

function rankMap(out: SimulatorOutputs): Map<Channel, number> {
  return new Map(
    [...out.rows]
      .sort((a, b) => b.allocation - a.allocation)
      .map((row, index) => [row.channel, index + 1]),
  );
}

function RQ3Content() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [budget, setBudget] = useState(() => readNumber(searchParams, "budget", 100000));
  const [rev, setRev] = useState(() => readNumber(searchParams, "rev", 100));
  const [scenarioId, setScenarioId] = useState<string>(() =>
    isScenarioId(searchParams.get("scenario")) ? searchParams.get("scenario")! : "as-labeled",
  );
  const [method, setMethod] = useState<Method>(() => {
    const value = searchParams.get("method");
    return isMethod(value) ? value : "Markov";
  });
  const [mode, setMode] = useState<Mode>(() => readMode(searchParams.get("mode")));
  const [manual, setManual] = useState<number[]>(() => readManual(searchParams));
  const [compare, setCompare] = useState<CompareState>(() =>
    searchParams.get("compare") === "1" ? "on" : "off",
  );
  const [compareMethod, setCompareMethod] = useState<Method>(() => {
    const value = searchParams.get("compareMethod");
    return isMethod(value) ? value : "Last-touch";
  });
  const [compareScenarioId, setCompareScenarioId] = useState<string>(() =>
    isScenarioId(searchParams.get("compareScenario"))
      ? searchParams.get("compareScenario")!
      : "bench-cal",
  );

  useEffect(() => {
    const next = new URLSearchParams(searchParams.toString());
    next.set("budget", String(Math.round(budget)));
    next.set("rev", String(Math.round(rev)));
    next.set("scenario", scenarioId);
    next.set("method", method);
    next.set("mode", mode);
    next.set("manual", manual.map((value) => Math.round(value)).join(","));
    next.set("compare", compare === "on" ? "1" : "0");
    next.set("compareMethod", compareMethod);
    next.set("compareScenario", compareScenarioId);
    const nextString = next.toString();
    if (nextString === searchParams.toString()) return;
    router.replace(`${pathname}?${nextString}` as Route, { scroll: false });
  }, [budget, compare, compareMethod, compareScenarioId, manual, method, mode, pathname, rev, router, scenarioId, searchParams]);

  const inputs: SimulatorInputs = useMemo(
    () => ({
      budget,
      revenuePerConversion: rev,
      scenarioId,
      method,
      mode,
      manualShares: manual,
    }),
    [budget, rev, scenarioId, method, mode, manual],
  );

  const out = useMemo(() => computeSimulation(inputs), [inputs]);
  const compareOut = useMemo(
    () =>
      computeSimulation({
        budget,
        revenuePerConversion: rev,
        scenarioId: compareScenarioId,
        method: compareMethod,
        mode: "auto",
        manualShares: manual,
      }),
    [budget, compareMethod, compareScenarioId, manual, rev],
  );

  const sortedRows = useMemo(
    () => [...out.rows].sort((a, b) => b.allocation - a.allocation),
    [out.rows],
  );

  const comparisonRows = useMemo(() => {
    const baseRanks = rankMap(out);
    const nextRanks = rankMap(compareOut);
    return CHANNELS.map((channel) => {
      const base = out.rows.find((row) => row.channel === channel)!;
      const next = compareOut.rows.find((row) => row.channel === channel)!;
      const baseRank = baseRanks.get(channel) ?? 0;
      const compareRank = nextRanks.get(channel) ?? 0;
      return {
        channel,
        base,
        next,
        baseRank,
        compareRank,
        rankMove: baseRank - compareRank,
        shareDelta: next.weight - base.weight,
        revenueDelta: next.conversions * rev - base.conversions * rev,
      };
    }).sort((a, b) => Math.abs(b.shareDelta) - Math.abs(a.shareDelta));
  }, [compareOut, out, rev]);

  const rankHeatmapRows = useMemo<RankHeatmapRow[]>(() => {
    const ranks = new Map(METHODS.map((methodName) => [methodName, rankWeights(methodName)]));
    return CHANNELS.map((channel) => {
      const cells = METHODS.map((methodName) => {
        const cell = ranks.get(methodName)?.get(channel) ?? { rank: 0, weight: 0 };
        return { method: methodName, rank: cell.rank, weight: cell.weight };
      });
      const rankValues = cells.map((cell) => cell.rank).filter((rank) => rank > 0);
      const spread = Math.max(...rankValues) - Math.min(...rankValues);
      return { channel, cells, spread };
    }).sort((a, b) => b.spread - a.spread);
  }, []);

  const mostVolatileRank = rankHeatmapRows[0] ?? null;

  const scenario = LABEL_SCENARIOS.find((s) => s.id === scenarioId) ?? LABEL_SCENARIOS[0]!;
  const compareScenario = LABEL_SCENARIOS.find((s) => s.id === compareScenarioId) ?? LABEL_SCENARIOS[0]!;
  const fallbackMove = useMemo(
    () => ({
      channel: CHANNELS[0]!,
      shareDelta: 0,
      rankMove: 0,
      base: out.rows[0]!,
      next: compareOut.rows[0]!,
      baseRank: 1,
      compareRank: 1,
      revenueDelta: 0,
    }),
    [compareOut.rows, out.rows],
  );
  const biggestShareMove = useMemo(
    () => comparisonRows[0] ?? fallbackMove,
    [comparisonRows, fallbackMove],
  );
  const biggestRankMove = useMemo(
    () =>
      comparisonRows.reduce(
        (max, row) => (Math.abs(row.rankMove) > Math.abs(max.rankMove) ? row : max),
        comparisonRows[0] ?? fallbackMove,
      ),
    [comparisonRows, fallbackMove],
  );
  const compareEvidenceText = useMemo(
    () =>
      [
        `RQ3 compare: ${method} / ${scenario.name} vs ${compareMethod} / ${compareScenario.name}`,
        `Revenue change: ${fmtSignedMoney(compareOut.totalRevenue - out.totalRevenue)}`,
        `Conversion change: ${fmtSignedInt(compareOut.totalConversions - out.totalConversions)}`,
        `Largest share move: ${biggestShareMove.channel} ${fmtPts(biggestShareMove.shareDelta)}`,
        `Largest rank move: ${biggestRankMove.channel} ${biggestRankMove.rankMove > 0 ? "+" : ""}${biggestRankMove.rankMove}`,
      ].join("\n"),
    [biggestRankMove, biggestShareMove, compareMethod, compareOut, compareScenario.name, method, out, scenario.name],
  );
  const compareCsv = useMemo(
    () =>
      [
        "channel,current_rank,current_share,compare_rank,compare_share,rank_delta,share_delta,revenue_delta",
        ...comparisonRows.map((row) =>
          [
            row.channel,
            row.baseRank,
            (row.base.weight * 100).toFixed(2),
            row.compareRank,
            (row.next.weight * 100).toFixed(2),
            row.rankMove,
            (row.shareDelta * 100).toFixed(2),
            Math.round(row.revenueDelta),
          ].join(","),
        ),
      ].join("\n"),
    [comparisonRows],
  );

  const dClass = (v: number) =>
    v > 0.5 ? "delta-up" : v < -0.5 ? "delta-down" : "delta-flat";

  const rankClass = (v: number) => (v > 0 ? "heat-up" : v < 0 ? "heat-down" : "heat-flat");
  const activeStability = METHOD_STABILITY[method];

  return (
    <div className="page">
      <PageHead
        eyebrow="RQ3 - Interactive simulator"
        title="Given the limitations, what analysis strategy is safer?"
        desc='A what-if diagnostic. Move the inputs to see how fragile any "allocation" becomes across attribution methods and label scenarios.'
      />


      <div className="split" style={{ marginTop: 18 }}>
        <div className="card card-pad" style={{ display: "flex", flexDirection: "column", gap: 15 }}>
          <div className="eyebrow-mono">Inputs</div>
          <NumberInput
            label="Total marketing budget"
            value={budget}
            prefix="$"
            step={1000}
            min={0}
            onChange={setBudget}
          />
          <NumberInput
            label="Revenue per conversion"
            value={rev}
            prefix="$"
            step={5}
            min={0}
            onChange={setRev}
          />
          <Select
            label="Conversion label scenario"
            value={scenarioId}
            onChange={setScenarioId}
            hint={scenario.note}
            options={LABEL_SCENARIOS.map((s) => ({ value: s.id, label: s.name }))}
          />
          <Select
            label="Attribution method"
            value={method}
            onChange={(v) => setMethod(v as Method)}
            options={METHODS as unknown as readonly string[]}
          />
          <div className="field">
            <label className="field-label">Allocation mode</label>
            <RadioGroup
              value={mode}
              onChange={(v) => setMode(v)}
              options={[
                { value: "auto" as const, label: "Auto from method", sub: `Weights derived from ${method}` },
                { value: "manual" as const, label: "Manual channel sliders", sub: "Set each channel share by hand" },
              ]}
            />
          </div>
          {mode === "manual" ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 11, paddingTop: 2 }}>
              <div className="field-hint" style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Channel shares</span>
                <span className="mono">Normalized to 100%</span>
              </div>
              {CHANNELS.map((c, i) => (
                <div key={c} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ width: 88, fontSize: 11.5, color: "var(--ink-2)" }}>{c}</span>
                  <input
                    type="range"
                    className="rng"
                    style={{ flex: 1 }}
                    min={0}
                    max={40}
                    step={1}
                    value={manual[i] ?? 0}
                    onChange={(e) => {
                      const next = [...manual];
                      next[i] = Number.parseFloat(e.target.value);
                      setManual(next);
                    }}
                  />
                  <span className="mono num" style={{ width: 42, textAlign: "right", fontSize: 11.5, color: "var(--navy)" }}>
                    {((out.rows[i]?.weight ?? 0) * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          ) : null}

          <div className="divider" />
          <div className="field">
            <label className="field-label">Compare mode</label>
            <RadioGroup
              value={compare}
              onChange={setCompare}
              options={[
                { value: "on" as const, label: "Compare scenarios", sub: "Show rank/share/revenue changes" },
                { value: "off" as const, label: "Single scenario", sub: "Keep the simulator focused" },
              ]}
            />
          </div>
          {compare === "on" ? (
            <div className="compare-controls">
              <Select
                label="Compare method"
                value={compareMethod}
                onChange={(v) => setCompareMethod(v as Method)}
                options={METHODS as unknown as readonly string[]}
              />
              <Select
                label="Compare label scenario"
                value={compareScenarioId}
                onChange={setCompareScenarioId}
                hint={compareScenario.note}
                options={LABEL_SCENARIOS.map((s) => ({ value: s.id, label: s.name }))}
              />
            </div>
          ) : null}
          <div className="share-link-hint">
            Shareable demo state: <span className="mono">/rq3?method={encodeURIComponent(method)}&amp;scenario={scenarioId}&amp;compare={compare === "on" ? "1" : "0"}</span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="card">
            <div className="table-card-head">
              <span className="section-title">Budget allocation</span>
              <div className="head-actions">
                <LineageButton metricKey="attribution-allocation" tone="button">Lineage</LineageButton>
                <StabilityBadge state={out.stabilityState} />
              </div>
            </div>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Channel</th>
                  <th className="r">Weight</th>
                  <th className="r">Allocation</th>
                  <th className="r">Est. conv.</th>
                </tr>
              </thead>
              <LayoutGroup>
                <motion.tbody layout>
                  {sortedRows.map((r) => (
                    <motion.tr key={r.channel} layout transition={{ type: "tween", duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}>
                      <td>{r.channel}</td>
                      <td className="r num">{(r.weight * 100).toFixed(1)}%</td>
                      <td className="r">{fmtMoney(r.allocation)}</td>
                      <td className="r">{r.conversions.toFixed(1)}</td>
                    </motion.tr>
                  ))}
                  <tr className="row-total">
                    <td>Total</td>
                    <td className="r num">100.0%</td>
                    <td className="r">{fmtMoney(budget)}</td>
                    <td className="r">{out.totalConversions.toFixed(1)}</td>
                  </tr>
                </motion.tbody>
              </LayoutGroup>
            </table>
          </div>

          <div className="grid-2">
            <div className="bignum-card accent">
              <div className="bn-label">Estimated conversions</div>
              <div className="bn-value num">{fmtInt(out.totalConversions)}</div>
              <div className="bn-sub">scenario x{scenario.mult.toFixed(2)}</div>
            </div>
            <div className="bignum-card">
              <div className="bn-label">Estimated revenue</div>
              <div className="bn-value num">{fmtMoney(out.totalRevenue)}</div>
              <div className="bn-sub">@ {fmtMoney(rev)} / conv</div>
            </div>
          </div>

          <div className="grid-2">
            <div className="delta-card">
              <div className="d-label">Delta conversions vs. equal split</div>
              <div className={"d-value num " + dClass(out.deltaConversions)}>{fmtSignedInt(out.deltaConversions)}</div>
            </div>
            <div className="delta-card">
              <div className="d-label">Delta revenue vs. equal split</div>
              <div className={"d-value num " + dClass(out.deltaRevenue)}>{fmtSignedMoney(out.deltaRevenue)}</div>
            </div>
          </div>

          <div className="card rank-heatmap-card">
            <div className="table-card-head">
              <span className="section-title">Rank stability heatmap</span>
              <div className="head-actions">
                <LineageButton metricKey="method-weights" tone="button">Lineage</LineageButton>
                <Chip kind={stabilityKind(activeStability)}>
                  {method} score {activeStability.toFixed(2)}
                </Chip>
              </div>
            </div>
            <div className="rank-heatmap-note">
              Method columns are selectable. The spread column shows how far a channel moves across attribution assumptions.
              {mostVolatileRank ? ` Most volatile: ${mostVolatileRank.channel}.` : ""}
            </div>
            <div className="rank-heatmap-scroll">
              <table className="rank-heatmap">
                <thead>
                  <tr>
                    <th>Channel</th>
                    {METHODS.map((methodName) => (
                      <th key={methodName}>
                        <button
                          className={methodName === method ? "active" : ""}
                          onClick={() => setMethod(methodName)}
                          type="button"
                        >
                          {methodName}
                        </button>
                      </th>
                    ))}
                    <th className="r">Spread</th>
                  </tr>
                </thead>
                <tbody>
                  {rankHeatmapRows.map((row) => (
                    <tr key={row.channel}>
                      <td>{row.channel}</td>
                      {row.cells.map((cell) => (
                        <td key={cell.method}>
                          <span
                            className={[
                              "rank-cell",
                              rankBand(cell.rank),
                              cell.method === method ? "active" : "",
                              compare === "on" && cell.method === compareMethod ? "compare" : "",
                            ].filter(Boolean).join(" ")}
                          >
                            <b>#{cell.rank}</b>
                            <small>{(cell.weight * 100).toFixed(1)}%</small>
                          </span>
                        </td>
                      ))}
                      <td className="r">
                        <span className={"rank-spread " + spreadBand(row.spread)}>
                          {row.spread}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {compare === "on" ? (
            <div className="card compare-card">
              <div className="table-card-head">
                <span className="section-title">Compare mode</span>
                <div className="head-actions">
                  <Chip kind="medium">{compareMethod} / {compareScenario.name}</Chip>
                  <EvidenceActions
                    copyText={compareEvidenceText}
                    downloadText={compareCsv}
                    filename="rq3-compare.csv"
                    mime="text/csv;charset=utf-8"
                  />
                </div>
              </div>
              <div className="compare-summary">
                <div>
                  <span>Revenue change</span>
                  <b className={dClass(compareOut.totalRevenue - out.totalRevenue)}>
                    {fmtSignedMoney(compareOut.totalRevenue - out.totalRevenue)}
                  </b>
                </div>
                <div>
                  <span>Conversion change</span>
                  <b className={dClass(compareOut.totalConversions - out.totalConversions)}>
                    {fmtSignedInt(compareOut.totalConversions - out.totalConversions)}
                  </b>
                </div>
                <div>
                  <span>Largest share move</span>
                  <b>{biggestShareMove.channel}: {fmtPts(biggestShareMove.shareDelta)}</b>
                </div>
                <div>
                  <span>Largest rank move</span>
                  <b>{biggestRankMove.channel}: {biggestRankMove.rankMove > 0 ? "+" : ""}{biggestRankMove.rankMove}</b>
                </div>
              </div>
              <table className="tbl compare-table">
                <thead>
                  <tr>
                    <th>Channel</th>
                    <th className="r">Current</th>
                    <th className="r">Compare</th>
                    <th className="r">Rank</th>
                    <th className="r">Share</th>
                    <th className="r">Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonRows.map((row) => (
                    <tr key={row.channel}>
                      <td>{row.channel}</td>
                      <td className="r num">#{row.baseRank} / {(row.base.weight * 100).toFixed(1)}%</td>
                      <td className="r num">#{row.compareRank} / {(row.next.weight * 100).toFixed(1)}%</td>
                      <td className="r">
                        <span className={"heat-cell " + rankClass(row.rankMove)}>
                          {row.rankMove > 0 ? "+" : ""}{row.rankMove}
                        </span>
                      </td>
                      <td className="r">
                        <span className={"heat-cell " + rankClass(row.shareDelta)}>{fmtPts(row.shareDelta)}</span>
                      </td>
                      <td className="r">
                        <span className={"heat-cell " + rankClass(row.revenueDelta)}>{fmtSignedMoney(row.revenueDelta)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          <Callout title="What-if diagnostic - not a recommendation">
            This simulator uses precomputed evidence from a validity-questionable
            dataset. It is a what-if diagnostic tool, <b>not a causal budget recommendation</b>.
            A <b>{out.stabilityState}</b> stability reading means the ranking {out.stabilityState === "stable" ? "is comparatively robust here, but still rests on suspect labels" : "re-orders under plausible label corrections"}.
          </Callout>
        </div>
      </div>
    </div>
  );
}

export default function RQ3Page() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <RQ3Content />
    </Suspense>
  );
}
