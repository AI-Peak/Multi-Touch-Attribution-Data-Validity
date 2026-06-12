export type Stability = "stable" | "moderate" | "unstable";

const LABELS: Record<Stability, string> = {
  stable: "Stable",
  moderate: "Moderate",
  unstable: "Unstable",
};

export function StabilityBadge({ state }: { state: Stability }) {
  return (
    <span className={"stab " + state}>
      <span className="stab-ico" />
      {LABELS[state]}
    </span>
  );
}
