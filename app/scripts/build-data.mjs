#!/usr/bin/env node
/**
 * build-data.mjs
 * Reads the 5 generated JSON files at app/data/generated/,
 * sanitizes NaN tokens, slims oversized blobs (audit metric rows),
 * and emits typed derived JSON at src/lib/data/__derived__/.
 *
 * This runs at `npm run build` (prebuild script) and on demand:
 *   npm run prepare-data
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const APP_DIR = resolve(__dirname, "..");
const SRC = join(APP_DIR, "data", "generated");
const DST = join(APP_DIR, "src", "lib", "data", "__derived__");

function readSanitized(name) {
  const raw = readFileSync(join(SRC, name), "utf8");
  // JSON.parse rejects bare NaN — replace with null.
  const cleaned = raw.replace(/\bNaN\b/g, "null");
  return JSON.parse(cleaned);
}

function dedupeByMetric(rows) {
  const seen = new Map();
  for (const r of rows ?? []) {
    if (r && typeof r.metric === "string" && !seen.has(r.metric)) {
      seen.set(r.metric, r);
    }
  }
  return [...seen.values()];
}

function ensureDir(p) {
  if (!existsSync(p)) mkdirSync(p, { recursive: true });
}

function writeDerived(filename, data) {
  ensureDir(DST);
  writeFileSync(join(DST, filename), JSON.stringify(data, null, 2), "utf8");
  return data;
}

function main() {
  const audit = readSanitized("audit-data.json");
  const attribution = readSanitized("attribution-data.json");
  const model = readSanitized("model-data.json");
  const sensitivity = readSanitized("sensitivity-data.json");
  const simulation = readSanitized("simulation-data.json");

  // Slim audit: dedupe metric rows. Keeps ~17 entries instead of 22861.
  const auditSlim = {
    conversion_rates: dedupeByMetric(audit?.sql_baseline?.conversion_rates),
    label_event_audit: audit?.sql_baseline?.label_event_audit ?? [],
    benchmark_conversion_rates:
      audit?.python_analysis?.benchmark_conversion_rates ?? [],
    data_validity_summary: dedupeByMetric(
      audit?.python_analysis?.data_validity_summary,
    ),
  };

  // Flatten the nested model + attribution shapes so consumers see one level.
  const attributionSlim = {
    attribution_baseline: attribution?.sql_baseline?.attribution_baseline ?? [],
    channel_conversion_rates:
      attribution?.sql_baseline?.channel_conversion_rates ?? [],
  };

  const modelSlim = {
    logistic_metrics: model?.logistic_regression?.metrics ?? [],
    logistic_coefficients: model?.logistic_regression?.coefficients ?? [],
    logistic_adjusted_share: model?.logistic_regression?.adjusted_share ?? [],
    markov_removal_effects: model?.markov_chain?.removal_effects ?? [],
    markov_attribution_share: model?.markov_chain?.attribution_share ?? [],
  };

  writeDerived("audit.json", auditSlim);
  writeDerived("attribution.json", attributionSlim);
  writeDerived("model.json", modelSlim);
  writeDerived("sensitivity.json", sensitivity);
  writeDerived("simulation.json", simulation);

  const reports = [
    ["audit.json", auditSlim.conversion_rates.length, "metric rows"],
    ["attribution.json", attributionSlim.attribution_baseline.length, "rows"],
    ["model.json", modelSlim.logistic_metrics.length, "logistic models"],
    ["sensitivity.json", sensitivity.rank_stability?.length ?? 0, "scenarios"],
    ["simulation.json", simulation.simulation_results?.length ?? 0, "rows"],
  ];
  console.log("derived data written:");
  for (const [name, n, unit] of reports) console.log(`  ${name} — ${n} ${unit}`);
}

main();
