import {
  CHANNELS,
  CH_EFF,
  METHOD_WEIGHTS,
  METHOD_STABILITY,
  LABEL_SCENARIOS,
  type Channel,
  type Method,
  type LabelScenario,
} from "@/lib/data/constants";
import { normalize } from "@/lib/format";

export type SimulatorInputs = {
  budget: number;
  revenuePerConversion: number;
  scenarioId: string;
  method: Method;
  mode: "auto" | "manual";
  manualShares: number[];
};

export type AllocationRow = {
  channel: Channel;
  weight: number;
  allocation: number;
  conversions: number;
};

export type SimulatorOutputs = {
  rows: AllocationRow[];
  totalConversions: number;
  totalRevenue: number;
  deltaConversions: number;
  deltaRevenue: number;
  stabilityScore: number;
  stabilityState: "stable" | "moderate" | "unstable";
  scenario: LabelScenario;
};

export function computeSimulation(inputs: SimulatorInputs): SimulatorOutputs {
  const scenario =
    LABEL_SCENARIOS.find((s) => s.id === inputs.scenarioId) ?? LABEL_SCENARIOS[0]!;
  const mult = scenario.mult;

  const rawWeights =
    inputs.mode === "auto"
      ? [...METHOD_WEIGHTS[inputs.method]]
      : [...inputs.manualShares];
  const weights = normalize(rawWeights);

  const safeBudget = inputs.budget > 0 ? inputs.budget : 0;
  const safeRev = inputs.revenuePerConversion > 0 ? inputs.revenuePerConversion : 0;

  const rows: AllocationRow[] = CHANNELS.map((ch, i) => {
    const w = weights[i] ?? 0;
    const alloc = safeBudget * w;
    const eff = CH_EFF[i] ?? 0;
    const conversions = (safeBudget * w) / 1000 * eff * mult;
    return { channel: ch, weight: w, allocation: alloc, conversions };
  });

  const totalConversions = rows.reduce((a, r) => a + r.conversions, 0);
  const totalRevenue = totalConversions * safeRev;

  const eqW = normalize(CHANNELS.map(() => 1));
  const eqConv = CHANNELS.reduce(
    (a, _c, i) => a + (safeBudget * (eqW[i] ?? 0)) / 1000 * (CH_EFF[i] ?? 0) * mult,
    0,
  );
  const eqRev = eqConv * safeRev;

  let stabilityScore: number;
  if (inputs.mode === "auto") {
    stabilityScore = METHOD_STABILITY[inputs.method];
  } else {
    const spread = Math.max(...weights) - Math.min(...weights);
    stabilityScore = Math.max(-0.2, 1 - spread * 4.2);
  }
  const stabilityState =
    stabilityScore >= 0.7
      ? "stable"
      : stabilityScore >= 0.3
        ? "moderate"
        : "unstable";

  return {
    rows,
    totalConversions,
    totalRevenue,
    deltaConversions: totalConversions - eqConv,
    deltaRevenue: totalRevenue - eqRev,
    stabilityScore,
    stabilityState,
    scenario,
  };
}
