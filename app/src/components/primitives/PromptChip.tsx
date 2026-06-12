"use client";

import type { ReactNode } from "react";

export function PromptChip({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick?: () => void;
}) {
  return (
    <button className="prompt-chip" onClick={onClick} type="button">
      {children}
    </button>
  );
}
