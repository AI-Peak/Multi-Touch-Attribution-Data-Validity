"use client";

import type { CSSProperties, MouseEvent } from "react";
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

export type BarDatum = {
  label: string;
  value: number;
  warn?: boolean;
  color?: string;
  dim?: boolean;
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
}: {
  data: BarDatum[];
  height?: number;
  yMax?: number;
  yFmt?: (v: number) => string;
  threshold?: { value: number; label: string };
  baseColor?: string;
  activeLabel?: string | null;
  onDatumClick?: (datum: BarDatum, index: number) => void;
}) {
  const interactive = Boolean(onDatumClick);
  const hasActiveLabel = activeLabel != null && data.some((d) => d.label === activeLabel);

  return (
    <div
      className="chart-stage"
      style={{ "--chart-height": `${height}px` } as CSSProperties}
    >
      <ResponsiveContainer width="100%" height="100%">
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
              stroke={CHART_TOKENS.amber}
              strokeDasharray="5 4"
              strokeWidth={1.4}
              label={{
                value: threshold.label,
                position: "insideTopRight",
                fill: CHART_TOKENS.amber,
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fontWeight: 600,
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
              formatter={(v: unknown) =>
                typeof v === "number" ? yFmt(v) : String(v)
              }
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fontWeight: 600,
                fill: CHART_TOKENS.text,
              }}
            />
            {data.map((d, i) => {
              const active = activeLabel === d.label;
              const dimmed = d.dim || (hasActiveLabel && !active);
              return (
                <Cell
                  key={i}
                  cursor={interactive ? "pointer" : undefined}
                  fill={d.warn ? CHART_TOKENS.amber : d.color ?? baseColor}
                  fillOpacity={dimmed ? 0.38 : 1}
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