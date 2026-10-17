import json

from dqdetect.cli import main


def test_cli_uses_singular_and_plural_wording(tmp_path, capsys):
    source = tmp_path / "sample.csv"
    source.write_text(
        "id,order_date,freight_cost\n"
        "1,2025-01-01,10.00\n"
        "2,bad-date,Included\n"
        "2,bad-date,Included\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "reports"
    exit_code = main(
        [
            str(source),
            "--format",
            "md",
            "--output",
            str(output_dir),
        ]
    )

    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "1 date-like column contains invalid values" in captured
    assert "1 column contains mixed numeric/text values" in captured
    assert (output_dir / "sample_report.md").exists()


def test_cli_writes_json_report(tmp_path):
    source = tmp_path / "sample.csv"
    source.write_text("id,value\n1,a\n2,b\n", encoding="utf-8")

    output_dir = tmp_path / "reports"
    exit_code = main(
        [
            str(source),
            "--format",
            "json",
            "--output",
            str(output_dir),
        ]
    )

    report_path = output_dir / "sample_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["summary"]["rows"] == 2
    assert payload["settings"]["iqr_multiplier"] == 1.5


def test_fail_on_issues_returns_one(tmp_path):
    source = tmp_path / "sample.csv"
    source.write_text("id\n1\n1\n", encoding="utf-8")

    exit_code = main(
        [
            str(source),
            "--format",
            "md",
            "--output",
            str(tmp_path / "reports"),
            "--fail-on-issues",
        ]
    )

    assert exit_code == 1


def test_fail_on_issues_returns_zero_for_clean_data(tmp_path):
    source = tmp_path / "sample.csv"
    source.write_text("id,value\n1,a\n2,b\n", encoding="utf-8")

    exit_code = main(
        [
            str(source),
            "--format",
            "md",
            "--output",
            str(tmp_path / "reports"),
            "--fail-on-issues",
        ]
    )

    assert exit_code == 0
