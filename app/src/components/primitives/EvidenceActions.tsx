"use client";

import { useMemo, useState } from "react";

export function EvidenceActions({
  copyText,
  downloadText,
  filename,
  mime = "text/plain;charset=utf-8",
}: {
  copyText: string;
  downloadText?: string;
  filename?: string;
  mime?: string;
}) {
  const [copied, setCopied] = useState(false);

  const downloadHref = useMemo(() => {
    if (!downloadText) return null;
    return `data:${mime},${encodeURIComponent(downloadText)}`;
  }, [downloadText, mime]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(copyText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="evidence-actions">
      <button type="button" onClick={copy}>
        {copied ? "Copied" : "Copy evidence"}
      </button>
      {downloadHref && filename ? (
        <a download={filename} href={downloadHref}>
          Download
        </a>
      ) : null}
    </div>
  );
}
