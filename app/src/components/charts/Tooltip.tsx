"use client";

import type { TooltipProps } from "recharts";

export function ChartTooltip<TValue extends number | string, TName extends string>({
  active,
  payload,
  label,
  formatter,
}: TooltipProps<TValue, TName> & {
  formatter?: (v: number) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--line-strong)",
        borderRadius: 4,
        padding: "6px 9px",
        boxShadow: "var(--shadow-card)",
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        color: "var(--ink)",
      }}
    >
      {label ? (
        <div style={{ color: "var(--ink-3)", marginBottom: 3 }}>{label}</div>
      ) : null}
      {payload.map((p, i) => {
        const v = p.value;
        const text =
          typeof v === "number"
            ? formatter
              ? formatter(v)
              : v.toString()
            : String(v ?? "");
        return (
          <div key={i} style={{ color: p.color ?? "var(--ink)" }}>
            {text}
          </div>
        );
      })}
    </div>
  );
}
