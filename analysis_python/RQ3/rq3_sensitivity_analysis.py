from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from analysis_python.common.common import CHANNELS, RANDOM_SEED, read_sql_output, write_output
else:
    from ..common.common import CHANNELS, RANDOM_SEED, read_sql_output, write_output


RQ = "RQ3/outputs"


def _baseline_scenario(attribution: pd.DataFrame, scenario: str, label: str) -> pd.DataFrame:
    frame = attribution.loc[attribution["label_scenario"].eq(scenario), ["channel", "first_touch_pct", "last_touch_pct", "linear_pct"]].copy()
    frame["scenario"] = label
    return frame[["scenario", "channel", "first_touch_pct", "last_touch_pct", "linear_pct"]]


def _scenario_labels(journeys: pd.DataFrame, target_rate: float) -> pd.Series:
    rng = np.random.default_rng(RANDOM_SEED + int(target_rate * 1000))
    positive_ids = journeys.loc[journeys["converted_any_yes"].eq(1), "user_id"].to_numpy()
    n_target = max(1, int(round(target_rate * len(journeys))))
    chosen = set(rng.choice(positive_ids, size=min(n_target, len(positive_ids)), replace=False))
    return journeys["user_id"].isin(chosen)


def _attribution_for_labels(journeys: pd.DataFrame, touchpoints: pd.DataFrame, labels: pd.Series, scenario_name: str) -> pd.DataFrame:
    user_labels = pd.Series(labels.to_numpy(dtype=bool), index=journeys["user_id"])
    positive_users = int(user_labels.sum())
    if positive_users == 0:
        return pd.DataFrame({"scenario": scenario_name, "channel": CHANNELS, "first_touch_pct": 0.0, "last_touch_pct": 0.0, "linear_pct": 0.0})

    selected_journeys = journeys[journeys["user_id"].map(user_labels).fillna(False).astype(bool)]
    selected_touchpoints = touchpoints[touchpoints["user_id"].map(user_labels).fillna(False).astype(bool)]
    first = selected_journeys["first_touch_channel"].value_counts().reindex(CHANNELS, fill_value=0) / positive_users * 100.0
    last = selected_journeys["last_touch_channel"].value_counts().reindex(CHANNELS, fill_value=0) / positive_users * 100.0
    linear_credit = selected_touchpoints.groupby("channel")["linear_weight"].sum().reindex(CHANNELS, fill_value=0.0)
    linear = linear_credit / linear_credit.sum() * 100.0 if linear_credit.sum() else linear_credit
    return pd.DataFrame(
        {
            "scenario": scenario_name,
            "channel": CHANNELS,
            "first_touch_pct": first.to_numpy(dtype=float),
            "last_touch_pct": last.to_numpy(dtype=float),
            "linear_pct": linear.to_numpy(dtype=float),
        }
    )


def _simulation(channel_rates: pd.DataFrame, any_yes_attr: pd.DataFrame) -> pd.DataFrame:
    total_budget = 100_000.0
    total_touchpoints = 10_000.0
    cost_per_touch = total_budget / total_touchpoints
    revenue_per_conversion = 100.0
    rates = channel_rates.set_index("channel")["conversion_rate_pct"].reindex(CHANNELS) / 100.0
    linear_weights = any_yes_attr.set_index("channel")["linear_pct"].reindex(CHANNELS) / 100.0
    linear_weights = linear_weights / linear_weights.sum()
    weights = {
        "S0_equal": pd.Series(1 / len(CHANNELS), index=CHANNELS),
        "S1_row_conversion_rate_weighted": rates / rates.sum(),
        "S2_current_linear_attribution_weighted": linear_weights,
    }
    rows = []
    for scenario, weight in weights.items():
        spend = total_budget * weight
        simulated_touches = spend / cost_per_touch
        conversions = float((simulated_touches * rates).sum())
        revenue = conversions * revenue_per_conversion
        rows.append({"scenario": scenario, "conversions": conversions, "revenue": revenue, "budget": total_budget, "revenue_per_conversion": revenue_per_conversion})
    result = pd.DataFrame(rows)
    base_conv = result.loc[result["scenario"].eq("S0_equal"), "conversions"].iloc[0]
    base_rev = result.loc[result["scenario"].eq("S0_equal"), "revenue"].iloc[0]
    result["delta_conversions_vs_s0"] = result["conversions"] - base_conv
    result["delta_revenue_vs_s0"] = result["revenue"] - base_rev
    result["delta_revenue_pct_vs_s0"] = (result["revenue"] - base_rev) / base_rev * 100.0
    return result.round(6)


