# Model Layer

This folder is separate from `analysis_python/` to make the rubric distinction clear.

Models consume SQL-generated analytical tables from `data/sql_outputs/`. They do not read the raw CSV directly and do not reconstruct journeys.

## Logistic Regression

`model/logistic_regression/` trains four diagnostic models for RQ2:

- row-channel logistic regression;
- user-any-channel logistic regression;
- journey-length-only logistic regression;
- channel-plus-length logistic regression.

The goal is to test whether channel identity has reliable predictive signal after accounting for journey-level confounding.

## Markov Chain

`model/markov_chain/` builds a transition matrix and removal effects from SQL-generated journey sequences.

Markov output supports RQ2 as a diagnostic attribution model and supports RQ3 as an input to cautious methodology discussion. It is not interpreted as causal channel contribution because the conversion label is under audit.

