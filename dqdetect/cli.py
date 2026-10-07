import argparse
from pathlib import Path

from dqdetect.io import load_data
from dqdetect.profiler import profile_dataframe
from dqdetect.report import write_reports


def _issue_line(count, singular_subject, plural_subject, issue):
    subject = singular_subject if count == 1 else plural_subject
    verb = "contains" if count == 1 else "contain"
    return f"- {count} {subject} {verb} {issue}"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="dqdetect",
        description="Profile a CSV or Excel file for common data-quality issues.",
    )
    parser.add_argument("file", help="Path to a CSV or Excel file")
    parser.add_argument(
        "--sheet",
        help="Excel sheet name or index. Ignored for CSV files.",
    )
    parser.add_argument(
        "--output",
        default="reports",
        help="Directory for generated reports (default: reports)",
    )
    parser.add_argument(
        "--format",
        choices=["md", "html", "both"],
        default="both",
        help="Report format (default: both)",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    source = Path(args.file)

    try:
        dataframe = load_data(source, sheet=args.sheet)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    profile = profile_dataframe(dataframe, source_name=source.name)
    summary = profile["summary"]
    written = write_reports(
        profile,
        output_dir=args.output,
        stem=source.stem,
        report_format=args.format,
    )

    print("Data Quality Detective")
    print(f"File: {source}")
    print()
    print(f"Rows: {summary['rows']:,}")
    print(f"Columns: {summary['columns']:,}")
    print(f"Duplicate rows: {summary['duplicate_rows']:,}")
    print()
    print("Issues found")
    print(
        _issue_line(
            summary["columns_with_missing"],
            "column",
            "columns",
            "missing values",
        )
    )
    print(
        _issue_line(
            summary["mixed_numeric_text_columns"],
            "column",
            "columns",
            "mixed numeric/text values",
        )
    )
    print(
        _issue_line(
            summary["date_columns_with_invalid_values"],
            "date-like column",
            "date-like columns",
            "invalid values",
        )
    )
    print(
        _issue_line(
            summary["numeric_columns_with_outliers"],
            "numeric column",
            "numeric columns",
            "potential IQR outliers",
        )
    )
    print()
    print("Reports written to:")
    for path in written:
        print(f"  {path}")


if __name__ == "__main__":
    main()
