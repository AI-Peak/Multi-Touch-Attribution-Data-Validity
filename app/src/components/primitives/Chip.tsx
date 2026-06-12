import type { ReactNode } from "react";

export type ChipKind = "low" | "medium" | "high" | "neutral";

export function Chip({
  kind = "neutral",
  children,
}: {
  kind?: ChipKind;
  children: ReactNode;
}) {
  return (
    <span className={"chip " + kind}>
      <span className="chip-dot" />
      {children}
    </span>
  );
}
