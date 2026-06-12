/**
 * Typed loaders for the derived JSON files produced by scripts/build-data.mjs.
 * Validates at module load — a malformed file fails the build, not runtime.
 */
import auditJson from "./__derived__/audit.json";
import attributionJson from "./__derived__/attribution.json";
import modelJson from "./__derived__/model.json";
import sensitivityJson from "./__derived__/sensitivity.json";
import simulationJson from "./__derived__/simulation.json";

import {
  AuditSchema,
  AttributionSchema,
  ModelSchema,
  SensitivitySchema,
  SimulationSchema,
  type AuditData,
  type AttributionData,
  type ModelData,
  type SensitivityData,
  type SimulationData,
} from "./schemas";

export const auditData: AuditData = AuditSchema.parse(auditJson);
export const attributionData: AttributionData =
  AttributionSchema.parse(attributionJson);
export const modelData: ModelData = ModelSchema.parse(modelJson);
export const sensitivityData: SensitivityData =
  SensitivitySchema.parse(sensitivityJson);
export const simulationData: SimulationData =
  SimulationSchema.parse(simulationJson);

/** Helper: look up a metric's value by name, returning null if missing. */
export function getMetric(
  rows: AuditData["conversion_rates"],
  name: string,
): number | null {
  return rows.find((r) => r.metric === name)?.value ?? null;
}
