import argparse
from pathlib import Path

from dqdetect.io import load_data
from dqdetect.profiler import profile_dataframe
from dqdetect.report import write_reports


def _label(count, singular, plural=None):
    if count == 1:
        return singular

    return plural or f"{singular}s"


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

    missing = summary["columns_with_missing"]
    mixed = summary["mixed_numeric_text_columns"]
    invalid_dates = summary["date_columns_with_invalid_values"]
    outliers = summary["numeric_columns_with_outliers"]

    print("Data Quality Detective")
    print(f"File: {source}")
    print()
    print(f"Rows: {summary['rows']:,}")
    print(f"Columns: {summary['columns']:,}")
    print(f"Duplicate rows: {summary['duplicate_rows']:,}")
    print()
    print("Issues found")
    print(
        f"- {missing} {_label(missing, 'column')} contain"
        if missing != 1
        else f"- {missing} column contains"
    )
    print(
        f"  missing values"
        if missing
        else "  missing values"
    )
    print(
        f"- {mixed} {_label(mixed, 'column')} contain"
        if mixed != 1
        else f"- {mixed} column contains"
    )
    print("  mixed numeric/text values")
    print(
        f"- {invalid_dates} {_label(invalid_dates, 'date-like column')} contain"
        if invalid_dates != 1
        else f"- {invalid_dates} date-like column contains"
    )
    print("  invalid values")
    print(
        f"- {outliers} {_label(outliers, 'numeric column')} contain"
        if outliers != 1
        else f"- {outliers} numeric column contains"
    )
    print("  potential IQR outliers")
    print()
    print("Reports written to:")
    for path in written:
        print(f"  {path}")


if __name__ == "__main__":
    main()
