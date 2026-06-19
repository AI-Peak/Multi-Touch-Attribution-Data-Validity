"use client";

import type { CSSProperties, MouseEvent } from "react";
import { useMemo, useState } from "react";
import {
  BarChart as RBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  LabelList,
  Tooltip,
} from "recharts";
import { CHART_TOKENS } from "./theme";
import { ChartTooltip } from "./Tooltip";
import type { CFStatus } from "@/lib/crossfilter/context";

export type BarDatum = {
  label: string;
  value: number;
  warn?: boolean;
  color?: string;
  dim?: boolean;
  cfKey?: string;
};

export function BarChart({
  data,
  height = 180,
  yMax,
  yFmt = (v) => String(v),
  threshold,
  baseColor = CHART_TOKENS.navy,
  activeLabel,
  onDatumClick,
  getStatus,
  xAxisPadding,
}: {
  data: BarDatum[];
  height?: number;
  yMax?: number;
  yFmt?: (v: number) => string;
  threshold?: {
    value: number;
    label: string;
    color?: string;
    labelPosition?: "start" | "end";
  };
  baseColor?: string;
  activeLabel?: string | null;
  onDatumClick?: (datum: BarDatum, index: number) => void;
  getStatus?: (datum: BarDatum, index: number) => CFStatus;
  xAxisPadding?: { left?: number; right?: number };
}) {
  const [containerWidth, setContainerWidth] = useState(0);
  const interactive = Boolean(onDatumClick);
  const hasActiveLabel = activeLabel != null && data.some((d) => d.label === activeLabel);
  // Cross-filter: only mute non-matching bars when THIS chart has a focused bar.
  // Otherwise an unrelated selection (e.g. dataset scope) would grey out every chart.
  const cfStatuses: CFStatus[] = data.map((d, i) => (getStatus ? getStatus(d, i) : "idle"));
  const anyChartFocus = cfStatuses.some((s) => s === "focus");
  const resolvedXAxisPadding = useMemo(() => {
    if (!xAxisPadding) return undefined;
    const responsiveCap = containerWidth > 0 ? Math.round(containerWidth * 0.11) : 0;
    const resolve = (value = 0) => Math.min(value, responsiveCap || value);
    return {
      left: resolve(xAxisPadding.left),
      right: resolve(xAxisPadding.right),
    };
  }, [containerWidth, xAxisPadding]);
  const thresholdColor = threshold?.color ?? CHART_TOKENS.amber;

  return (
    <div
      className="chart-stage"
      style={{ "--chart-height": `${height}px` } as CSSProperties}
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
        onResize={(width) => setContainerWidth(width)}
      >
        <RBarChart
          data={data}
          margin={{ top: 18, right: 14, bottom: 22, left: 6 }}
        >
          <CartesianGrid
            vertical={false}
            stroke={CHART_TOKENS.gridline}
            strokeWidth={1}
          />
          <XAxis
            dataKey="label"
            padding={resolvedXAxisPadding}
            axisLine={{ stroke: CHART_TOKENS.gridline }}
            tickLine={false}
            tick={{
              fontFamily: "var(--font-sans)",
              fontSize: 10,
              fill: CHART_TOKENS.axisLabel,
            }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            domain={yMax != null ? [0, yMax] : ["auto", "auto"]}
            tickFormatter={yFmt}
            tick={{
              fontFamily: "var(--font-mono)",
              fontSize: 9.5,
              fill: CHART_TOKENS.axis,
            }}
            width={44}
          />
          {!interactive ? (
            <Tooltip
              cursor={{ fill: "rgba(30, 58, 95, 0.06)" }}
              content={<ChartTooltip formatter={yFmt} />}
            />
          ) : null}
          {threshold ? (
            <ReferenceLine
              y={threshold.value}
              stroke={thresholdColor}
              strokeDasharray="5 4"
              strokeWidth={1.4}
              label={(props: { viewBox?: { x: number; y: number; width: number; height: number } }) => {
                const vb = props.viewBox;
                if (!vb) return <g />;
                const labelPosition = threshold.labelPosition ?? "end";
                const x = labelPosition === "start" ? vb.x + 8 : vb.x + vb.width - 6;
                const y = Math.max(12, vb.y - 8);
                return (
                  <text
                    x={x}
                    y={y}
                    textAnchor={labelPosition === "start" ? "start" : "end"}
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 10,
                      fontWeight: 600,
                      fill: thresholdColor,
                    }}
                  >
                    {threshold.label}
                  </text>
                );
              }}
            />
          ) : null}
          <Bar
            dataKey="value"
            radius={[2, 2, 0, 0]}
            maxBarSize={64}
            isAnimationActive={false}
          >
            <LabelList
              dataKey="value"
              position="top"
              offset={9}
              formatter={(v: unknown) =>
                typeof v === "number" ? yFmt(v) : String(v)
              }
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fontWeight: 600,
                fill: CHART_TOKENS.text,
                stroke: "none",
              }}
            />
            {data.map((d, i) => {
              const active = activeLabel === d.label;
              // PowerBI-style: ghost the non-selected bars only when THIS chart has a selection.
              const cfDim = anyChartFocus && cfStatuses[i] !== "focus";
              const dimmed = d.dim || (hasActiveLabel && !active) || cfDim;
              return (
                <Cell
                  key={i}
                  cursor={interactive ? "pointer" : undefined}
                  fill={d.warn ? CHART_TOKENS.amber : d.color ?? baseColor}
                  fillOpacity={dimmed ? 0.32 : 1}
                  style={{ transition: "fill-opacity .16s" }}
                  onClick={
                    onDatumClick
                      ? (event: MouseEvent<SVGElement>) => {
                          event.stopPropagation();
                          onDatumClick(d, i);
                        }
                      : undefined
                  }
                />
              );
            })}
          </Bar>
        </RBarChart>
      </ResponsiveContainer>
    </div>
  );
}
