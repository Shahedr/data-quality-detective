"""Stateless workspace tools. Original bytes are never modified or retained."""
import hashlib
import io
import math
import re
from datetime import datetime
from zipfile import ZipFile

import pandas as pd
from fastapi import HTTPException
from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal

from webapp.workbook import parse_sheets, select_sheet
from webapp.xlsx_export import MAX_EXPORT_CELLS


class CleanOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    sheet: str = ""
    columns: list[str] = Field(default_factory=list, max_length=200)
    trim: bool = False
    case: Literal["keep", "lower", "upper"] = "keep"
    date_format: Literal["", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"] = ""
    remove_duplicates: bool = False


def clean_options(raw):
    if len(raw) > 20000:
        raise HTTPException(422, "Cleaning options are too large.")
    try:
        return CleanOptions.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(422, "Invalid cleaning options.") from exc


def clean_frames(name, data, options):
    """Preserve CSV strings, blanks and IDs; transform only explicitly chosen columns."""
    bounded, suffix = parse_sheets(name, data)
    if suffix == ".csv":
        frames = {"CSV data": pd.read_csv(io.BytesIO(data), dtype=str, na_filter=False)}
    else:
        # Values-only copies intentionally do not retain formulas, formatting or VBA.
        frames = pd.read_excel(io.BytesIO(data), sheet_name=None, dtype=object,
                               keep_default_na=False, engine="openpyxl")
    selected, original = select_sheet(frames, options.sheet)
    if list(frames) != list(bounded) or any(frames[k].shape != bounded[k].shape for k in frames):
        raise HTTPException(422, "Workbook structure changed during import.")
    labels = [str(c) for c in original.columns]
    if (len(set(options.columns)) != len(options.columns) or
            any(labels.count(c) != 1 for c in options.columns)):
        raise HTTPException(422, "Select unique, existing column names.")
    if (options.trim or options.case != "keep" or options.date_format) and not options.columns:
        raise HTTPException(422, "Select at least one column to transform.")
    result = original.copy(deep=True)
    changes, changed_count, invalid_dates = [], 0, 0
    for column in options.columns:
        col = labels.index(column)
        for row, old in enumerate(original.iloc[:, col]):
            new = old
            if isinstance(new, str):
                if options.trim:
                    new = new.strip()
                if options.case != "keep":
                    new = new.lower() if options.case == "lower" else new.upper()
                if options.date_format and new:
                    try:
                        parsed = datetime.strptime(new, options.date_format)
                        new = parsed.strftime("%Y-%m-%d")
                    except ValueError:
                        invalid_dates += 1
            if isinstance(old, str) and new != old:
                changed_count += 1
                result.iat[row, col] = new
                if len(changes) < 100:
                    changes.append({"row": row + 2, "column": str(column),
                                    "before": str(old)[:500], "after": str(new)[:500]})
    duplicates = result.duplicated(keep="first") if options.remove_duplicates else pd.Series(False, index=result.index)
    removed = int(duplicates.sum())
    frames[selected] = result.loc[~duplicates].reset_index(drop=True)
    canonical = options.model_dump_json()
    fingerprint = hashlib.sha256(data + name.encode() + canonical.encode()).hexdigest()
    return frames, {
        "fingerprint": fingerprint, "sheet": selected, "rows_before": len(original),
        "rows_after": len(frames[selected]), "cells_changed": changed_count,
        "duplicates_removed": removed, "removed_source_rows": (duplicates[duplicates].index + 2).tolist()[:100],
        "invalid_dates_unchanged": invalid_dates, "changes": changes,
        "preview_truncated": changed_count > 100 or removed > 100,
        "notice": "Download is a separate values-only XLSX copy of every worksheet. Hidden sheets become visible. Formulas, macros, formatting, links and controls are not preserved. Invalid dates stay unchanged. Duplicate removal keeps the first full-row match after transformations, on the selected sheet only.",
    }


def cleaned_workbook(frames):
    if sum((len(df) + 1) * len(df.columns) for df in frames.values()) > MAX_EXPORT_CELLS:
        raise HTTPException(413, "Cleaned export exceeds the 1,000,000-cell limit.")
    # Validate before opening write-only XML streams: never emit a partial file.
    for frame in frames.values():
        for row in [list(frame.columns)]:
            for value in row:
                validate_excel_value(value)
        for row in frame.itertuples(index=False, name=None):
            for value in row:
                validate_excel_value(value)
    book = Workbook(write_only=True)
    output = io.BytesIO()
    for name, frame in frames.items():
        sheet = book.create_sheet(name)
        for row in [list(frame.columns)]:
            sheet.append([literal_cell(sheet, v) for v in row])
        for row in frame.itertuples(index=False, name=None):
            sheet.append([literal_cell(sheet, v) for v in row])
    book.save(output)
    output.seek(0)
    return output


def literal_cell(sheet, value):
    if pd.isna(value):
        value = None
    cell = WriteOnlyCell(sheet, value=value)
    if isinstance(value, str):
        cell.data_type = "s"
    return cell


def validate_excel_value(value):
    if isinstance(value, str) and (len(value) > 32767 or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", value)):
        raise HTTPException(422, "A cell cannot be represented safely in Excel. No cleaned file was generated.")


def explore(frame):
    """Bounded chart aggregates, with no raw dataset sent to a chart service."""
    columns = []
    for name in frame.columns:
        series = frame[name]
        entry = {"column": str(name), "missing": int(series.isna().sum()), "total": len(series)}
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            values = pd.to_numeric(series, errors="coerce").dropna()
            values = values[values.map(math.isfinite)]
            if len(values):
                import numpy as np
                if values.nunique() == 1:
                    entry["distribution"] = [{"label": f"{values.iloc[0]:.4g}", "count": len(values)}]
                    columns.append(entry)
                    continue
                # Normalize finite extremes to avoid overflow in histogram range arithmetic.
                scale = max(float(values.abs().max()), 1.0)
                counts, edges = np.histogram(values.to_numpy(dtype=float) / scale, bins=min(8, max(1, values.nunique())))
                edges = edges * scale
                entry["distribution"] = [{"label": f"{edges[i]:.4g} – {edges[i+1]:.4g}", "count": int(count)} for i, count in enumerate(counts)]
        else:
            counts = series.dropna().astype(str).value_counts().head(8)
            entry["common_values"] = [{"label": str(v)[:100], "count": int(n)} for v, n in counts.items()]
        columns.append(entry)
    return columns


def workbook_health(name, data):
    if not name.lower().endswith((".xlsx", ".xlsm")):
        return {"available": False, "notice": "Workbook health applies to XLSX/XLSM files."}
    book = load_workbook(io.BytesIO(data), read_only=True, data_only=False, keep_links=False)
    findings, total_errors, broken, formula_count = [], 0, 0, 0
    try:
        sheets = []
        for sheet in book:
            sheets.append({"name": sheet.title, "visibility": sheet.sheet_state})
            for row in sheet.iter_rows():
                for cell in row:
                    kind = None
                    if cell.data_type == "f":
                        formula_count += 1
                        if "#REF!" in str(cell.value):
                            broken += 1
                            kind = "Broken formula reference"
                    elif cell.data_type == "e":
                        total_errors += 1
                        kind = "Saved Excel error: " + str(cell.value)
                    if kind and len(findings) < 100:
                        findings.append({"sheet": sheet.title, "cell": cell.coordinate, "finding": kind})
        with ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            external_links = sum(bool(re.fullmatch(r"xl/externalLinks/externalLink\d+\.xml", p)) for p in names)
            macro = any(p.lower().endswith("/vbaproject.bin") for p in names)
        return {"available": True, "sheets": sheets, "formulas": formula_count,
                "broken_references": broken, "saved_errors": total_errors,
                "external_link_parts": external_links, "macro_present": macro,
                "findings": findings, "findings_truncated": broken + total_errors > 100,
                "notice": "Static inspection only. External-link parts are counted, never opened. Formulas are not recalculated. Macro presence is not a safety verdict. Only stored Excel error cells and explicit #REF! formulas are detected."}
    finally:
        book.close()


TEMPLATES = {
    "sales": [("order_id", "Order ID", "unique"), ("order_date", "Order date", "date"), ("quantity", "Quantity", "positive"), ("unit_price", "Unit price", "nonnegative")],
    "inventory": [("sku", "SKU", "unique"), ("quantity", "Stock quantity", "nonnegative"), ("reorder_level", "Reorder level", "nonnegative")],
    "customers": [("customer_id", "Customer ID", "unique"), ("email", "Email", "email"), ("name", "Customer name", "required")],
}

ALIASES = {
    "order_id": ["order id", "order number", "order no", "invoice number"],
    "order_date": ["order date", "purchase date", "invoice date", "date of order"],
    "quantity": ["quantity", "qty", "units", "stock quantity", "stock on hand"],
    "unit_price": ["unit price", "price per unit", "item price", "price"],
    "sku": ["sku", "product code", "item code", "stock keeping unit"],
    "reorder_level": ["reorder level", "reorder point", "minimum stock", "min stock"],
    "customer_id": ["customer id", "customer number", "client id", "client number"],
    "email": ["email", "email address", "e mail", "customer email"],
    "name": ["name", "full name", "customer name", "client name"],
}

RULE_LABELS = {
    "unique": "must be filled in and unique", "required": "must be filled in",
    "date": "must match the selected date format", "positive": "must be a number greater than zero",
    "nonnegative": "must be a number zero or greater", "email": "must have a basic email format",
}


def template_definitions():
    return {name: [{"key": key, "label": label, "rule": rule} for key, label, rule in rules]
            for name, rules in TEMPLATES.items()}


class AuditMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    columns: dict[str, str] = Field(default_factory=dict, max_length=20)
    date_format: Literal["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"] = "%Y-%m-%d"


def parse_audit_mapping(raw):
    if len(raw) > 20000:
        raise HTTPException(422, "Audit mapping is too large.")
    try:
        return AuditMapping.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(422, "Invalid audit mapping or date format.") from exc


def suggest_mapping(columns, template):
    normalize = lambda value: re.sub(r"[^a-z0-9]", "", str(value).casefold())
    mapping = {}
    for key, _, _ in TEMPLATES[template]:
        names = {normalize(key), *(normalize(alias) for alias in ALIASES[key])}
        matches = [str(c) for c in columns if normalize(c) in names]
        mapping[key] = matches[0] if len(matches) == 1 else ""
    # A suggestion must not silently use a source column for two meanings.
    return {key: value if list(mapping.values()).count(value) == 1 else "" for key, value in mapping.items()}


def template_audit(frame, template, mapping=None):
    if template not in TEMPLATES:
        raise HTTPException(422, "Unknown audit template.")
    mapping = mapping or AuditMapping()
    keys = {key for key, _, _ in TEMPLATES[template]}
    if set(mapping.columns) - keys:
        raise HTTPException(422, "Mapping contains fields outside the selected template.")
    selected = {**suggest_mapping(frame.columns, template), **mapping.columns}
    labels = [str(c) for c in frame.columns]
    chosen = [c for c in selected.values() if c]
    if len(chosen) != len(set(chosen)) or any(labels.count(c) != 1 for c in chosen):
        raise HTTPException(422, "Map each audit field to a distinct, existing column.")
    results = []
    for key, label, rule in TEMPLATES[template]:
        column = selected[key]
        if not column:
            results.append({"field": key, "column": "", "rule": label, "status": "not_checked", "message": "Choose the matching column below, or leave this check unapplied. No column renaming is needed."})
            continue
        series = frame.iloc[:, labels.index(column)]
        blank = series.isna() | series.astype(str).str.strip().eq("")
        invalid = blank.copy()
        if rule == "unique":
            invalid |= series.duplicated(keep=False)
        elif rule == "date":
            # Explicit ISO date rules avoid silently swapping month/day.
            parsed = pd.to_datetime(series.astype(str), format=mapping.date_format, errors="coerce")
            invalid |= parsed.isna()
        elif rule in {"positive", "nonnegative"}:
            numeric = pd.to_numeric(series, errors="coerce")
            invalid |= numeric.isna() | ~numeric.map(lambda v: math.isfinite(v) if pd.notna(v) else False)
            invalid |= numeric.le(0) if rule == "positive" else numeric.lt(0)
        elif rule == "email":
            invalid |= ~series.astype(str).str.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+")
        results.append({"field": key, "column": column, "rule": label + ": " + RULE_LABELS[rule],
                        "status": "review" if invalid.any() else "passed", "count": int(invalid.sum()),
                        "source_rows": (invalid[invalid].index + 2).tolist()[:100]})
    return results


def narrative(profile, health, template, checks):
    summary = profile["summary"]
    lines = ["DATA QUALITY REVIEW", f"Source: {summary['source']}",
             f"Selected worksheet: {summary['rows']:,} data rows and {summary['columns']} columns.",
             f"{summary['duplicate_rows']} extra duplicate row(s); {summary['columns_with_missing']} column(s) contain missing values."]
    for col in profile["columns"]:
        if col["issues"]:
            lines.append(f"Review {col['column']}: {', '.join(col['issues'])}.")
    if health["available"]:
        lines.append(f"Workbook: {len(health['sheets'])} sheets, {health['formulas']} formula cells, {health['broken_references']} explicit broken references, {health['saved_errors']} saved Excel errors, {health['external_link_parts']} external link parts. VBA present: {health['macro_present']}.")
    if checks:
        lines.append(f"Audit template: {template}. These are screening rules, not business or regulatory certification.")
        lines.append(f"Coverage: {sum(c['status'] != 'not_checked' for c in checks)} of {len(checks)} template checks applied. Unmapped fields were not assessed.")
        for check in checks:
            lines.append(f"{check['column'] or check.get('field', 'Unmapped field')}: {check['status']}" + (f" — {check['count']} row(s) to review." if "count" in check else " — no source column mapped."))
    lines.extend(["Review findings with the data owner before using the data for reporting. Outliers and duplicates can be legitimate.", "This report does not establish financial impact, completeness, security, or compliance. Formulas and VBA were not executed. Original files are unchanged."])
    return "\n\n".join(lines)
