from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SQL_OUTPUT_DIR = PROJECT_ROOT / "data" / "sql_outputs"
OUTPUT_DIR = PROJECT_ROOT / "model" / "markov_chain" / "outputs"

CHANNELS = [
    "Direct Traffic",
    "Display Ads",
    "Email",
    "Referral",
    "Search Ads",
    "Social Media",
]


def _read_sql_output(name: str) -> pd.DataFrame:
    path = SQL_OUTPUT_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing SQL output: {path}")
    return pd.read_csv(path)


def _conversion_absorption_probability(P: pd.DataFrame) -> float:
    absorbing = ["CONVERSION", "NULL"]
    transient = [state for state in P.index if state not in absorbing]
    Q = P.loc[transient, transient].to_numpy(dtype=float)
    R = P.loc[transient, ["CONVERSION"]].to_numpy(dtype=float)
    N = np.linalg.solve(np.eye(len(transient)) - Q, R)
    return float(N[transient.index("START"), 0])


def _remove_channel(P: pd.DataFrame, channel: str) -> pd.DataFrame:
    removed = P.copy()
    outgoing = removed.loc[channel].copy()
    for state in list(removed.index):
        if state == channel:
            continue
        inbound = removed.loc[state, channel]
        if inbound != 0:
            removed.loc[state, :] = removed.loc[state, :] + inbound * outgoing
            removed.loc[state, channel] = 0
    removed = removed.drop(index=channel, columns=channel)
    removed = removed.div(removed.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    return removed


def run() -> dict[str, pd.DataFrame]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    journeys = _read_sql_output("rq13_journey_features")
    states = ["START"] + CHANNELS + ["CONVERSION", "NULL"]
    counts = pd.DataFrame(0.0, index=states, columns=states)

    for _, row in journeys.iterrows():
        channels = str(row["channel_sequence"]).split(" -> ")
        terminal = "CONVERSION" if int(row["converted_any_yes"]) == 1 else "NULL"
        path = ["START"] + channels + [terminal]
        for source, target in zip(path[:-1], path[1:]):
            counts.loc[source, target] += 1
    counts.loc["CONVERSION", "CONVERSION"] = 1
    counts.loc["NULL", "NULL"] = 1

    transition = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    baseline = _conversion_absorption_probability(transition)
    rows = []
    for channel in CHANNELS:
        without = _remove_channel(transition, channel)
        prob_without = _conversion_absorption_probability(without)
        rows.append(
            {
                "channel": channel,
                "baseline_conversion_probability": baseline,
                "probability_without_channel": prob_without,
                "removal_effect": baseline - prob_without,
            }
        )

    removal = pd.DataFrame(rows)
    positive = removal["removal_effect"].clip(lower=0)
    removal["positive_removal_effect"] = positive
    removal["markov_positive_share_pct"] = np.where(positive.sum() > 0, positive / positive.sum() * 100.0, 0.0)
    markov_share = removal[["channel", "markov_positive_share_pct", "removal_effect", "positive_removal_effect"]].copy()

    transition.round(6).to_csv(OUTPUT_DIR / "rq2_markov_transition_matrix.csv", index=True)
    removal.round(6).to_csv(OUTPUT_DIR / "rq2_markov_removal_effects.csv", index=False)
    markov_share.round(6).to_csv(OUTPUT_DIR / "rq2_markov_attribution_share.csv", index=False)
    counts.round(0).to_csv(OUTPUT_DIR / "rq2_markov_transition_counts.csv", index=True)

    return {
        "markov_transition_matrix": transition.round(6),
        "markov_removal_effects": removal.round(6),
        "markov_attribution_share": markov_share.round(6),
        "markov_transition_counts": counts.round(0),
    }


def main() -> None:
    run()
    print("Markov chain model layer complete. Inputs were SQL outputs only.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Markov model failed: {exc}", file=sys.stderr)
        raise

