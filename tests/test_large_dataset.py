"""Regression coverage for datasets larger than 50,000 rows."""

import json

import pandas as pd

from dqdetect.cli import main


def test_cli_profiles_50001_row_csv_and_writes_json(tmp_path):
    """End-to-end CLI profiling must work above the 50,000-row threshold."""
    row_count = 50_001
    df = pd.DataFrame(
        {
            "record_id": list(range(row_count - 1)) + [0],
            "order_date": ["2025-01-01"] * row_count,
            "amount": [float(20 + index % 5) for index in range(row_count - 1)]
            + [20.0],
            "freight_cost": ["5.00"] * row_count,
            "customer_id": ["C001"] * row_count,
        }
    )

    # The last row initially duplicates the first row.
    df.loc[3, "amount"] = 10_000.0
    df.loc[7, "order_date"] = "not-a-date"
    df.loc[9, "freight_cost"] = "Included"
    df.loc[11, "customer_id"] = None

    source = tmp_path / "large_orders.csv"
    output_dir = tmp_path / "reports"
    df.to_csv(source, index=False)

    exit_code = main(
        [
            str(source),
            "--format",
            "json",
            "--output",
            str(output_dir),
        ]
    )

    report_path = output_dir / "large_orders_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report["summary"]

    assert exit_code == 0
    assert summary["rows"] == row_count
    assert summary["columns"] == 5
    assert summary["duplicate_rows"] == 1
    assert summary["columns_with_missing"] == 1
    assert summary["mixed_numeric_text_columns"] == 1
    assert summary["date_columns_with_invalid_values"] == 1
    assert summary["numeric_columns_with_outliers"] == 1
    assert len(report["columns"]) == 5


def test_cli_profiles_50001_row_excel_and_writes_json(tmp_path):
    """End-to-end Excel profiling must also work above 50,000 rows."""
    row_count = 50_001
    df = pd.DataFrame(
        {
            "record_id": list(range(row_count - 1)) + [0],
            "amount": [float(20 + index % 5) for index in range(row_count - 1)]
            + [20.0],
            "status": ["Shipped"] * row_count,
        }
    )
    df.loc[4, "status"] = None

    source = tmp_path / "large_orders.xlsx"
    output_dir = tmp_path / "excel_reports"
    df.to_excel(source, index=False)

    exit_code = main(
        [
            str(source),
            "--format",
            "json",
            "--output",
            str(output_dir),
        ]
    )

    report_path = output_dir / "large_orders_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report["summary"]

    assert exit_code == 0
    assert summary["rows"] == row_count
    assert summary["columns"] == 3
    assert summary["duplicate_rows"] == 1
    assert summary["columns_with_missing"] == 1
