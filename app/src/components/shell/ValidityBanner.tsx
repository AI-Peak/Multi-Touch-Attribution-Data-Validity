import { IconWarn } from "@/lib/icons";

export function ValidityBanner() {
  return (
    <div className="validity-banner">
      <IconWarn size={15} className="vb-icon" />
      <span>
        <b>Validity-audit &amp; scenario-exploration tool.</b> This dashboard
        does not provide causal budget optimization.
      </span>
    </div>
  );
}
