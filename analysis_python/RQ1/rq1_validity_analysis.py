from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from analysis_python.common.common import BENCHMARK_ROWS, read_sql_output, write_output
else:
    from ..common.common import BENCHMARK_ROWS, read_sql_output, write_output


RQ = "RQ1/outputs"


def run() -> dict[str, pd.DataFrame]:
    conversion = read_sql_output("rq1_conversion_rate_base")
    date_coverage = read_sql_output("rq1_date_coverage_base")
    label_audit = read_sql_output("rq1_label_event_audit_base")
    yes_distribution = read_sql_output("rq1_yes_event_distribution_base")
    journeys = read_sql_output("rq13_journey_features")

    summary = conversion.copy()
    summary["value"] = summary["value"].astype(object)
    date_row = date_coverage.iloc[0]
    summary.loc[summary["metric"].eq("date_start"), "value"] = date_row["date_start"]
    summary.loc[summary["metric"].eq("date_end"), "value"] = date_row["date_end"]

    metric_values = summary.set_index("metric")["value"]
    row_yes_rate = float(metric_values.loc["row_yes_rate_pct"])
    user_any_rate = float(metric_values.loc["user_any_yes_rate_pct"])
    user_last_rate = float(metric_values.loc["user_last_touch_yes_rate_pct"])

    observed = pd.DataFrame(
        [
            {
                "source": "Case-study raw touchpoint data",
                "period": "2025-02-10 to 2025-02-11",
                "rate_pct": row_yes_rate,
                "denominator": "Yes touchpoints / all touchpoints",
                "url": "data/sql_outputs/rq23_touchpoint_features.csv",
                "note": "SQL row-level label prevalence; not an e-commerce session purchase rate.",
            },
            {
                "source": "Case-study reconstructed user journeys",
                "period": "2025-02-10 to 2025-02-11",
                "rate_pct": user_any_rate,
                "denominator": "users with any Yes touchpoint / users",
                "url": "data/sql_outputs/rq13_journey_features.csv",
                "note": "Inflated by the SQL any-Yes label rule and not directly comparable to session-level e-commerce benchmarks.",
            },
            {
                "source": "Case-study stricter journey label",
                "period": "2025-02-10 to 2025-02-11",
                "rate_pct": user_last_rate,
                "denominator": "users whose final touchpoint is Yes / users",
                "url": "data/sql_outputs/rq13_journey_features.csv",
                "note": "A stricter SQL-generated internal alternative, still much higher than external e-commerce purchase benchmarks.",
            },
        ]
    )
    benchmark = pd.concat([pd.DataFrame(BENCHMARK_ROWS), observed], ignore_index=True)

    length_by_label = (
        journeys.groupby("converted_any_yes")["n_touchpoints"]
        .describe()
        .reset_index()
        .rename(columns={"converted_any_yes": "converted_any_yes"})
    )

    write_output(summary, RQ, "rq1_data_validity_summary.csv")
    write_output(label_audit, RQ, "rq1_label_event_audit.csv")
    write_output(yes_distribution, RQ, "rq1_yes_event_distribution.csv")
    write_output(length_by_label, RQ, "rq1_journey_length_by_label.csv")
    write_output(benchmark, RQ, "rq1_benchmark_conversion_rates.csv")

    return {
        "data_validity_summary": summary,
        "label_event_audit": label_audit,
        "yes_event_distribution": yes_distribution,
        "journey_length_by_label": length_by_label,
        "benchmark_conversion_rates": benchmark,
    }


def main() -> None:
    run()
    print("Python validity analysis complete. Inputs were SQL outputs only.")


if __name__ == "__main__":
    main()
