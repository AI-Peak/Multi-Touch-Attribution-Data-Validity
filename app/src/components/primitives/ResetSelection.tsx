"use client";

import { useCrossFilter } from "@/lib/crossfilter/context";
import { IconX } from "@/lib/icons";

export function ResetSelection() {
  const { isActive, selectedLabel, clear } = useCrossFilter();
  if (!isActive) return null;
  return (
    <button className="cf-reset" onClick={clear} type="button" aria-label="Clear filter">
      <span className="cf-reset-dot" />
      <span className="cf-reset-text">
        <span className="cf-reset-eyebrow">Filtering</span>
        <span className="cf-reset-label">{selectedLabel ?? "Selection"}</span>
      </span>
      <span className="cf-reset-clear">
        <IconX size={11} />
        Clear
      </span>
    </button>
  );
}
