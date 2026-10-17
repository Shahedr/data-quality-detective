import json
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
            "Review missing values by column before deciding whether to "
            "impute, exclude, or preserve them."
        )
    if summary["mixed_numeric_text_columns"]:
        recommendations.append(
            "Keep mixed numeric/text source values separate from any cleaned "
            "numeric field instead of coercing text to zero."
        )
    if summary["date_columns_with_invalid_values"]:
        recommendations.append(
            "Inspect invalid date values before calculating durations or "
            "time-based KPIs."
        )
    if summary["numeric_columns_with_outliers"]:
        recommendations.append(
            "Investigate outliers before removing them; unusual values may "
            "be valid business events."
        )
    if summary["constant_columns"]:
        recommendations.append(
            "Constant columns may not add analytical value and can often be "
            "excluded from modeling."
        )

    schema_validation = profile.get("schema_validation")
    if schema_validation is not None and not schema_validation["valid"]:
        if schema_validation["missing_required_columns"]:
            recommendations.append(
                "Add or investigate missing required columns before relying "
                "on the dataset."
            )
        if schema_validation["unexpected_columns"]:
            recommendations.append(
                "Review unexpected columns against the declared schema."
            )
        if schema_validation["type_mismatches"]:
            recommendations.append(
                "Review schema type mismatches before downstream processing."
            )

    if not recommendations:
        recommendations.append(
            "No issues were flagged by the current rules. Domain-specific "
            "validation may still be needed."
        )

    return recommendations


def _generated_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _render_schema_markdown(profile):
    validation = profile.get("schema_validation")
    if validation is None:
        return []

    lines = [
        "",
        "## Schema validation",
        "",
        f"**Status:** {'passed' if validation['valid'] else 'issues found'}",
        "",
    ]

    missing = validation["missing_required_columns"]
    unexpected = validation["unexpected_columns"]
    mismatches = validation["type_mismatches"]

    lines.append(
        "- Missing required columns: "
        + (", ".join(missing) if missing else "none")
    )
    lines.append(
        "- Unexpected columns: "
        + (", ".join(unexpected) if unexpected else "none")
    )

    if mismatches:
        lines.extend(
            [
                "",
                "| Column | Expected | Actual |",
                "|---|---|---|",
            ]
        )
        for item in mismatches:
            lines.append(
                f"| {item['column']} | {item['expected']} | {item['actual']} |"
            )
    else:
        lines.append("- Type mismatches: none")

    return lines


def _render_comparison_markdown(profile):
    comparison = profile.get("comparison")
    if comparison is None:
        return []

    lines = [
        "",
        "## Dataset comparison",
        "",
        f"**Previous:** {comparison['previous_source']}",
        f"**Current:** {comparison['current_source']}",
        "",
        "| Metric | Change |",
        "|---|---:|",
        f"| Rows | {comparison['row_delta']:+,} |",
        f"| Columns | {comparison['column_delta']:+,} |",
        f"| Duplicate rows | {comparison['duplicate_row_delta']:+,} |",
        "",
        "- Added columns: "
        + (
            ", ".join(comparison["added_columns"])
            if comparison["added_columns"]
            else "none"
        ),
        "- Removed columns: "
        + (
            ", ".join(comparison["removed_columns"])
            if comparison["removed_columns"]
            else "none"
        ),
    ]

    if comparison["type_changes"]:
        lines.extend(
            [
                "",
                "### Type changes",
                "",
                "| Column | Previous | Current |",
                "|---|---|---|",
            ]
        )
        for item in comparison["type_changes"]:
            lines.append(
                f"| {item['column']} | {item['previous']} | {item['current']} |"
            )

    if comparison["missing_value_changes"]:
        lines.extend(
            [
                "",
                "### Missing-value changes",
                "",
                "| Column | Previous | Current | Change |",
                "|---|---:|---:|---:|",
            ]
        )
        for item in comparison["missing_value_changes"]:
            lines.append(
                f"| {item['column']} | {item['previous']} | "
                f"{item['current']} | {item['delta']:+} |"
            )

    return lines


