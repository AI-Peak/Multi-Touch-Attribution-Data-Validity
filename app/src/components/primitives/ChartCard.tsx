import type { MouseEventHandler, ReactNode } from "react";

export function ChartCard({
  title,
  caption,
  source = "Source: model pipeline",
  tag,
  children,
  foot,
  active,
  muted,
  onClick,
}: {
  title: string;
  caption?: string;
  source?: string;
  tag?: string;
  children: ReactNode;
  foot?: ReactNode;
  active?: boolean;
  muted?: boolean;
  onClick?: MouseEventHandler<HTMLButtonElement>;
}) {
  const className =
    "chart-card" +
    (onClick ? " chart-card-button" : "") +
    (active ? " active" : "") +
    (muted ? " cross-muted" : "");

  const content = (
    <>
      <div className="chart-head">
        <div className="chart-title">{title}</div>
        {caption ? <div className="chart-caption">{caption}</div> : null}
      </div>
      <div className="chart-body">{children}</div>
      <div className="chart-foot">
        <span>{foot ?? source}</span>
        {tag ? <span className="tag-mini">{tag}</span> : null}
      </div>
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
