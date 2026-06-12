from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATED_DIR = PROJECT_ROOT / "app" / "data" / "generated"


def _csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    df = pd.read_csv(path)
    return df.where(pd.notnull(df), None).to_dict(orient="records")


def _write_json(filename: str, payload: dict) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    (GENERATED_DIR / filename).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    sql = PROJECT_ROOT / "data" / "sql_outputs"
    analysis = PROJECT_ROOT / "analysis_python"
    model = PROJECT_ROOT / "model"

    _write_json(
        "audit-data.json",
        {
            "sql_baseline": {
                "conversion_rates": _csv(sql / "rq1_conversion_rate_base.csv"),
                "label_event_audit": _csv(sql / "rq1_label_event_audit_base.csv"),
            },
            "python_analysis": {
                "benchmark_conversion_rates": _csv(analysis / "RQ1" / "outputs" / "rq1_benchmark_conversion_rates.csv"),
                "data_validity_summary": _csv(analysis / "RQ1" / "outputs" / "rq1_data_validity_summary.csv"),
            },
        },
    )
    _write_json(
        "attribution-data.json",
        {
            "sql_baseline": {
                "attribution_baseline": _csv(sql / "rq23_attribution_baseline.csv"),
                "channel_conversion_rates": _csv(sql / "rq23_channel_conversion_rates_base.csv"),
            }
        },
    )
    _write_json(
        "model-data.json",
        {
            "logistic_regression": {
                "metrics": _csv(model / "logistic_regression" / "outputs" / "rq2_logistic_model_metrics.csv"),
                "coefficients": _csv(model / "logistic_regression" / "outputs" / "rq2_logistic_model_coefficients.csv"),
                "adjusted_share": _csv(model / "logistic_regression" / "outputs" / "rq2_logistic_adjusted_channel_share.csv"),
            },
            "markov_chain": {
                "removal_effects": _csv(model / "markov_chain" / "outputs" / "rq2_markov_removal_effects.csv"),
                "attribution_share": _csv(model / "markov_chain" / "outputs" / "rq2_markov_attribution_share.csv"),
            },
        },
    )
    _write_json(
        "sensitivity-data.json",
        {
            "rank_stability": _csv(analysis / "RQ3" / "outputs" / "rq3_sensitivity_rank_stability.csv"),
            "channel_shares": _csv(analysis / "RQ3" / "outputs" / "rq3_sensitivity_channel_shares.csv"),
        },
    )
    _write_json(
        "simulation-data.json",
        {"simulation_results": _csv(analysis / "RQ3" / "outputs" / "rq3_simulation_results.csv")},
    )
    print(f"Prepared app data JSON in {GENERATED_DIR}")


if __name__ == "__main__":
    main()
