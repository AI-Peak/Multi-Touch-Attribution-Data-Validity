from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import chi2_contingency, spearmanr

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from analysis_python.common.common import CHANNELS, read_sql_output, write_output
else:
    from ..common.common import CHANNELS, read_sql_output, write_output


RQ = "RQ2/outputs"


def _scenario_attribution(attribution: pd.DataFrame, scenario: str) -> pd.DataFrame:
    return (
        attribution.loc[attribution["label_scenario"].eq(scenario), ["channel", "first_touch_pct", "last_touch_pct", "linear_pct"]]
        .set_index("channel")
        .reindex(CHANNELS)
        .reset_index()
    )


def run() -> dict[str, pd.DataFrame]:
    touchpoints = read_sql_output("rq123_touchpoint_features")
    channel_rates = read_sql_output("rq2_channel_conversion_rates_base").rename(columns={"channel": "Channel"})
    attribution = read_sql_output("rq2_attribution_baseline")

    contingency = pd.crosstab(touchpoints["channel"], touchpoints["is_conversion"])
    chi2, p_value, dof, _ = chi2_contingency(contingency)
    n = contingency.to_numpy().sum()
    cramers_v = math.sqrt(chi2 / (n * (min(contingency.shape) - 1)))
    signal_tests = pd.DataFrame(
        [
            {
                "test": "channel_by_row_conversion",
                "chi_square": chi2,
                "p_value": p_value,
                "degrees_of_freedom": dof,
                "cramers_v": cramers_v,
                "interpretation": "High p-value and tiny Cramer's V indicate weak row-level channel-conversion association.",
            }
        ]
    ).round(6)

    any_yes = _scenario_attribution(attribution, "any_yes").round(4)
    last_touch_yes = _scenario_attribution(attribution, "last_touch_yes").round(4)

    method_rank_rows = []
    for scenario, frame in [("any_yes", any_yes), ("last_touch_yes", last_touch_yes)]:
        first_rank = frame.set_index("channel")["first_touch_pct"].rank(ascending=False)
        last_rank = frame.set_index("channel")["last_touch_pct"].rank(ascending=False)
        linear_rank = frame.set_index("channel")["linear_pct"].rank(ascending=False)
        method_rank_rows.extend(
            [
                {"label_scenario": scenario, "comparison": "first_vs_last", "spearman_rho": spearmanr(first_rank, last_rank).correlation},
                {"label_scenario": scenario, "comparison": "first_vs_linear", "spearman_rho": spearmanr(first_rank, linear_rank).correlation},
                {"label_scenario": scenario, "comparison": "last_vs_linear", "spearman_rho": spearmanr(last_rank, linear_rank).correlation},
            ]
        )
    ranking_stability = pd.DataFrame(method_rank_rows).round(6)

    write_output(channel_rates.round(4), RQ, "rq2_channel_conversion_rates.csv")
    write_output(signal_tests, RQ, "rq2_channel_signal_tests.csv")
    write_output(any_yes, RQ, "rq2_attribution_shares_any_yes.csv")
    write_output(last_touch_yes, RQ, "rq2_attribution_shares_last_touch_yes.csv")
    write_output(ranking_stability, RQ, "rq2_ranking_stability.csv")

    return {
        "channel_conversion_rates": channel_rates.round(4),
        "channel_signal_tests": signal_tests,
        "attribution_shares_any_yes": any_yes,
        "attribution_shares_last_touch_yes": last_touch_yes,
        "ranking_stability": ranking_stability,
    }


def main() -> None:
    run()
    print("Python signal diagnosis complete. Baseline attribution came from SQL outputs.")


if __name__ == "__main__":
    main()

