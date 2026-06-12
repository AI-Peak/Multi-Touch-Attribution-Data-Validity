"use client";

import type { CSSProperties } from "react";
import {
  BarChart as RBarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
  LabelList,
  Tooltip,
} from "recharts";
import { CHART_TOKENS } from "./theme";
import { ChartTooltip } from "./Tooltip";

export type HBarDatum = {
  label: string;
  value: number;
  warn?: boolean;
  color?: string;
};

export function HBarChart({
  data,
  height,
  xFmt = (v) => String(v),
  xMax,
  baseColor = CHART_TOKENS.navy,
  labelWidth = 96,
}: {
  data: HBarDatum[];
  height?: number;
  xFmt?: (v: number) => string;
  xMax?: number;
  baseColor?: string;
  labelWidth?: number;
}) {
  const h = height ?? data.length * 28 + 12;
  return (
    <div
      className="chart-stage"
      style={{ "--chart-height": `${h}px` } as CSSProperties}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RBarChart
          layout="vertical"
          data={data}
          margin={{ top: 6, right: 44, bottom: 6, left: 8 }}
        >
          <CartesianGrid
            horizontal={false}
            stroke={CHART_TOKENS.gridline}
            strokeWidth={1}
          />
          <XAxis
            type="number"
            hide
            domain={xMax != null ? [0, xMax] : ["auto", "auto"]}
          />
          <YAxis
            type="category"
            dataKey="label"
            axisLine={false}
            tickLine={false}
            width={labelWidth}
            tick={{
              fontFamily: "var(--font-sans)",
              fontSize: 11,
              fill: CHART_TOKENS.axisLabel,
            }}
          />
          <Tooltip
            cursor={{ fill: "rgba(30, 58, 95, 0.06)" }}
            content={<ChartTooltip formatter={xFmt} />}
          />
          <Bar
            dataKey="value"
            radius={[2, 2, 2, 2]}
            isAnimationActive={false}
            barSize={14}
          >
            <LabelList
              dataKey="value"
              position="right"
              formatter={(v: unknown) =>
                typeof v === "number" ? xFmt(v) : String(v)
              }
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fontWeight: 600,
                fill: CHART_TOKENS.text,
              }}
            />
            {data.map((d, i) => (
              <Cell
                key={i}
                fill={d.warn ? CHART_TOKENS.amber : d.color ?? baseColor}
              />
            ))}
          </Bar>
        </RBarChart>
      </ResponsiveContainer>
    </div>
  );
}
