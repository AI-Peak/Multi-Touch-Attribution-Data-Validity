# Python Analysis Layer

This layer consumes SQL-generated CSVs from `data/sql_outputs/`.

It does **not**:

- read the raw CSV directly;
- reconstruct journeys;
- recompute first-touch, last-touch, or linear baseline attribution.

It does:

- compare SQL conversion rates with external benchmarks;
- run statistical signal diagnostics such as chi-square and Cramer's V;
- run label-sensitivity and descriptive budget what-if analysis;
- generate figures for the paper, proposal, and visual brief.

Model training is intentionally separated into `model/`.

