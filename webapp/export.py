"""Stream a complete, read-only spreadsheet into a standalone HTML report.

Unlike the JSON dashboard response, this iterates through ALL accepted
data rows, including those with no detected issues. A full HTML table
can be large; use the virtualized web viewer for very wide/large data.
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
.flagged-note{display:block;font-size:.72rem;font-weight:700;margin-top:4px}
.export-note{font-size:.85rem;color:#576781}
.export-meta{padding:12px 16px;border-left:4px solid #718bbf;background:#f2f6ff}
"""


def full_html_chunks(profile, df, workbook=None, dropdown_masks=None):
    """Yield HTML text chunks; do not materialize a huge HTML string."""
    base = render_html(profile)
    base = base.replace("</style>", _STYLES + "\n</style>", 1)
    opening, delimiter, closing = base.partition("</body>")
    if not delimiter:
        raise ValueError("Base HTML report has no closing body tag.")
    yield opening
    yield '<section id="full-spreadsheet"><h2>Full spreadsheet — all rows</h2>'
    yield (
        "<p class=\"export-note\">Every accepted row is included, not just "
        "the first 50 flagged rows. This is a read-only snapshot of loaded "
        "cell values and quality-screening flags. It is not an Excel workbook "
        "and does not contain executable VBA, formulas, or functional dropdowns. "
        "Some very large HTML reports may be slow to open.</p>"
    )
    if workbook:
        yield "<div class=\"export-meta\"><strong>Excel workbook review</strong><ul>"
        yield "<li>Worksheet: " + escape(str(workbook["worksheet_analyzed"])) + "</li>"
        yield (
            "<li>Dropdown/list rules: " + str(workbook["dropdown_rules"])
            + "; unchecked rules: " + str(workbook["dropdown_rules_unchecked"])
            + "; invalid selected cells: " + str(workbook["dropdown_invalid_cells"]) + "</li>"
        )
        yield "<li>VBA code executed: No</li>"
        for warning in workbook["warnings"]:
            yield "<li>" + escape(warning) + "</li>"
        yield "</ul></div>"
    yield "<div class=\"full-grid-wrap\" role=\"region\" tabindex=\"0\" aria-label=\"Scrollable full spreadsheet\">"
    yield '<table class="full-grid"><thead><tr><th class="row-index">Data row</th><th>Duplicate group</th>'
    for column in df.columns:
        yield "<th>" + escape(str(column)) + "</th>"
    yield "</tr></thead><tbody>"

    prepared = prepare_inspection(df, dropdown_masks)
    num_pages = max(1, math.ceil(len(df) / PAGE_SIZE))
    for page in range(1, num_pages + 1):
        chunk = inspect_dataframe(
            df, page=page, issue="all", prepared=prepared, cell_limit=None
        )
        output = []
        for row in chunk["rows"]:
            duplicate = bool(row["row_flags"])
            row_class = ' class="duplicate"' if duplicate else ""
            output.append(f"<tr{row_class}><td class=\"row-index\">{row['row_number']}</td>")
            output.append("<td>" + ("Duplicate group" if duplicate else "") + "</td>")
            for value, flags in zip(row["values"], row["cell_flags"]):
                raw = "(blank)" if value is None else str(value)
                label = "; ".join(ISSUE_LABELS[flag] for flag in flags)
                td_class = f' class="{escape(flags[0], quote=True)}"' if flags else ""
                title = f' title="{escape(label, quote=True)}"' if label else ""
                output.append(f"<td{td_class}{title}>{escape(raw)}")
                if label:
                    output.append(f'<small class="flagged-note">{escape(label)}</small>')
                output.append("</td>")
            output.append("</tr>")
        yield "".join(output)

    yield "</tbody></table></div></section>\n</body>" + closing
