from __future__ import annotations

import json
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def write_notebook(dest_dir: Path, filename: str, cells: list[dict]) -> None:
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / filename).write_text(json.dumps(nb, indent=2), encoding="utf-8")


def main() -> None:
    # Clean up the old, redundant top-level notebooks directory if it exists
    old_notebook_dir = PROJECT_ROOT / "notebooks"
    if old_notebook_dir.exists():
        try:
            shutil.rmtree(old_notebook_dir)
            print(f"Removed old notebooks directory: {old_notebook_dir}")
        except Exception as e:
            print(f"Warning: Could not remove old notebooks directory: {e}")

    # 1. RQ1 Data Validity Audit Notebook
    write_notebook(
        PROJECT_ROOT / "analysis_python" / "RQ1",
        "rq1_data_validity_audit.ipynb",
        [
            markdown(
                "# Notebook 01 - RQ1 Data Validity Audit\n\n"
                "RQ1 asks whether the dataset is valid enough for direct multi-touch attribution analysis. "
                "This notebook reads the pipeline outputs and focuses on conversion-rate plausibility, label construction, and event timing."
            ),
            code(
                "import pandas as pd\n"
                "validity = pd.read_csv('outputs/rq1_data_validity_summary.csv')\n"
                "label_audit = pd.read_csv('outputs/rq1_label_event_audit.csv')\n"
                "benchmarks = pd.read_csv('outputs/rq1_benchmark_conversion_rates.csv')\n"
                "validity"
            ),
            code("label_audit"),
            code("benchmarks[['source', 'rate_pct', 'denominator', 'note']]"),
            markdown(
                "## RQ1 Conclusion\n\n"
                "The dataset fails the direct-attribution plausibility check. The current any-Yes rule produces an 83.63% user-level conversion rate, "
                "while repeated and non-terminal Yes labels are common. This does not prove the data is useless, but it means channel attribution should be framed as a validity caution rather than a market recommendation."
            ),
        ],
    )

    # 2. RQ2 Channel Signal And Confounding Notebook
    write_notebook(
        PROJECT_ROOT / "analysis_python" / "RQ2",
        "rq2_signal_and_confounding.ipynb",
        [
            markdown(
                "# Notebook 02 - RQ2 Channel Signal And Confounding\n\n"
                "RQ2 asks what evidence shows conversion-label bias, weak channel signal, or confounding. "
                "The key comparisons are row-level channel signal, logistic model performance, and Markov removal diagnostics."
            ),
            code(
                "import pandas as pd\n"
                "channel_rates = pd.read_csv('outputs/rq2_channel_conversion_rates.csv')\n"
                "tests = pd.read_csv('outputs/rq2_channel_signal_tests.csv')\n"
                "metrics = pd.read_csv('../../model/logistic_regression/outputs/rq2_logistic_model_metrics.csv')\n"
                "coefs = pd.read_csv('../../model/logistic_regression/outputs/rq2_logistic_model_coefficients.csv')\n"
                "markov = pd.read_csv('../../model/markov_chain/outputs/rq2_markov_removal_effects.csv')\n"
                "channel_rates"
            ),
            code("tests"),
            code("metrics"),
            code("coefs[coefs['model'].eq('channel_plus_length')]"),
            code("markov"),
            markdown(
                "## RQ2 Conclusion\n\n"
                "Channel identity is weak at row level: the chi-square p-value is high and row-channel AUC is near random. "
                "User-level prediction improves mainly because journey length captures repeated exposure. Markov removal effects should therefore be treated as diagnostic output, not causal channel credit."
            ),
        ],
    )

    # 3. RQ3 Safe Analysis Strategy Notebook
    write_notebook(
        PROJECT_ROOT / "analysis_python" / "RQ3",
        "rq3_safe_analysis_strategy.ipynb",
        [
            markdown(
                "# Notebook 03 - RQ3 Safe Analysis Strategy\n\n"
                "RQ3 asks what analysis is safer when the label is questionable. This notebook summarizes sensitivity labels and the descriptive budget simulation."
            ),
            code(
                "import pandas as pd\n"
                "stability = pd.read_csv('outputs/rq3_sensitivity_rank_stability.csv')\n"
                "shares = pd.read_csv('outputs/rq3_sensitivity_channel_shares.csv')\n"
                "sim = pd.read_csv('outputs/rq3_simulation_results.csv')\n"
                "stability"
            ),
            code("shares.pivot(index='channel', columns='scenario', values='linear_pct')"),
            code("sim"),
            markdown(
                "## RQ3 Conclusion\n\n"
                "The safer strategy is to report a validity audit, label sensitivity, and cautious descriptive comparisons. "
                "Direct budget optimization claims should be avoided because ranking stability changes under alternative labels and simulated gains are very small."
            ),
        ],
    )
    print("Notebooks successfully generated in analysis_python/RQ1, RQ2, and RQ3.")


if __name__ == "__main__":
    main()
