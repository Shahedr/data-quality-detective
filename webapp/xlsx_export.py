"""Generate a separate, safe, color-coded Excel audit workbook.

No source workbook is ever edited. This is a values-only snapshot with an
issue register, not an Excel/VBA replica. Strings (especially those beginning
with '=' or '+' etc.) are forced to literal cells, never executable formulas.
The output is generated with openpyxl write-only sheets to bound memory.
"""
from collections import Counter
from tempfile import TemporaryFile

import pandas as pd
from fastapi import HTTPException
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font, PatternFill

from webapp.inspect import ISSUE_LABELS, prepare_inspection

MAX_EXPORT_CELLS = 1_000_000
MAX_ISSUE_REGISTER_ROWS = 100_000
EXPORT_CHUNK_BYTES = 256 * 1024

_HEADER_FILL = PatternFill("solid", fgColor="DDE8F8")
_DUPLICATE_FILL = PatternFill("solid", fgColor="FFF1E6")
_FLAG_FILLS = {
    "formula_ref": PatternFill("solid", fgColor="FBC7C3"),
    "dropdown_invalid": PatternFill("solid", fgColor="EDDBFD"),
    "missing": PatternFill("solid", fgColor="FFE1DF"),
    "invalid_date": PatternFill("solid", fgColor="FFE5BE"),
    "mixed": PatternFill("solid", fgColor="E5E9FF"),
    "outlier": PatternFill("solid", fgColor="FBE0F1"),
}
_FLAG_PRIORITY = tuple(_FLAG_FILLS)


def _cell(sheet, value, style=None, bold=False):
    """Only literal values, including strings that look like Excel formulas."""
    if value is None:
        raw = None
    else:
        raw = str(value)
        # Excel has a 32767-character cell limit.
        if len(raw) > 32767:
            raw = raw[:32754] + "… [truncated]"
    cell = WriteOnlyCell(sheet, value=raw)
    if raw is not None:
        cell.data_type = "s"  # prevent =HYPERLINK(...), +cmd, etc. injection
    if style is not None:
        cell.fill = style
    if bold:
        cell.font = Font(bold=True, color="22324D")
    return cell


def _safe_title(title, used):
    """Avoid collisions with our special tabs; preserve original titles."""
    candidate = str(title)[:31] or "Sheet"
    stem = candidate[:27]
    count = 2
    while candidate.casefold() in used:
        candidate = (stem + f" ({count})")[:31]
        count += 1
    used.add(candidate.casefold())
    return candidate


def _header(sheet, names):
    sheet.append([_cell(sheet, name, _HEADER_FILL, bold=True) for name in names])


def _validate_size(frames):
    cells = sum((len(df) + 1) * (len(df.columns) + 2) for df in frames.values())
    if cells > MAX_EXPORT_CELLS:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Annotated XLSX export is limited to {MAX_EXPORT_CELLS:,} "
                "worksheet cells to keep memory and processing bounded. "
                "Use Download full HTML spreadsheet for larger files."
            ),
        )


