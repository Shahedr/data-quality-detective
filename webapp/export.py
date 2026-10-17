"""Stream complete annotated HTML reports for CSVs or multi-sheet workbooks.

Reports are read-only snapshots. They never contain executable VBA, workbook
formula logic, or external scripts. All user-supplied text is HTML-escaped.
"""

from html import escape
import math

from dqdetect.report import render_html
from webapp.inspect import ISSUE_LABELS, PAGE_SIZE, inspect_dataframe, prepare_inspection

_STYLES = """
.full-grid-wrap{border:1px solid #d7dfed;border-radius:10px;overflow:auto;
  max-height:75vh;background:white}
.full-grid{min-width:max-content;border-collapse:separate;border-spacing:0}
.full-grid th{position:sticky;top:0;background:#eaf1fc;z-index:2}
.full-grid td,.full-grid th{border-right:1px solid #e9edf5;min-width:100px;
  max-width:420px;overflow-wrap:anywhere}
.full-grid .row-index{position:sticky;left:0;background:#eef3fa;z-index:3;
  font-variant-numeric:tabular-nums}
.full-grid tr.duplicate .row-index{background:#fff0ed;color:#963c27}
.full-grid td.missing{background:#ffeded}
.full-grid td.invalid_date{background:#fff0db}
.full-grid td.mixed{background:#edf0ff}
.full-grid td.outlier{background:#ffeffa}
.full-grid td.dropdown_invalid{background:#f5eaff}
.full-grid td.formula_ref{background:#fee9e4}
.flagged-note{display:block;font-size:.72rem;font-weight:700;margin-top:4px}
.export-note{font-size:.85rem;color:#576781}
.export-meta{padding:12px 16px;border-left:4px solid #718bbf;background:#f2f6ff}
.sheet-separator{margin:28px 0;border-top:3px solid #dfe6f5;padding-top:15px}
"""


def _open_html(profile):
    base = render_html(profile).replace("</style>", _STYLES + "\n</style>", 1)
    opening, delimiter, closing = base.partition("</body>")
    if not delimiter:
        raise ValueError("Base HTML report has no closing body tag.")
    return opening, closing


def _grid_chunks(df, workbook=None, dropdown_masks=None, sheet_name=None):
    if sheet_name is not None:
        yield ('<section class="sheet-separator" id="sheet-' +
               escape(str(sheet_name), quote=True) + '"><h2>Worksheet: ' +
               escape(str(sheet_name)) + '</h2>')
    else:
        yield '<section id="full-spreadsheet"><h2>Full spreadsheet — all rows</h2>'
    yield (
        '<p class="export-note">Every accepted row is included. This is a '
        "read-only diagnostic snapshot, not a spreadsheet program. "
        "VBA, cell formulas, functional dropdown controls, styles and "
        "conditional-formatting behavior are not reproduced.</p>"
    )
    if workbook:
        yield '<div class="export-meta"><strong>Excel worksheet review</strong><ul>'
        yield "<li>Worksheet: " + escape(str(workbook["worksheet_analyzed"])) + "</li>"
        yield (
            "<li>Dropdown/list rules: " + str(workbook["dropdown_rules"])
            + "; unchecked rules: " + str(workbook["dropdown_rules_unchecked"])
            + "; invalid selected cells: " + str(workbook["dropdown_invalid_cells"]) + "</li>"
        )
        yield "<li>Formulas: " + str(workbook.get("formula_cells_count", 0)) + "</li>"
        yield "<li>Excel tables: " + str(workbook.get("excel_tables", 0)) + "</li>"
        yield "<li>VBA code executed: No</li>"
        for warning in workbook["warnings"]:
            yield "<li>" + escape(warning) + "</li>"
        yield "</ul></div>"
    yield '<div class="full-grid-wrap" role="region" tabindex="0" aria-label="Scrollable full spreadsheet">'
    yield '<table class="full-grid"><thead><tr><th class="row-index">Data row</th><th>Duplicate group</th>'
    for column in df.columns:
        yield "<th>" + escape(str(column)) + "</th>"
    yield "</tr></thead><tbody>"

    prepared = prepare_inspection(df, dropdown_masks)
    num_pages = max(1, math.ceil(len(df) / PAGE_SIZE))
    for page in range(1, num_pages + 1):
        snapshot = inspect_dataframe(
            df, page=page, issue="all", prepared=prepared, cell_limit=None
        )
        parts = []
        for row in snapshot["rows"]:
            duplicate = bool(row["row_flags"])
            row_class = ' class="duplicate"' if duplicate else ""
            parts.append(f'<tr{row_class}><td class="row-index">{row["row_number"]}</td>')
            parts.append("<td>" + ("Duplicate group" if duplicate else "") + "</td>")
            for value, flags in zip(row["values"], row["cell_flags"]):
                raw = "(blank)" if value is None else str(value)
                label = "; ".join(ISSUE_LABELS[flag] for flag in flags)
                td_class = f' class="{escape(flags[0], quote=True)}"' if flags else ""
                title = f' title="{escape(label, quote=True)}"' if label else ""
                parts.append(f"<td{td_class}{title}>{escape(raw)}")
                if label:
                    parts.append(f'<small class="flagged-note">{escape(label)}</small>')
                parts.append("</td>")
            parts.append("</tr>")
        yield "".join(parts)
    yield "</tbody></table></div></section>"


def full_html_chunks(profile, df, workbook=None, dropdown_masks=None):
    """Backward-compatible single-sheet full HTML export."""
    opening, closing = _open_html(profile)
    yield opening
    yield from _grid_chunks(df, workbook, dropdown_masks)
    yield "\n</body>" + closing


def full_workbook_html_chunks(profiles, frames, reviews, vba_audit=None):
    """Stream every worksheet of a workbook in Excel tab order."""
    first = next(iter(profiles))
    opening, closing = _open_html(profiles[first])
    yield opening
    yield "<h2>Full spreadsheet — all rows, all worksheets</h2>"
    yield "<h3>Workbook overview — all worksheets</h3>"
    yield (
        "<p>This export covers all analyzed worksheets, including hidden "
        "worksheets; they may contain sensitive data. "
        "Each table is a read-only value snapshot.</p>"
    )
    yield "<ul>"
    for sheet, frame in frames.items():
        meta = reviews[sheet]["metadata"]
        yield (
            "<li>" + escape(sheet) + " — "
            + str(len(frame)) + " rows, " + str(len(frame.columns)) + " columns"
            + "; visibility: " + escape(str(meta["worksheet_visibility"])) + "</li>"
        )
    yield "</ul>"
    if vba_audit:
        yield "<h2>VBA static audit (no execution)</h2>"
        yield "<p>Scan status: " + escape(vba_audit["source_scan_status"]) + "</p>"
        yield "<p>" + escape(vba_audit["limitations"]) + "</p>"
        for module in vba_audit["modules"]:
            yield ("<p>Module: " + escape(module["name"]) + " ("
                   + str(module["source_lines"]) + " source lines)</p>")
        for finding in vba_audit["findings"]:
            yield (
                "<p>[" + escape(finding["category"]) + "] "
                + escape(finding["keyword"]) + " — "
                + escape(finding["explanation"]) + "</p>"
            )
    for sheet, frame in frames.items():
        review = reviews[sheet]
        yield from _grid_chunks(
            frame,
            workbook=review["metadata"],
            dropdown_masks=review["masks"],
            sheet_name=sheet,
        )
    yield "\n</body>" + closing
