import argparse
import os
from pathlib import Path

from dqdetect.compare import compare_profiles
from dqdetect.database import load_database_table
from dqdetect.io import load_data
from dqdetect.profiler import profile_dataframe, profile_has_issues
from dqdetect.report import write_reports
from dqdetect.schema import load_schema


def _issue_line(count, singular_subject, plural_subject, issue):
    subject = singular_subject if count == 1 else plural_subject
    verb = "contains" if count == 1 else "contain"
    return f"- {count} {subject} {verb} {issue}"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="dqdetect",
        description=(
            "Profile CSV, Excel, or database table data for common "
            "data-quality issues."
        ),
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to a CSV or Excel file",
    )
    parser.add_argument(
        "--sheet",
        help="Excel sheet name or index. Ignored for CSV files.",
    )
    parser.add_argument(
        "--database-url",
        help=(
            "SQLAlchemy database URL. For secrets, prefer the "
            "DQDETECT_DATABASE_URL environment variable."
        ),
    )
    parser.add_argument(
        "--table",
        help="Database table to profile instead of a file",
    )
    parser.add_argument(
        "--db-schema",
        help="Optional database schema name, for example public",
    )
    parser.add_argument(
        "--compare",
        help="Optional CSV or Excel file to compare with the current dataset",
    )
    parser.add_argument(
        "--compare-sheet",
        help="Excel sheet name or index for the comparison file",
    )
    parser.add_argument(
        "--schema",
        dest="schema_path",
        help="Path to a JSON schema-rules file",
    )
    parser.add_argument(
        "--iqr-multiplier",
        type=float,
        default=1.5,
        help="IQR outlier multiplier (default: 1.5)",
    )
    parser.add_argument(
        "--min-outlier-sample-size",
        type=int,
        default=4,
        help="Minimum non-missing values required for IQR checks (default: 4)",
    )
    parser.add_argument(
        "--output",
        default="reports",
        help="Directory for generated reports (default: reports)",
    )
    parser.add_argument(
        "--format",
        choices=["md", "html", "json", "both", "all"],
        default="both",
        help=(
            "Report format: md, html, json, both (md+html), "
            "or all (default: both)"
        ),
    )
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit with status 1 when any data-quality or schema issue is found",
    )
    return parser


def _load_current_dataset(args, parser):
    if bool(args.file) == bool(args.table):
        parser.error("Provide exactly one input: a file path or --table")

    if args.table:
        if args.sheet:
            parser.error("--sheet can only be used with file input")

        database_url = args.database_url or os.getenv("DQDETECT_DATABASE_URL")
        try:
            dataframe = load_database_table(
                database_url,
                table=args.table,
                schema=args.db_schema,
            )
        except (ImportError, ValueError) as exc:
            parser.error(str(exc))

        source_name = (
            f"{args.db_schema}.{args.table}" if args.db_schema else args.table
        )
        stem = source_name.replace(".", "_")
        return dataframe, source_name, stem

    source = Path(args.file)
    try:
        dataframe = load_data(source, sheet=args.sheet)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    return dataframe, source.name, source.stem


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.iqr_multiplier <= 0:
        parser.error("--iqr-multiplier must be greater than 0")

    if args.min_outlier_sample_size < 1:
        parser.error("--min-outlier-sample-size must be at least 1")

    schema_rules = None
    if args.schema_path:
        try:
            schema_rules = load_schema(args.schema_path)
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))

    dataframe, source_name, stem = _load_current_dataset(args, parser)

    profile = profile_dataframe(
        dataframe,
        source_name=source_name,
        iqr_multiplier=args.iqr_multiplier,
        min_outlier_sample_size=args.min_outlier_sample_size,
        schema_rules=schema_rules,
    )

    if args.compare:
        compare_source = Path(args.compare)
        try:
            previous_dataframe = load_data(
                compare_source,
                sheet=args.compare_sheet,
            )
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))

        previous_profile = profile_dataframe(
            previous_dataframe,
            source_name=compare_source.name,
            iqr_multiplier=args.iqr_multiplier,
            min_outlier_sample_size=args.min_outlier_sample_size,
        )
        profile["comparison"] = compare_profiles(profile, previous_profile)

    summary = profile["summary"]
    written = write_reports(
        profile,
        output_dir=args.output,
        stem=stem,
        report_format=args.format,
    )

    print("Data Quality Detective")
    print(f"Source: {source_name}")
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

    schema_validation = profile.get("schema_validation")
    if schema_validation is not None:
        print()
        print(
            "Schema validation: "
            + ("passed" if schema_validation["valid"] else "issues found")
        )

    comparison = profile.get("comparison")
    if comparison is not None:
        print()
        print("Dataset comparison")
        print(f"- Row change: {comparison['row_delta']:+,}")
        print(f"- Column change: {comparison['column_delta']:+,}")
        print(
            f"- Duplicate-row change: "
            f"{comparison['duplicate_row_delta']:+,}"
        )

    print()
    print("Reports written to:")
    for path in written:
        print(f"  {path}")

    if args.fail_on_issues and profile_has_issues(profile):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
