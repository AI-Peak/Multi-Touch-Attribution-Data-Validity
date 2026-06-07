from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from analysis_python.common.common import ANALYSIS_OUTPUT_DIR, ANALYSIS_OUTPUT_DIR
else:
    from .common import ANALYSIS_OUTPUT_DIR, ANALYSIS_OUTPUT_DIR


STYLE = {
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#30343B",
    "axes.labelcolor": "#20242B",
    "xtick.color": "#20242B",
    "ytick.color": "#20242B",
    "font.size": 10,
}


def _read(rq: str, filename: str) -> pd.DataFrame:
    return pd.read_csv(ANALYSIS_OUTPUT_DIR / rq / filename)


def _save(fig: plt.Figure, rq: str, filename: str) -> None:
    target_dir = ANALYSIS_OUTPUT_DIR / rq
    target_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(target_dir / filename, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_conversion_gap() -> None:
    rows = _read("RQ1/outputs", "rq1_benchmark_conversion_rates.csv")
    rows = rows[rows["source"].str.contains("Case-study|IRP|Shopify", case=False, regex=True)].copy()
    rows["label"] = rows["source"].replace(
        {
            "Case-study raw touchpoint data": "Dataset row Yes rate",
            "Case-study reconstructed user journeys": "Dataset user any-Yes rate",
            "Case-study stricter journey label": "Dataset final-touch Yes rate",
            "IRP Commerce Market Data": "IRP benchmark",
            "Shopify retail conversion benchmark summary": "Shopify benchmark",
        }
    )
    rows = rows.sort_values("rate_pct")
    colors = ["#5B7C99" if value < 10 else "#C94C4C" for value in rows["rate_pct"]]
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        ax.barh(rows["label"], rows["rate_pct"], color=colors)
        ax.set_xlabel("Conversion rate (%)")
        ax.set_title("Observed Conversion Labels Are Far Above External Benchmarks")
        ax.grid(axis="x", color="#E1E5EA", linewidth=0.8)
        ax.set_xlim(0, max(rows["rate_pct"].max() * 1.12, 5))
        for i, value in enumerate(rows["rate_pct"]):
            ax.text(value + 1.0, i, f"{value:.2f}%", va="center", fontsize=9)
    _save(fig, "RQ1/outputs", "conversion_rate_gap.png")


def plot_label_event_audit() -> None:
    rows = _read("RQ1/outputs", "rq1_label_event_audit.csv").copy()
    rows["label"] = rows["metric"].replace(
        {
            "users_with_multiple_yes_events": "Multiple Yes events",
            "users_with_yes_before_last_touch": "Yes before final touch",
            "users_with_last_touch_yes": "Final touch is Yes",
            "converted_users_with_single_yes": "Exactly one Yes event",
        }
    )
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(8.0, 4.8))
        bars = ax.bar(rows["label"], rows["count"], color=["#C94C4C", "#C94C4C", "#5B7C99", "#7A9A58"])
        ax.set_ylabel("Users")
        ax.set_title("Label Event Audit Reveals Non-Terminal And Repeated Yes Labels")
        ax.grid(axis="y", color="#E1E5EA", linewidth=0.8)
        ax.tick_params(axis="x", rotation=20)
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 40, f"{bar.get_height():.0f}", ha="center", fontsize=9)
    _save(fig, "RQ1/outputs", "label_event_audit.png")


def plot_channel_signal() -> None:
    rates = _read("RQ2/outputs", "rq2_channel_conversion_rates.csv").sort_values("conversion_rate_pct")
    tests = _read("RQ2/outputs", "rq2_channel_signal_tests.csv")
    p_value = float(tests.loc[0, "p_value"])
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(8.0, 4.8))
        ax.barh(rates["Channel"], rates["conversion_rate_pct"], color="#6F8FA8")
        ax.set_xlabel("Touchpoint-level Yes rate (%)")
        ax.set_title("Channel-Level Row Conversion Rates Are Nearly Flat")
        ax.set_xlim(45, 52)
        ax.grid(axis="x", color="#E1E5EA", linewidth=0.8)
        ax.text(45.05, -0.75, f"Chi-square p-value = {p_value:.4f}", fontsize=10, color="#4B5563")
        for i, value in enumerate(rates["conversion_rate_pct"]):
            ax.text(value + 0.08, i, f"{value:.2f}%", va="center", fontsize=9)
    _save(fig, "RQ2/outputs", "channel_signal.png")


