# SQL Baseline Layer

This folder contains the SQL layer for the project. SQL is responsible for data engineering and baseline analytics only:

- construct touchpoint, journey, and user-channel analytical tables;
- compute core conversion-rate and label-event audit tables;
- compute channel conversion rates;
- compute first-touch, last-touch, and linear attribution baselines;
- prepare scenario metadata for later Python sensitivity analysis.

Python analysis does not reconstruct journeys or recompute these baseline attribution tables. It consumes the CSV outputs exported to `data/sql_outputs/`.

Run from the project root:

```bash
python analysis_sql/run_sql_pipeline.py
```

Outputs are written to `data/sql_outputs/*.csv`.