def run() -> dict[str, pd.DataFrame]:
    journeys = read_sql_output("rq123_journey_features")
    touchpoints = read_sql_output("rq23_touchpoint_features")
    scenario_base = read_sql_output("rq3_sensitivity_base")
    attribution = read_sql_output("rq23_attribution_baseline")
    channel_rates = read_sql_output("rq23_channel_conversion_rates_base")

    any_yes = _baseline_scenario(attribution, "any_yes", "Current any-Yes label")
    last_touch = _baseline_scenario(attribution, "last_touch_yes", "Stricter final-touch Yes label")
    share_frames = [any_yes, last_touch]
    stability_rows = []

    base_linear = any_yes.set_index("channel")["linear_pct"].reindex(CHANNELS)
    for frame, target_rate in [(any_yes, np.nan), (last_touch, np.nan)]:
        linear = frame.set_index("channel")["linear_pct"].reindex(CHANNELS)
        labels = journeys["converted_any_yes"].astype(bool) if frame["scenario"].iloc[0].startswith("Current") else journeys["last_touch_yes"].astype(bool)
        stability_rows.append(
            {
                "scenario": frame["scenario"].iloc[0],
                "target_rate_pct": target_rate,
                "positive_users": int(labels.sum()),
                "positive_rate_pct": labels.mean() * 100.0,
                "spearman_linear_share_vs_current": spearmanr(base_linear, linear).correlation,
                "top_channel_linear": str(linear.sort_values(ascending=False).index[0]),
                "top_channel_linear_share_pct": float(linear.max()),
            }
        )

    for _, row in scenario_base.dropna(subset=["target_rate_pct"]).iterrows():
        target_rate = float(row["target_rate_pct"]) / 100.0
        labels = _scenario_labels(journeys, target_rate)
        frame = _attribution_for_labels(journeys, touchpoints, labels, str(row["scenario"]))
        share_frames.append(frame)
        linear = frame.set_index("channel")["linear_pct"].reindex(CHANNELS)
        stability_rows.append(
            {
                "scenario": row["scenario"],
                "target_rate_pct": float(row["target_rate_pct"]),
                "positive_users": int(labels.sum()),
                "positive_rate_pct": labels.mean() * 100.0,
                "spearman_linear_share_vs_current": spearmanr(base_linear, linear).correlation,
                "top_channel_linear": str(linear.sort_values(ascending=False).index[0]),
                "top_channel_linear_share_pct": float(linear.max()),
            }
        )

    sensitivity_shares = pd.concat(share_frames, ignore_index=True).round(6)
    stability = pd.DataFrame(stability_rows).round(6)
    simulation = _simulation(channel_rates, any_yes).round(6)

    write_output(stability, RQ, "rq3_sensitivity_rank_stability.csv")
    write_output(sensitivity_shares, RQ, "rq3_sensitivity_channel_shares.csv")
    write_output(simulation, RQ, "rq3_simulation_results.csv")
    return {
        "sensitivity_rank_stability": stability,
        "sensitivity_channel_shares": sensitivity_shares,
        "simulation_results": simulation,
    }


def main() -> None:
    run()
    print("Python sensitivity analysis complete. Inputs were SQL outputs only.")


if __name__ == "__main__":
    main()

