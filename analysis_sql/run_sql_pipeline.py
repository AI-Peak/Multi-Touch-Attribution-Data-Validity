from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA = PROJECT_ROOT / "data" / "raw" / "multi_touch_attribution_data.csv"
SQL_DIR = PROJECT_ROOT / "analysis_sql"
SQL_OUTPUT_DIR = PROJECT_ROOT / "data" / "sql_outputs"

SQL_FILES = [
    "rq1_data_audit.sql",
    "rq2_attribution_baseline.sql",
    "rq3_sensitivity_prep.sql",
]

EXPORT_TABLES = {
    # rq1_data_audit.sql — used in RQ2+RQ3
    "touchpoint_features":          "rq23_touchpoint_features",
    # rq1_data_audit.sql — used in RQ1+RQ3
    "journey_features":             "rq13_journey_features",
    # rq1_data_audit.sql — RQ2 only (ML-ready pivot)
    "user_channel_features":        "rq2_user_channel_features",
    # rq1_data_audit.sql — RQ1 only
    "conversion_rate_base":         "rq1_conversion_rate_base",
    "date_coverage_base":           "rq1_date_coverage_base",
    "label_event_audit_base":       "rq1_label_event_audit_base",
    "yes_event_distribution_base":  "rq1_yes_event_distribution_base",
    # rq2_attribution_baseline.sql — used in RQ2+RQ3
    "channel_conversion_rates_base": "rq23_channel_conversion_rates_base",
    "attribution_baseline":          "rq23_attribution_baseline",
    # rq3_sensitivity_prep.sql — RQ3 only
    "sensitivity_base":             "rq3_sensitivity_base",
    "scenario_user_label_base":     "rq3_scenario_user_label_base",
}


def load_raw_to_sqlite(conn: sqlite3.Connection) -> None:
    raw = pd.read_csv(RAW_DATA)
    required = ["User ID", "Timestamp", "Channel", "Campaign", "Conversion"]
    missing = [col for col in required if col not in raw.columns]
    if missing:
        raise ValueError(f"Missing required raw columns: {missing}")

    raw = raw.reset_index().rename(columns={"index": "touchpoint_id"})
    raw["touchpoint_id"] = raw["touchpoint_id"] + 1
    raw["timestamp_iso"] = pd.to_datetime(raw["Timestamp"], errors="raise").dt.strftime("%Y-%m-%d %H:%M:%S")
    staging = raw.rename(
        columns={
            "User ID": "user_id",
            "Channel": "channel",
            "Campaign": "campaign",
            "Conversion": "conversion",
        }
    )[["touchpoint_id", "user_id", "timestamp_iso", "channel", "campaign", "conversion"]]
    staging.to_sql("raw_touchpoints", conn, index=False, if_exists="replace")


def execute_sql_files(conn: sqlite3.Connection) -> None:
    for filename in SQL_FILES:
        sql = (SQL_DIR / filename).read_text(encoding="utf-8")
        conn.executescript(sql)
    conn.commit()


def export_tables(conn: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    if SQL_OUTPUT_DIR.exists():
        for f in SQL_OUTPUT_DIR.glob("*"):
            if f.is_file():
                try:
                    f.unlink()
                except OSError:
                    pass
    SQL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    exports: dict[str, pd.DataFrame] = {}
    for table, csv_name in EXPORT_TABLES.items():
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        exports[table] = df
        df.to_csv(SQL_OUTPUT_DIR / f"{csv_name}.csv", index=False)
    return exports


def assert_sql_outputs(exports: dict[str, pd.DataFrame]) -> None:
    touchpoints = exports["touchpoint_features"]
    journeys = exports["journey_features"]
    conversion = exports["conversion_rate_base"].set_index("metric")["value"]
    channels = set(exports["channel_conversion_rates_base"]["channel"])
    expected_channels = {"Direct Traffic", "Display Ads", "Email", "Referral", "Search Ads", "Social Media"}

    assert len(touchpoints) == 10_000, len(touchpoints)
    assert len(journeys) == 2_847, len(journeys)
    assert channels == expected_channels, channels
    assert abs(float(conversion.loc["user_any_yes_rate_pct"]) - 83.6319) < 0.05
    assert abs(float(conversion.loc["row_yes_rate_pct"]) - 49.44) < 0.05


def run() -> dict[str, pd.DataFrame]:
    with sqlite3.connect(":memory:") as conn:
        load_raw_to_sqlite(conn)
        execute_sql_files(conn)
        exports = export_tables(conn)
        assert_sql_outputs(exports)
        return exports


def main() -> None:
    exports = run()
    print(f"SQL baseline complete. Exported {len(exports)} tables to {SQL_OUTPUT_DIR}.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SQL pipeline failed: {exc}", file=sys.stderr)
        raise
