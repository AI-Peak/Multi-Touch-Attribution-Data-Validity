import type { ReactNode } from "react";

export function Section({
  title,
  note,
  right,
  children,
}: {
  title?: string;
  note?: string;
  right?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="section">
      {(title || right) && (
        <div className="section-head">
          <div>
            {title ? <div className="section-title">{title}</div> : null}
            {note ? <div className="section-note">{note}</div> : null}
          </div>
          {right ?? null}
        </div>
      )}
      {children}
    </div>
  );
}
