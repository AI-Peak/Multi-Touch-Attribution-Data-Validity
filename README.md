# Multi-Touch Attribution Data Validity Paper Package

This folder contains a complete reproducible package for reframing a public multi-touch attribution dataset as a data-validity and methodology-caution study.

## Research Questions

1. **RQ1:** Is the dataset valid enough for direct multi-touch attribution analysis?
2. **RQ2:** What evidence shows conversion-label bias, weak channel signal, or confounding?
3. **RQ3:** Given these limitations, what analysis strategy is safer for future users?

## Folder Structure And Rubric Mapping

- `data/raw/`: Source CSV copied from the original project.
- `data/sql_outputs/`: Intermediate CSV outputs created by the SQL baseline. Files are prefixed with `rq1_`, `rq2_`, `rq3_`, or `rq123_` indicating which research question they answer.
- `analysis_sql/`: SQLite SQL baseline layer for data preparation, journey construction, label audit, and first/last/linear attribution baseline.
- `analysis_python/RQ1/`: Jupyter notebook, Python script, and localized outputs (`outputs/`) for answering RQ1 (Data Validity Audit).
- `analysis_python/RQ2/`: Jupyter notebook, Python script, and localized outputs (`outputs/`) for answering RQ2 (Signal and Confounding).
- `analysis_python/RQ3/`: Jupyter notebook, Python script, and localized outputs (`outputs/`) for answering RQ3 (Sensitivity Analysis).
- `analysis_python/common/`: Shared Python helper utilities (`common.py`) and visualization generation (`visualization.py`).
- `model/`: Separate Python model layer for logistic regression (`model/logistic_regression/`) and Markov chain diagnostics (`model/markov_chain/`).
- `app/`: Scaffold only. It prepares JSON data contracts (`app/data/generated/`) for a future web app; no UI is implemented in this iteration.
- `scripts/run_all.py`: Deterministic entrypoint that orchestrates the entire pipeline: runs cleanup, regenerates SQL outputs, executes Python analysis and models, builds visualizations, prepares app JSON, and aggregates final outputs.

| Layer | Tool | Input | Output | Purpose |
|---|---|---|---|---|
| SQL baseline | SQLite SQL | `data/raw/*.csv` | `data/sql_outputs/rq*.csv` | Data preparation, journey features, label audit, baseline attribution |
| Python analysis | Python | `data/sql_outputs/rq*.csv` | `analysis_python/RQ*/outputs/*` | Benchmark comparison, statistical tests, sensitivity, visualizations |
| Model | Python | `data/sql_outputs/rq*.csv` | `model/*/outputs/*` | Logistic regression and Markov diagnostics |
| App scaffold | Python/JSON | SQL + Python + model outputs | `app/data/generated/*.json` | Data contract for future interactive app |
| Aggregated Output | Python (shutil) | RQ & Model outputs | `outputs/tables/`, `outputs/figures/` | Centralized, standardized final results with `rqX_` prefixes |

## Reproduce The Analysis

Install dependencies if needed:

```bash
pip install -r requirements.txt
```

Run the full non-overlapping pipeline from this folder:

```bash
python scripts/run_all.py
```

The pipeline asserts the key checks in the study: 10,000 touchpoints, 2,847 users, 83.63% any-Yes user conversion rate, 49.44% row-level Yes rate, all six channels present, row-channel AUC near random, and sensitivity labels at 1%, 3%, 5%, and 10%.

It also asserts the no-overlap contract: `analysis_python/` and `model/` do not read the raw CSV, do not reconstruct journeys, and do not recompute SQL baseline attribution.


## Main Finding

The dataset should not be used for direct channel-winner claims or causal budget reallocation. The user-level conversion label is inflated by an any-Yes aggregation rule, repeated and non-terminal Yes labels are common, channel-level row signal is weak, and attribution rankings are unstable under alternative label definitions.