def plot_model_comparison() -> None:
    metrics = pd.read_csv(Path(__file__).resolve().parents[2] / "model" / "logistic_regression" / "outputs" / "rq2_logistic_model_metrics.csv")
    rows = metrics.copy()
    rows["model"] = rows["model"].replace(
        {
            "row_channel": "Row channel",
            "user_any_channel": "User any-channel",
            "journey_length_only": "Journey length only",
            "channel_plus_length": "Channel + length",
        }
    )
    long = rows.melt(id_vars="model", value_vars=["auc_test", "pseudo_r2_mcfadden"], var_name="metric", value_name="value")
    long["metric"] = long["metric"].replace({"auc_test": "AUC", "pseudo_r2_mcfadden": "McFadden pseudo-R2"})
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        sns.barplot(data=long, x="model", y="value", hue="metric", palette=["#5B7C99", "#C88A3D"], ax=ax)
        ax.set_xlabel("")
        ax.set_ylabel("Metric value")
        ax.set_title("Predictive Signal Comes Mainly From Journey-Level Context")
        ax.set_ylim(0, max(0.82, long["value"].max() * 1.15))
        ax.tick_params(axis="x", rotation=18)
        ax.grid(axis="y", color="#E1E5EA", linewidth=0.8)
        ax.legend(title="")
    _save(fig, "RQ2/outputs", "model_comparison.png")


def plot_sensitivity() -> None:
    rows = _read("RQ3/outputs", "rq3_sensitivity_rank_stability.csv").copy()
    rows["scenario_short"] = rows["scenario"].replace(
        {
            "Current any-Yes label": "Any Yes",
            "Stricter final-touch Yes label": "Final Yes",
            "Downsampled current positives to 1%": "1%",
            "Downsampled current positives to 3%": "3%",
            "Downsampled current positives to 5%": "5%",
            "Downsampled current positives to 10%": "10%",
        }
    )
    with plt.rc_context(STYLE):
        fig, ax1 = plt.subplots(figsize=(8.5, 4.8))
        ax1.bar(rows["scenario_short"], rows["positive_rate_pct"], color="#6F8FA8", alpha=0.75, label="Positive rate")
        ax1.set_ylabel("Positive label rate (%)")
        ax1.set_xlabel("Sensitivity label")
        ax1.grid(axis="y", color="#E1E5EA", linewidth=0.8)
        ax2 = ax1.twinx()
        ax2.plot(rows["scenario_short"], rows["spearman_linear_share_vs_current"], color="#C94C4C", marker="o", label="Spearman vs current")
        ax2.set_ylabel("Rank stability")
        ax2.set_ylim(-1.05, 1.05)
        ax1.set_title("Attribution Rankings Change Under Stricter Or Downsampled Labels")
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines + lines2, labels + labels2, loc="upper right")
    _save(fig, "RQ3/outputs", "sensitivity_stability.png")


def plot_safe_analysis_flow() -> None:
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(9.0, 4.8))
        ax.axis("off")
        boxes = [
            (0.03, 0.58, "1. SQL audit\nlabels and denominators"),
            (0.27, 0.58, "2. Python tests\nchannel signal"),
            (0.51, 0.58, "3. Model controls\njourney length"),
            (0.75, 0.58, "4. Sensitivity\nlabel assumptions"),
            (0.27, 0.18, "Unsafe: direct\nchannel winner claim"),
            (0.62, 0.18, "Safer: report\nvalidity caution"),
        ]
        for x, y, text in boxes:
            face = "#F4F6F9" if "Unsafe" not in text else "#FCE8E6"
            edge = "#6F8FA8" if "Unsafe" not in text else "#C94C4C"
            ax.text(x, y, text, transform=ax.transAxes, ha="left", va="center", fontsize=11, bbox=dict(boxstyle="round,pad=0.45", facecolor=face, edgecolor=edge, linewidth=1.5))
        for start, end in [((0.21, 0.58), (0.26, 0.58)), ((0.45, 0.58), (0.50, 0.58)), ((0.69, 0.58), (0.74, 0.58)), ((0.83, 0.49), (0.72, 0.28)), ((0.42, 0.28), (0.60, 0.24))]:
            ax.annotate("", xy=end, xytext=start, xycoords="axes fraction", arrowprops=dict(arrowstyle="->", color="#30343B", lw=1.5))
        ax.set_title("Recommended Analysis Path For Biased Attribution Data", pad=18, fontsize=13)
    _save(fig, "RQ3/outputs", "safe_analysis_flow.png")


def run() -> None:
    plot_conversion_gap()
    plot_label_event_audit()
    plot_channel_signal()
    plot_model_comparison()
    plot_sensitivity()
    plot_safe_analysis_flow()


def main() -> None:
    run()
    print("Visualization complete. Figures written to analysis_python/RQ1/outputs, RQ2/outputs, and RQ3/outputs.")


if __name__ == "__main__":
    main()

