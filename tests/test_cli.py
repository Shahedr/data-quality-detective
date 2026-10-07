from pathlib import Path

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
    main(
        [
            str(source),
            "--format",
            "md",
            "--output",
            str(output_dir),
        ]
    )

    captured = capsys.readouterr().out

    assert "1 date-like column contains invalid values" in captured
    assert "1 column contains mixed numeric/text values" in captured
    assert (output_dir / "sample_report.md").exists()
