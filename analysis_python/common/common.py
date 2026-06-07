from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_OUTPUT_DIR = PROJECT_ROOT / "data" / "sql_outputs"
ANALYSIS_OUTPUT_DIR = PROJECT_ROOT / "analysis_python"
FINAL_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
FINAL_FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"

RANDOM_SEED = 42

CHANNELS = [
    "Direct Traffic",
    "Display Ads",
    "Email",
    "Referral",
    "Search Ads",
    "Social Media",
]

BENCHMARK_ROWS = [
    {
        "source": "IRP Commerce Market Data",
        "period": "2026 market-data page accessed 2026-06-07",
        "rate_pct": 1.56,
        "denominator": "transactions / sessions",
        "url": "https://www.irpcommerce.com/en/gb/ecommercemarketdata.aspx",
        "note": "External e-commerce session-level benchmark; denominator differs from the case-study user-level any-Yes label.",
    },
    {
        "source": "Shopify retail conversion benchmark summary",
        "period": "article accessed 2026-06-07",
        "rate_pct": 1.60,
        "denominator": "lower bound of typical online retail conversion-rate range",
        "url": "https://www.shopify.com/blog/retail-conversion-rate",
        "note": "Reported as a typical low-end online retail benchmark in Shopify's summary.",
    },
    {
        "source": "Shopify retail conversion benchmark summary",
        "period": "article accessed 2026-06-07",
        "rate_pct": 3.00,
        "denominator": "upper bound of common online retail conversion-rate range",
        "url": "https://www.shopify.com/blog/retail-conversion-rate",
        "note": "Used as a conservative upper-range comparator, not as an exact sector match.",
    },
]


def read_sql_output(name: str) -> pd.DataFrame:
    path = SQL_OUTPUT_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing SQL output: {path}")
    return pd.read_csv(path)


def write_output(df: pd.DataFrame, rq_folder: str, filename: str) -> Path:
    out_dir = ANALYSIS_OUTPUT_DIR / rq_folder
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    df.to_csv(path, index=False)
    return path


def ensure_output_dirs() -> None:
    for path in [ANALYSIS_OUTPUT_DIR, FINAL_TABLES_DIR, FINAL_FIGURES_DIR]:
        path.mkdir(parents=True, exist_ok=True)

