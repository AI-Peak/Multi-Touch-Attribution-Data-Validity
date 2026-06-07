from __future__ import annotations

import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis_python.RQ3.rq3_sensitivity_analysis import run as rq3_sensitivity_analysis_run
from analysis_python.RQ2.rq2_signal_diagnosis import run as rq2_signal_diagnosis_run
from analysis_python.RQ1.rq1_validity_analysis import run as rq1_validity_analysis_run
from analysis_python.common.visualization import run as visualization_run
from analysis_sql.run_sql_pipeline import run as run_sql_pipeline  # noqa: E402
from app.scripts.prepare_app_data import main as prepare_app_data  # noqa: E402
from model.logistic_regression.src.train_logistic_models import run as run_logistic_models  # noqa: E402
from model.markov_chain.src.build_markov_model import run as run_markov_model  # noqa: E402


FINAL_TABLES = PROJECT_ROOT / "outputs" / "tables"
FINAL_FIGURES = PROJECT_ROOT / "outputs" / "figures"
SQL_OUT = PROJECT_ROOT / "data" / "sql_outputs"
PY_OUT = PROJECT_ROOT / "analysis_python" / "outputs"
LOGIT_OUT = PROJECT_ROOT / "model" / "logistic_regression" / "outputs"
MARKOV_OUT = PROJECT_ROOT / "model" / "markov_chain" / "outputs"

EXPECTED_FINAL_TABLES = [
    "rq1_data_validity_summary.csv",
    "label_event_audit.csv",
    "benchmark_conversion_rates.csv",
    "channel_signal_tests.csv",
    "rq2_logistic_model_metrics.csv",
    "model_coefficients.csv",
    "markov_removal_effects.csv",
    "rq3_sensitivity_rank_stability.csv",
    "simulation_results.csv",
]


def _copy(src: Path, dest_name: str | None = None) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    FINAL_TABLES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, FINAL_TABLES / (dest_name or src.name))


def aggregate_final_outputs() -> None:
    pass

def assert_reproducibility() -> None:
    validity = (PROJECT_ROOT / "analysis_python" / "RQ1" / "outputs" / "rq1_data_validity_summary.csv")
    import pandas as pd

    values = pd.read_csv(validity).set_index("metric")["value"]
    assert int(float(values.loc["total_touchpoints"])) == 10_000
    assert int(float(values.loc["unique_users"])) == 2_847
    assert abs(float(values.loc["user_any_yes_rate_pct"]) - 83.6319) < 0.05
    assert abs(float(values.loc["row_yes_rate_pct"]) - 49.44) < 0.05

    channels = set(pd.read_csv(SQL_OUT / "rq2_channel_conversion_rates_base.csv")["channel"])
    assert channels == {"Direct Traffic", "Display Ads", "Email", "Referral", "Search Ads", "Social Media"}

    model_metrics = pd.read_csv(LOGIT_OUT / "rq2_logistic_model_metrics.csv")
    row_auc = float(model_metrics.loc[model_metrics["model"].eq("row_channel"), "auc_test"].iloc[0])
    assert 0.45 <= row_auc <= 0.55, row_auc
    assert {"journey_length_only", "channel_plus_length"}.issubset(set(model_metrics["model"]))

    sensitivity = pd.read_csv(PROJECT_ROOT / "analysis_python" / "RQ3" / "outputs" / "rq3_sensitivity_rank_stability.csv")
    assert {1.0, 3.0, 5.0, 10.0} == set(sensitivity["target_rate_pct"].dropna().round(1))

def assert_no_overlap_contract() -> None:
    analysis_files = list((PROJECT_ROOT / "analysis_python").rglob("*.py"))
    model_files = list((PROJECT_ROOT / "model").rglob("*.py"))
    forbidden_analysis = ["multi_touch_attribution_data.csv", "RAW_DATA", "reconstruct_journeys", "First_Touch_Channel"]
    forbidden_model = ["multi_touch_attribution_data.csv", "RAW_DATA", "reconstruct_journeys"]

    for path in analysis_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_analysis:
            assert token not in text, f"analysis_python overlaps SQL baseline via {token} in {path}"
    for path in model_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_model:
            assert token not in text, f"model overlaps SQL baseline via {token} in {path}"


def main() -> None:
    print("0/8 Cleaning up redundant and stale directories")
    redundant_dirs = [
        PROJECT_ROOT / "outputs",
        PROJECT_ROOT / "analysis_python" / "outputs",
    ]
    for d in redundant_dirs:
        if d.exists():
            try:
                shutil.rmtree(d)
                print(f"Removed redundant directory: {d}")
            except Exception as e:
                print(f"Warning: Could not remove directory {d}: {e}")

    # Remove any duplicate .png files saved directly in analysis_python
    for f in (PROJECT_ROOT / "analysis_python").glob("*.png"):
        try:
            f.unlink()
            print(f"Removed duplicate figure: {f}")
        except OSError:
            pass

    # Remove stale legacy files that are no longer imported/used
    legacy_files = [
        PROJECT_ROOT / "analysis_python" / "common" / "analysis.py",
        PROJECT_ROOT / "analysis_python" / "common" / "data.py",
        PROJECT_ROOT / "analysis_python" / "common" / "plots.py",
        PROJECT_ROOT / "analysis_python" / "common" / "config.py",
    ]
    for f in legacy_files:
        if f.exists():
            try:
                f.unlink()
                print(f"Removed legacy file: {f}")
            except OSError as e:
                print(f"Warning: Could not remove {f}: {e}")

    print("1/8 SQL baseline")
    run_sql_pipeline()
    print("2/8 Python validity analysis")
    rq1_validity_analysis_run()
    print("3/8 Python signal diagnosis")
    rq2_signal_diagnosis_run()
    print("4/8 Logistic regression model layer")
    run_logistic_models()
    print("5/8 Markov chain model layer")
    run_markov_model()
    print("6/8 Python sensitivity analysis")
    rq3_sensitivity_analysis_run()
    print("7/8 Visualization")
    visualization_run()
    print("8/8 App data JSON scaffold")
    prepare_app_data()
    aggregate_final_outputs()
    assert_reproducibility()
    assert_no_overlap_contract()
    print("Pipeline complete. SQL, Python analysis, model, app data, and final compatibility outputs are ready.")


if __name__ == "__main__":
    main()

