import pandas as pd

from dqdetect.profiler import profile_dataframe
from dqdetect.report import render_markdown, write_reports


def test_markdown_contains_summary():
    profile = profile_dataframe(pd.DataFrame({"id": [1, 2, 2]}))
    report = render_markdown(profile)

    assert "# Data Quality Report" in report
    assert "Duplicate rows" in report


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