def render_markdown(profile):
    summary = profile["summary"]
    settings = profile.get("settings", {})
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
        f"| Mixed numeric/text columns | "
        f"{summary['mixed_numeric_text_columns']} |",
        f"| Date columns with invalid values | "
        f"{summary['date_columns_with_invalid_values']} |",
        f"| Numeric columns with potential outliers | "
        f"{summary['numeric_columns_with_outliers']} |",
    ]

    if settings:
        lines.extend(
            [
                "",
                "## Analysis settings",
                "",
                f"- IQR multiplier: {settings['iqr_multiplier']}",
                "- Minimum outlier sample size: "
                f"{settings['min_outlier_sample_size']}",
            ]
        )

    lines.extend(
        [
            "",
            "## Column profile",
            "",
            "| Column | Type | Missing | Unique | Mixed | Invalid dates | "
            "Outliers | Issues |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )

    for item in profile["columns"]:
        issues = ", ".join(item["issues"]) if item["issues"] else "none"
        lines.append(
            "| {column} | {dtype} | {missing_count} ({missing_pct:.2f}%) | "
            "{unique_count} | {mixed_numeric_text_count} | "
            "{invalid_date_count} | {outlier_count} | {issues_text} |".format(
                **item,
                issues_text=issues,
            )
        )

    lines.extend(_render_schema_markdown(profile))
    lines.extend(_render_comparison_markdown(profile))

    lines.extend(["", "## Recommendations", ""])
    for recommendation in _recommendations(profile):
        lines.append(f"- {recommendation}")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "The checks in this report are screening rules, not automatic "
            "cleaning instructions. Business context should decide what gets "
            "changed.",
            "",
        ]
    )

    return "\n".join(lines)


def _issue_chart_html(summary):
    issue_counts = [
        ("Duplicate rows", summary["duplicate_rows"]),
        ("Columns with missing values", summary["columns_with_missing"]),
        ("Constant columns", summary["constant_columns"]),
        ("Mixed numeric/text columns", summary["mixed_numeric_text_columns"]),
        (
            "Date columns with invalid values",
            summary["date_columns_with_invalid_values"],
        ),
        (
            "Numeric columns with outliers",
            summary["numeric_columns_with_outliers"],
        ),
    ]
    maximum = max([count for _, count in issue_counts] + [1])

    rows = []
    for label, count in issue_counts:
        width = round((count / maximum) * 100, 1)
        rows.append(
            '<div class="bar-row">'
            f'<div class="bar-label">{escape(label)}</div>'
            '<div class="bar-track">'
            f'<div class="bar-fill" style="width:{width}%"></div>'
            "</div>"
            f'<div class="bar-value">{count}</div>'
            "</div>"
        )

    return "".join(rows)


def _schema_html(profile):
    validation = profile.get("schema_validation")
    if validation is None:
        return ""

    missing = ", ".join(validation["missing_required_columns"]) or "none"
    unexpected = ", ".join(validation["unexpected_columns"]) or "none"

    mismatch_rows = ""
    if validation["type_mismatches"]:
        mismatch_rows = "".join(
            "<tr>"
            f"<td>{escape(item['column'])}</td>"
            f"<td>{escape(item['expected'])}</td>"
            f"<td>{escape(item['actual'])}</td>"
            "</tr>"
            for item in validation["type_mismatches"]
        )
        mismatch_table = (
            "<table><thead><tr><th>Column</th><th>Expected</th>"
            "<th>Actual</th></tr></thead>"
            f"<tbody>{mismatch_rows}</tbody></table>"
        )
    else:
        mismatch_table = "<p>Type mismatches: none</p>"

    status = "passed" if validation["valid"] else "issues found"
    return (
        "<h2>Schema validation</h2>"
        f"<p><strong>Status:</strong> {escape(status)}</p>"
        f"<p><strong>Missing required columns:</strong> {escape(missing)}<br>"
        f"<strong>Unexpected columns:</strong> {escape(unexpected)}</p>"
        f"{mismatch_table}"
    )


def _comparison_html(profile):
    comparison = profile.get("comparison")
    if comparison is None:
        return ""

    added = ", ".join(comparison["added_columns"]) or "none"
    removed = ", ".join(comparison["removed_columns"]) or "none"

    type_rows = "".join(
        "<tr>"
        f"<td>{escape(item['column'])}</td>"
        f"<td>{escape(item['previous'])}</td>"
        f"<td>{escape(item['current'])}</td>"
        "</tr>"
        for item in comparison["type_changes"]
    )
    type_table = (
        "<h3>Type changes</h3>"
        "<table><thead><tr><th>Column</th><th>Previous</th>"
        "<th>Current</th></tr></thead>"
        f"<tbody>{type_rows}</tbody></table>"
        if type_rows
        else ""
    )

    missing_rows = "".join(
        "<tr>"
        f"<td>{escape(item['column'])}</td>"
        f"<td>{item['previous']}</td>"
        f"<td>{item['current']}</td>"
        f"<td>{item['delta']:+}</td>"
        "</tr>"
        for item in comparison["missing_value_changes"]
    )
    missing_table = (
        "<h3>Missing-value changes</h3>"
        "<table><thead><tr><th>Column</th><th>Previous</th>"
        "<th>Current</th><th>Change</th></tr></thead>"
        f"<tbody>{missing_rows}</tbody></table>"
        if missing_rows
        else ""
    )

    return (
        "<h2>Dataset comparison</h2>"
        f"<p><strong>Previous:</strong> "
        f"{escape(comparison['previous_source'])}<br>"
        f"<strong>Current:</strong> {escape(comparison['current_source'])}</p>"
        '<div class="cards">'
        f'<div class="card">Row change<div class="value">'
        f"{comparison['row_delta']:+,}</div></div>"
        f'<div class="card">Column change<div class="value">'
        f"{comparison['column_delta']:+,}</div></div>"
        f'<div class="card">Duplicate-row change<div class="value">'
        f"{comparison['duplicate_row_delta']:+,}</div></div>"
        "</div>"
        f"<p><strong>Added columns:</strong> {escape(added)}<br>"
        f"<strong>Removed columns:</strong> {escape(removed)}</p>"
        f"{type_table}{missing_table}"
    )


