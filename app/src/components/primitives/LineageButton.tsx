"use client";

import { useEffect, useState, type ReactNode } from "react";
import { LINEAGE, type LineageKey } from "@/lib/data/lineage";
import { IconInfo, IconX } from "@/lib/icons";

export function LineageButton({
  metricKey,
  children,
  tone = "inline",
}: {
  metricKey: LineageKey;
  children: ReactNode;
  tone?: "inline" | "button";
}) {
  const [open, setOpen] = useState(false);
  const info = LINEAGE[metricKey];

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <>
      <button
        className={tone === "button" ? "lineage-button solid" : "lineage-button"}
        onClick={() => setOpen(true)}
        title="Open metric lineage"
        type="button"
      >
        <span>{children}</span>
        <IconInfo size={13} />
      </button>
      {open ? (
        <div className="lineage-layer" role="dialog" aria-modal="true" aria-label={`${info.title} lineage`}>
          <button className="lineage-scrim" aria-label="Close lineage drawer" onClick={() => setOpen(false)} type="button" />
          <aside className="lineage-drawer">
            <div className="lineage-head">
              <div>
                <div className="eyebrow-mono">Data lineage</div>
                <h2>{info.title}</h2>
              </div>
              <button className="lineage-close" onClick={() => setOpen(false)} type="button" aria-label="Close lineage drawer">
                <IconX size={16} />
              </button>
            </div>
            <div className="lineage-sections">
              <div>
                <span>Source</span>
                <p>{info.source}</p>
              </div>
              <div>
                <span>Transform</span>
                <p>{info.transform}</p>
              </div>
              <div>
                <span>Refresh</span>
                <p>{info.refresh}</p>
              </div>
              <div className="lineage-caveat">
                <span>Caveat</span>
                <p>{info.caveat}</p>
              </div>
            </div>
          </aside>
        </div>
      ) : null}
    </>
  );
}
