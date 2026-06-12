import { STUDY } from "@/lib/data/constants";
import { fmtInt } from "@/lib/format";

export function DataStatusPanel() {
  const rows: Array<[string, string]> = [
    ["Files loaded", "5 / 5"],
    ["Touchpoints", fmtInt(STUDY.touchpoints)],
    ["Last refresh", STUDY.lastRefresh],
    ["Pipeline", STUDY.pipelineVersion],
  ];

  return (
    <div className="data-status">
      <div className="ds-title">
        <span className="ds-dot" aria-hidden />
        Data status
      </div>
      {rows.map(([k, v]) => (
        <div key={k} className="ds-row">
          <span className="k">{k}</span>
          <span className="v">{v}</span>
        </div>
      ))}
    </div>
  );
}
