import json

import pandas as pd

from dqdetect.compare import compare_profiles
from dqdetect.profiler import profile_dataframe
from dqdetect.report import (
    render_html,
    render_json,
    render_markdown,
    write_reports,
)


def test_markdown_contains_summary_and_settings():
    profile = profile_dataframe(pd.DataFrame({"id": [1, 2, 2]}))
    report = render_markdown(profile)

    assert "# Data Quality Report" in report
    assert "Duplicate rows" in report
    assert "IQR multiplier" in report


def test_html_contains_issue_overview():
    profile = profile_dataframe(pd.DataFrame({"id": [1, 2, 2]}))
    report = render_html(profile)

    assert "<h2>Issue overview</h2>" in report
    assert 'class="bar-track"' in report


def test_json_contains_machine_readable_profile():
    profile = profile_dataframe(
        pd.DataFrame(
            {
                "order_date": ["2025-01-01", "bad-date"],
                "amount": [10.0, 20.0],
            }
        )
    )

    payload = json.loads(render_json(profile))

    assert payload["summary"]["rows"] == 2
    assert payload["summary"]["columns"] == 2
    assert payload["summary"]["date_columns_with_invalid_values"] == 1
    assert payload["settings"]["iqr_multiplier"] == 1.5
    assert isinstance(payload["columns"], list)
    assert isinstance(payload["recommendations"], list)
    assert "generated_at" in payload


def test_json_includes_schema_and_comparison():
    previous = profile_dataframe(
        pd.DataFrame({"id": [1], "amount": [10.0]}),
        source_name="previous.csv",
    )
    current = profile_dataframe(
        pd.DataFrame({"id": [1, 2], "amount": [10.0, 20.0]}),
        source_name="current.csv",
        schema_rules={
            "required_columns": ["id"],
            "column_types": {"id": "numeric"},
            "allow_extra_columns": True,
        },
    )
    current["comparison"] = compare_profiles(current, previous)

    payload = json.loads(render_json(current))

    assert payload["schema_validation"]["valid"] is True
    assert payload["comparison"]["row_delta"] == 1


def test_write_markdown_report(tmp_path):
    profile = profile_dataframe(pd.DataFrame({"id": [1, 2]}))
    written = write_reports(
        profile,
        output_dir=tmp_path,
        stem="sample",
        report_format="md",
    )

    assert len(written) == 1
    assert written[0].exists()


def test_write_json_report(tmp_path):
    profile = profile_dataframe(pd.DataFrame({"id": [1, 2]}))
    written = write_reports(
        profile,
        output_dir=tmp_path,
        stem="sample",
        report_format="json",
    )

    assert len(written) == 1
    assert written[0].suffix == ".json"

    payload = json.loads(written[0].read_text(encoding="utf-8"))
    assert payload["summary"]["rows"] == 2


def test_write_all_reports(tmp_path):
    profile = profile_dataframe(pd.DataFrame({"id": [1, 2]}))
    written = write_reports(
        profile,
        output_dir=tmp_path,
        stem="sample",
        report_format="all",
    )

    assert {path.suffix for path in written} == {".md", ".html", ".json"}
