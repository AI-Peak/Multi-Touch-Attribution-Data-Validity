"use client";

import type { CSSProperties, MouseEvent } from "react";
import {
  BarChart as RBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
  LabelList,
  Tooltip,
  Cell,
} from "recharts";
import { CHART_TOKENS } from "./theme";
import { ChartTooltip } from "./Tooltip";

export type GroupedBarGroup = { label: string };

export function GroupedBar({
  groups,
  series,
  height = 200,
  yMax,
  yFmt = (v) => String(v),
  activeLabel,
  onGroupClick,
}: {
  groups: GroupedBarGroup[];
  series: { name: string; color: string; values: number[] }[];
  height?: number;
  yMax?: number;
  yFmt?: (v: number) => string;
  activeLabel?: string | null;
  onGroupClick?: (group: GroupedBarGroup, index: number) => void;
}) {
  const data = groups.map((g, gi) => {
    const row: Record<string, string | number> = { label: g.label };
    for (const s of series) row[s.name] = s.values[gi] ?? 0;
    return row;
  });
  const interactive = Boolean(onGroupClick);
  const hasActiveLabel = activeLabel != null && groups.some((g) => g.label === activeLabel);

  return (
    <div
      className="chart-stage"
      style={{ "--chart-height": `${height}px` } as CSSProperties}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RBarChart
          data={data}
          margin={{ top: 18, right: 14, bottom: 6, left: 6 }}
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
          <Legend
            wrapperStyle={{
              fontFamily: "var(--font-sans)",
              fontSize: 11,
              color: CHART_TOKENS.text,
            }}
            iconType="square"
            iconSize={10}
          />
          {!interactive ? (
            <Tooltip
              cursor={{ fill: "rgba(30, 58, 95, 0.06)" }}
              content={<ChartTooltip formatter={yFmt} />}
            />
          ) : null}
          {series.map((s) => (
            <Bar
              key={s.name}
              dataKey={s.name}
              fill={s.color}
              radius={[2, 2, 0, 0]}
              isAnimationActive={false}
              maxBarSize={48}
            >
              <LabelList
                dataKey={s.name}
                position="top"
                formatter={(v: unknown) =>
                  typeof v === "number" ? yFmt(v) : String(v)
                }
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 9,
                  fontWeight: 600,
                  fill: s.color,
                }}
              />
              {groups.map((g, index) => {
                const active = activeLabel === g.label;
                const dimmed = hasActiveLabel && !active;
                return (
                  <Cell
                    key={`${s.name}-${g.label}`}
                    cursor={interactive ? "pointer" : undefined}
                    fill={s.color}
                    fillOpacity={dimmed ? 0.38 : 1}
                    onClick={
                      onGroupClick
                        ? (event: MouseEvent<SVGElement>) => {
                            event.stopPropagation();
                            onGroupClick(g, index);
                          }
                        : undefined
                    }
                  />
                );
              })}
            </Bar>
          ))}
        </RBarChart>
      </ResponsiveContainer>
    </div>
  );
}