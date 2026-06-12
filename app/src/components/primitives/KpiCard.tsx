import type { MouseEventHandler, ReactNode } from "react";
import { IconWarn } from "@/lib/icons";

export function KpiCard({
  label,
  value,
  caption,
  valueSmall,
  warn,
  chip,
  active,
  onClick,
}: {
  label: string;
  value: ReactNode;
  caption?: string;
  valueSmall?: boolean;
  warn?: boolean;
  chip?: ReactNode;
  active?: boolean;
  onClick?: MouseEventHandler<HTMLButtonElement>;
}) {
  const className =
    "kpi" +
    (warn ? " warn" : "") +
    (onClick ? " kpi-button" : "") +
    (active ? " active" : "");

  const content = (
    <>
      <div className="kpi-label">
        {warn ? <IconWarn size={13} /> : null}
        {label}
      </div>
      <div className={"kpi-value num" + (valueSmall ? " sm" : "")}>{value}</div>
      {caption ? <div className="kpi-caption">{caption}</div> : null}
      {chip ? <div style={{ marginTop: 8 }}>{chip}</div> : null}
    </>
  );

  if (onClick) {
    return (
      <button className={className} onClick={onClick} type="button">
        {content}
      </button>
    );
  }

  return (
    <div className={className}>
      {content}
    </div>
  );
}
