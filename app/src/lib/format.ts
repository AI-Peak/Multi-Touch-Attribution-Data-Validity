/** Formatting helpers — single source of truth for number presentation. */

const EM_DASH = "—";

export function fmtInt(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return EM_DASH;
  return Math.round(value).toLocaleString("en-US");
}

export function fmtPct(
  value: number | null | undefined,
  digits: number = 2,
  alreadyPct: boolean = false,
): string {
  if (value == null || !Number.isFinite(value)) return EM_DASH;
  const pct = alreadyPct ? value : value * 100;
  return `${pct.toFixed(digits)}%`;
}

export function fmtMoney(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return EM_DASH;
  return `$${Math.round(value).toLocaleString("en-US")}`;
}

export function fmtSignedInt(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return EM_DASH;
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded.toLocaleString("en-US")}`;
}

export function fmtSignedMoney(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return EM_DASH;
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}$${Math.round(Math.abs(value)).toLocaleString("en-US")}`;
}

export function fmtFloat(
  value: number | null | undefined,
  digits: number = 4,
): string {
  if (value == null || !Number.isFinite(value)) return EM_DASH;
  return value.toFixed(digits);
}

export function normalize(weights: number[]): number[] {
  const sum = weights.reduce((a, b) => a + b, 0);
  if (sum === 0) return weights.map(() => 0);
  return weights.map((w) => w / sum);
}