def render_html(profile):
    summary = profile["summary"]
    settings = profile.get("settings", {})
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

    settings_html = ""
    if settings:
        settings_html = (
            "<h2>Analysis settings</h2>"
            f"<p>IQR multiplier: <strong>{settings['iqr_multiplier']}</strong>"
            "<br>Minimum outlier sample size: "
            f"<strong>{settings['min_outlier_sample_size']}</strong></p>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data Quality Report</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 1100px; margin: 40px auto; padding: 0 24px; color: #202124; }}
h1, h2, h3 {{ color: #172554; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 24px 0; }}
.card {{ border: 1px solid #d9dee8; border-radius: 10px; padding: 16px; }}
.value {{ font-size: 1.5rem; font-weight: 700; margin-top: 6px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; margin: 12px 0 24px; }}
th, td {{ border-bottom: 1px solid #e5e7eb; padding: 10px; text-align: left; vertical-align: top; }}
th {{ background: #f8fafc; }}
.issue-chart {{ margin: 20px 0 30px; }}
.bar-row {{ display: grid; grid-template-columns: minmax(210px, 1.3fr) 3fr 50px; gap: 12px; align-items: center; margin: 10px 0; }}
.bar-track {{ height: 14px; background: #e5e7eb; border-radius: 999px; overflow: hidden; }}
.bar-fill {{ height: 100%; background: #64748b; border-radius: 999px; min-width: 0; }}
.bar-label {{ font-size: 0.9rem; }}
.bar-value {{ font-weight: 700; text-align: right; }}
.note {{ background: #f8fafc; border-left: 4px solid #64748b; padding: 12px 16px; margin-top: 24px; }}
@media (max-width: 700px) {{
  .bar-row {{ grid-template-columns: 1fr; gap: 5px; }}
  .bar-value {{ text-align: left; }}
  table {{ display: block; overflow-x: auto; }}
}}
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

<h2>Issue overview</h2>
<div class="issue-chart">{_issue_chart_html(summary)}</div>

{settings_html}

<h2>Column profile</h2>
<table>
<thead>
<tr><th>Column</th><th>Type</th><th>Missing</th><th>Unique</th><th>Mixed</th><th>Invalid dates</th><th>Outliers</th><th>Issues</th></tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>

{_schema_html(profile)}
{_comparison_html(profile)}

<h2>Recommendations</h2>
<ul>{recommendation_items}</ul>

<div class="note">
These checks are screening rules, not automatic cleaning instructions. Business context should decide what gets changed.
</div>
</body>
</html>
"""


def render_json(profile):
    payload = {
        "generated_at": _generated_timestamp(),
        "summary": profile["summary"],
        "settings": profile.get("settings", {}),
        "columns": profile["columns"],
    }

    if "schema_validation" in profile:
        payload["schema_validation"] = profile["schema_validation"]

    if "comparison" in profile:
        payload["comparison"] = profile["comparison"]

    payload["recommendations"] = _recommendations(profile)
    return json.dumps(payload, indent=2)


def write_reports(profile, output_dir, stem, report_format="both"):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    written = []

    if report_format in {"md", "both", "all"}:
        markdown_path = output / f"{stem}_report.md"
        markdown_path.write_text(render_markdown(profile), encoding="utf-8")
        written.append(markdown_path)

    if report_format in {"html", "both", "all"}:
        html_path = output / f"{stem}_report.html"
        html_path.write_text(render_html(profile), encoding="utf-8")
        written.append(html_path)

    if report_format in {"json", "all"}:
        json_path = output / f"{stem}_report.json"
        json_path.write_text(render_json(profile), encoding="utf-8")
        written.append(json_path)

    return written