def build_review_workbook(frames, reviews, profiles, source_filename, macro_audit=None):
    """Return an open seekable binary stream, positioned at byte 0.

    Caller owns and must close the stream. Original XLSX/XLSM bytes remain
    completely untouched. Generated XLSX deliberately has no VBA or formulas.
    """
    _validate_size(frames)
    book = Workbook(write_only=True)
    used = {name.casefold() for name in frames}
    summary = book.create_sheet(_safe_title("DQD Audit Overview", used))
    issues = book.create_sheet(_safe_title("DQD Issue Register", used))
    summary.freeze_panes = "B5"
    issues.freeze_panes = "D2"
    summary.append([_cell(summary, "DATA QUALITY DETECTIVE — EXCEL REVIEW", bold=True)])
    summary.append([_cell(summary, "Source file"), _cell(summary, source_filename)])
    summary.append([_cell(summary, "Export type"),
                    _cell(summary, "Value-only review copy; no executable VBA, formulas, dropdown controls, or source formatting")])
    summary.append([_cell(summary, "Important"),
                    _cell(summary, "Flagged values need human review; this does not prove corruption, danger, or mathematical error.")])
    _header(summary, [
        "Worksheet", "Rows", "Columns", "Duplicate copies",
        "Columns with missing data", "Invalid dropdown cells",
        "Broken formula references", "Visibility", "Warnings",
    ])
    _header(issues, [
        "Worksheet", "Data row", "Original Excel cell",
        "Column", "Issue type", "Displayed source value",
    ])
    register_written = 0
    register_omitted = 0
    for title, df in frames.items():
        meta = reviews.get(title, {}).get("metadata") or {}
        masks = prepare_inspection(df, reviews.get(title, {}).get("masks"))
        source_summary = profiles[title]["summary"]
        summary.append([
            _cell(summary, title),
            _cell(summary, len(df)),
            _cell(summary, len(df.columns)),
            _cell(summary, source_summary["duplicate_rows"]),
            _cell(summary, source_summary["columns_with_missing"]),
            _cell(summary, meta.get("dropdown_invalid_cells", 0)),
            _cell(summary, meta.get("broken_formula_refs", 0)),
            _cell(summary, meta.get("worksheet_visibility", "visible")),
            _cell(summary, " | ".join(meta.get("warnings", []))),
        ])
        tab = book.create_sheet(_safe_title(title, used))
        tab.freeze_panes = "C2"
        _header(tab, ["Data row", "Duplicate group", *map(str, df.columns)])
        per_column = masks["column_masks"]
        duplicate = masks["duplicate"]
        for pos in range(len(df)):
            dup = bool(duplicate[pos])
            cells = [
                _cell(tab, pos + 1, _DUPLICATE_FILL if dup else None),
                _cell(tab, "Duplicate group" if dup else None,
                      _DUPLICATE_FILL if dup else None),
            ]
            if dup:
                if register_written < MAX_ISSUE_REGISTER_ROWS:
                    issues.append([
                        _cell(issues, title), _cell(issues, pos + 1),
                        _cell(issues, "—"), _cell(issues, "Entire row"),
                        _cell(issues, ISSUE_LABELS["duplicate"]),
                        _cell(issues, "Repeated row"),
                    ])
                    register_written += 1
                else:
                    register_omitted += 1
            for col in range(len(df.columns)):
                value = df.iat[pos, col]
                blank = bool(pd.isna(value))
                text = None if blank else str(value)
                found = [
                    name for name in _FLAG_PRIORITY
                    if name in per_column[col] and per_column[col][name][pos]
                ]
                # Also account for any future issue kind without changing the export.
                found.extend(
                    name for name, mask in per_column[col].items()
                    if name not in found and name in ISSUE_LABELS
                    and name != "duplicate" and bool(mask[pos])
                )
                fill = _FLAG_FILLS.get(found[0]) if found else None
                cells.append(_cell(tab, text, fill))
                for kind in found:
                    if register_written < MAX_ISSUE_REGISTER_ROWS:
                        from openpyxl.utils.cell import get_column_letter
                        original_ref = get_column_letter(col + 1) + str(pos + 2)
                        issues.append([
                            _cell(issues, title), _cell(issues, pos + 1),
                            _cell(issues, original_ref),
                            _cell(issues, str(df.columns[col])),
                            _cell(issues, ISSUE_LABELS[kind]),
                            _cell(issues, "(blank)" if blank else text),
                        ])
                        register_written += 1
                    else:
                        register_omitted += 1
            tab.append(cells)
    summary.append([_cell(summary, "Issue register entries included"),
                    _cell(summary, register_written)])
    summary.append([_cell(summary, "Issue register entries omitted"),
                    _cell(summary, register_omitted)])
    if macro_audit and macro_audit.get("vba_project_present"):
        summary.append([_cell(summary, "VBA source scan"),
                        _cell(summary, macro_audit["source_scan_status"])])
        summary.append([_cell(summary, "VBA executions in this export"),
                        _cell(summary, "None")])
    if register_omitted:
        issues.append([
            _cell(issues, "IMPORTANT"), _cell(issues, "—"),
            _cell(issues, "—"), _cell(issues, "—"),
            _cell(issues, "Issue register truncated"),
            _cell(issues, f"{register_omitted:,} additional findings not listed; review the source tabs."),
        ])
    output = TemporaryFile(mode="w+b")
    try:
        book.save(output)
        output.seek(0)
    except Exception:
        output.close()
        raise
    finally:
        book.close()
    return output


def stream_file_chunks(fileobj):
    try:
        while chunk := fileobj.read(EXPORT_CHUNK_BYTES):
            yield chunk
    finally:
        fileobj.close()
