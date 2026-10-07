from datetime import datetime, timezone
from html import escape
from pathlib import Path


def _recommendations(profile):
    summary = profile["summary"]
    recommendations = []

    if summary["duplicate_rows"]:
        recommendations.append(
            "Review duplicate rows before aggregating or counting records."
        )
    if summary["columns_with_missing"]:
        recommendations.append(
            "Review missing values by column before deciding whether to impute, exclude, or preserve them."
        )
    if summary["mixed_numeric_text_columns"]:
        recommendations.append(
            "Keep mixed numeric/text source values separate from any cleaned numeric field instead of coercing text to zero."
        )
    if summary["date_columns_with_invalid_values"]:
        recommendations.append(
            "Inspect invalid date values before calculating durations or time-based KPIs."
        )
    if summary["numeric_columns_with_outliers"]:
        recommendations.append(
            "Investigate outliers before removing them; unusual values may be valid business events."
        )
    if summary["constant_columns"]:
        recommendations.append(
            "Constant columns may not add analytical value and can often be excluded from modeling."
        )

    if not recommendations:
        recommendations.append(
            "No issues were flagged by the current rules. Domain-specific validation may still be needed."
        )

    return recommendations


def render_markdown(profile):
    summary = profile["summary"]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Data Quality Report",
        "",
        f"**Source:** {summary['source']}",
        f"**Generated:** {generated}",
        "",
        "## Dataset summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Rows | {summary['rows']:,} |",
        f"| Columns | {summary['columns']:,} |",
        f"| Duplicate rows | {summary['duplicate_rows']:,} |",
        f"| Columns with missing values | {summary['columns_with_missing']} |",
        f"| Constant columns | {summary['constant_columns']} |",
        f"| Mixed numeric/text columns | {summary['mixed_numeric_text_columns']} |",
        f"| Date columns with invalid values | {summary['date_columns_with_invalid_values']} |",
        f"| Numeric columns with potential outliers | {summary['numeric_columns_with_outliers']} |",
        "",
        "## Column profile",
        "",
        "| Column | Type | Missing | Unique | Mixed | Invalid dates | Outliers | Issues |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]

    for item in profile["columns"]:
        issues = ", ".join(item["issues"]) if item["issues"] else "none"
        lines.append(
            "| {column} | {dtype} | {missing_count} ({missing_pct:.2f}%) | "
            "{unique_count} | {mixed_numeric_text_count} | {invalid_date_count} | "
            "{outlier_count} | {issues_text} |".format(**item, issues_text=issues)
        )

    lines.extend(["", "## Recommendations", ""])
    for recommendation in _recommendations(profile):
        lines.append(f"- {recommendation}")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "The checks in this report are screening rules, not automatic cleaning instructions. Business context should decide what gets changed.",
            "",
        ]
    )

    return "\n".join(lines)


def render_html(profile):
    summary = profile["summary"]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rows = []
    for item in profile["columns"]:
        issues = ", ".join(item["issues"]) if item["issues"] else "none"
        rows.append(
            "<tr>"
            f"<td>{escape(item['column'])}</td>"
            f"<td>{escape(item['dtype'])}</td>"
            f"<td>{item['missing_count']} ({item['missing_pct']:.2f}%)</td>"
            f"<td>{item['unique_count']}</td>"
            f"<td>{item['mixed_numeric_text_count']}</td>"
            f"<td>{item['invalid_date_count']}</td>"
            f"<td>{item['outlier_count']}</td>"
            f"<td>{escape(issues)}</td>"
            "</tr>"
        )

    recommendation_items = "".join(
        f"<li>{escape(item)}</li>" for item in _recommendations(profile)
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data Quality Report</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 1100px; margin: 40px auto; padding: 0 24px; color: #202124; }}
h1, h2 {{ color: #172554; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 24px 0; }}
.card {{ border: 1px solid #d9dee8; border-radius: 10px; padding: 16px; }}
.value {{ font-size: 1.5rem; font-weight: 700; margin-top: 6px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
th, td {{ border-bottom: 1px solid #e5e7eb; padding: 10px; text-align: left; vertical-align: top; }}
th {{ background: #f8fafc; }}
.note {{ background: #f8fafc; border-left: 4px solid #64748b; padding: 12px 16px; margin-top: 24px; }}
</style>
</head>
<body>
<h1>Data Quality Report</h1>
<p><strong>Source:</strong> {escape(summary['source'])}<br>
<strong>Generated:</strong> {generated}</p>

<div class="cards">
  <div class="card">Rows<div class="value">{summary['rows']:,}</div></div>
  <div class="card">Columns<div class="value">{summary['columns']}</div></div>
  <div class="card">Duplicate rows<div class="value">{summary['duplicate_rows']}</div></div>
  <div class="card">Columns with missing<div class="value">{summary['columns_with_missing']}</div></div>
</div>

<h2>Column profile</h2>
<table>
<thead>
<tr><th>Column</th><th>Type</th><th>Missing</th><th>Unique</th><th>Mixed</th><th>Invalid dates</th><th>Outliers</th><th>Issues</th></tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>

<h2>Recommendations</h2>
<ul>{recommendation_items}</ul>

<div class="note">
These checks are screening rules, not automatic cleaning instructions. Business context should decide what gets changed.
</div>
</body>
</html>
"""


def write_reports(profile, output_dir, stem, report_format="both"):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    written = []

    if report_format in {"md", "both"}:
        markdown_path = output / f"{stem}_report.md"
        markdown_path.write_text(render_markdown(profile), encoding="utf-8")
        written.append(markdown_path)

    if report_format in {"html", "both"}:
        html_path = output / f"{stem}_report.html"
        html_path.write_text(render_html(profile), encoding="utf-8")
        written.append(html_path)

    return written
