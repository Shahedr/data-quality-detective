"""Read-only, row-level issue inspection for the browser spreadsheet grid.

The screening rules mirror dqdetect.checks. A duplicate *group* highlights
all matching rows, while the summary counts only repeats after the first.
"""

from html import escape
import math

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype

from dqdetect.checks import is_date_like_column


PAGE_SIZE = 50
ISSUE_FILTERS = {
    "all", "flagged", "duplicate", "missing", "mixed", "invalid_date", "outlier",
    "dropdown_invalid", "formula_ref"
}
ISSUE_LABELS = {
    "duplicate": "Duplicate row",
    "formula_ref": "Formula contains broken #REF! reference",
    "missing": "Missing value",
    "mixed": "Mixed numeric/text value",
    "invalid_date": "Invalid date",
    "outlier": "Potential IQR outlier",
    "dropdown_invalid": "Value not in supported dropdown list",
}


def _column_masks(series, column_name):
    """Return boolean masks aligned to positional rows, using existing CLI rules."""
    length = len(series)
    masks = {}

    missing = series.isna().to_numpy(dtype=bool)
    if missing.any():
        masks["missing"] = missing

    if not is_numeric_dtype(series):
        values = series.dropna().astype(str).str.strip()
        values = values[values.ne("")]
        if not values.empty:
            parsed = pd.to_numeric(values, errors="coerce")
            numeric_count = int(parsed.notna().sum())
            text_count = int(parsed.isna().sum())
            if numeric_count and text_count:
                # The minority class is the one the profiler reports; tie -> text.
                minority = parsed.notna() if numeric_count < text_count else parsed.isna()
                mixed = np.zeros(length, dtype=bool)
                mixed[minority[minority].index.to_numpy(dtype=int)] = True
                masks["mixed"] = mixed

    if is_date_like_column(column_name):
        non_null = series.dropna()
        if not non_null.empty:
            parsed_dates = pd.to_datetime(non_null, errors="coerce")
            bad = parsed_dates.isna()
            if bad.any():
                invalid = np.zeros(length, dtype=bool)
                invalid[bad[bad].index.to_numpy(dtype=int)] = True
                masks["invalid_date"] = invalid

    if is_numeric_dtype(series):
        numbers = series.dropna()
        if len(numbers) >= 4:
            q1 = numbers.quantile(0.25, interpolation="linear")
            q3 = numbers.quantile(0.75, interpolation="linear")
            iqr = q3 - q1
            if pd.notna(iqr) and iqr != 0:
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                outliers = ((series < lower) | (series > upper)).fillna(False)
                if outliers.any():
                    masks["outlier"] = outliers.to_numpy(dtype=bool)
    return masks


def prepare_inspection(df, dropdown_masks=None):
    """Compute all issue masks once for page browsing or complete HTML exports."""
    row_count = len(df)
    row_masks = {
        label: np.zeros(row_count, dtype=bool)
        for label in ISSUE_FILTERS - {"all", "flagged"}
    }
    duplicate = df.duplicated(keep=False).to_numpy(dtype=bool)
    row_masks["duplicate"] = duplicate
    column_masks = []
    for idx, name in enumerate(df.columns):
        masks = _column_masks(df.iloc[:, idx], name)
        if dropdown_masks is not None and idx in dropdown_masks:
            additional = dropdown_masks[idx]
            # Accept the historical array-shaped dropdown mask, plus the
            # new per-issue mapping for formula errors and list violations.
            extras = (additional if isinstance(additional, dict)
                      else {"dropdown_invalid": additional})
            for issue_name, extra in extras.items():
                if issue_name not in row_masks or len(extra) != row_count:
                    raise ValueError("Invalid supplemental cell issue mask.")
                if extra.any():
                    masks[issue_name] = extra
        column_masks.append(masks)
        for kind, mask in masks.items():
            row_masks[kind] |= mask

    flagged = np.zeros(row_count, dtype=bool)
    for mask in row_masks.values():
        flagged |= mask
    return {
        "column_masks": column_masks,
        "row_masks": row_masks,
        "flagged": flagged,
        "duplicate": duplicate,
    }


def inspect_dataframe(df, page=1, issue="all", page_size=PAGE_SIZE,
                      dropdown_masks=None, prepared=None, cell_limit=500):
    """Return an annotated page, optionally reusing masks computed once."""
    if not isinstance(page, int) or page < 1:
        raise ValueError("Page must be a positive integer.")
    if issue not in ISSUE_FILTERS:
        raise ValueError("Unknown issue filter.")
    if page_size < 1 or page_size > PAGE_SIZE:
        raise ValueError("Page size must be between 1 and 50.")

    row_count, col_count = df.shape
    masks = prepared if prepared is not None else prepare_inspection(df, dropdown_masks)
    column_masks = masks["column_masks"]
    duplicate = masks["duplicate"]
    flagged = masks["flagged"]
    if issue == "all":
        included = np.arange(row_count, dtype=int)
    elif issue == "flagged":
        included = np.flatnonzero(flagged)
    else:
        included = np.flatnonzero(masks["row_masks"][issue])

    total = int(len(included))
    pages = max(1, math.ceil(total / page_size))
    if page > pages:
        raise ValueError(f"Page {page} exceeds the available {pages} pages.")

    selected = included[(page - 1) * page_size:page * page_size]
    rows = []
    for position in selected:
        values = []
        flags = []
        for column_idx in range(col_count):
            value = df.iat[int(position), column_idx]
            text = None if pd.isna(value) else str(value)
            values.append(
                None if text is None else
                (text[:cell_limit] if cell_limit is not None else text)
            )
            flags.append([
                kind for kind in ISSUE_LABELS
                if kind != "duplicate" and kind in column_masks[column_idx]
                and bool(column_masks[column_idx][kind][position])
            ])
        rows.append({
            "row_number": int(position) + 1,
            "values": values,
            "cell_flags": flags,
            "row_flags": ["duplicate"] if duplicate[position] else [],
        })

    return {
        "columns": [str(name) for name in df.columns],
        "rows": rows,
        "page": page,
        "page_size": page_size,
        "total_matching_rows": total,
        "total_rows": row_count,
        "flagged_rows": int(flagged.sum()),
        "pages": pages,
        "filter": issue,
        "filter_labels": ISSUE_LABELS,
        "truncated_cell_display_at": cell_limit,
    }


def append_annotated_excerpt(html_report, df, dropdown_masks=None):
    """Include actual flagged data in the downloadable HTML, capped at 50 rows."""
    snapshot = inspect_dataframe(df, page=1, issue="flagged", dropdown_masks=dropdown_masks)
    heading = (
        "<h2>Highlighted data excerpt</h2>"
        "<p>Flags identify values to review, not proven errors. "
        "Data row numbers start at 1 and exclude the header. "
        "Duplicate groups highlight every matching row, "
        "while the summary counts only additional occurrences.</p>"
    )
    if not snapshot["total_matching_rows"]:
        excerpt = heading + "<p>No row-level issues detected.</p>"
    else:
        shown = len(snapshot["rows"])
        note = (
            f"<p>Showing {shown:,} of "
            f"{snapshot['total_matching_rows']:,} flagged rows. "
            "Use the browser app to browse all flagged rows.</p>"
        )
        columns = snapshot["columns"]
        table = [
            '<div style="overflow-x:auto"><table>',
            '<thead><tr><th>Data row</th><th>Row issue</th>',
            *[f"<th>{escape(name)}</th>" for name in columns],
            "</tr></thead><tbody>",
        ]
        for row in snapshot["rows"]:
            duplicate = bool(row["row_flags"])
            bg = ' style="background:#fff7ed"' if duplicate else ""
            table.append(f"<tr{bg}><td>{row['row_number']}</td>")
            table.append(
                "<td>" + ("Duplicate row" if duplicate else "") + "</td>"
            )
            for value, flags in zip(row["values"], row["cell_flags"]):
                text = escape("(blank)" if value is None else value)
                if flags:
                    labels = ", ".join(ISSUE_LABELS[label] for label in flags)
                    safe_labels = escape(labels, quote=True)
                    table.append(
                        f'<td style="background:#fef3c7" title="{safe_labels}">'
                        f"<strong>{text}</strong><small> — {escape(labels)}</small></td>"
                    )
                else:
                    table.append(f"<td>{text}</td>")
            table.append("</tr>")
        table.append("</tbody></table></div>")
        excerpt = heading + note + "".join(table)
    return html_report.replace("</body>", excerpt + "\n</body>")
