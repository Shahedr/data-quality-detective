"""Bounded multi-worksheet ingestion for the local workbook auditor.

Reads cell values (not live formulas/macros) from all worksheets, while keeping
a combined workbook limit to avoid silently bypassing the single-sheet cap.
"""

import io
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import pandas as pd
from fastapi import HTTPException

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 200
MAX_SHEETS = 40
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_ZIP_MEMBERS = 2000


def validate_upload(name, data):
    suffix = Path(name).suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xlsm"}:
        raise HTTPException(415, "Supported upload formats: .csv, .xlsx and .xlsm.")
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, "File exceeds the 10 MB prototype upload limit.")
    if suffix == ".csv":
        return suffix
    if not data.startswith(b"PK"):
        raise HTTPException(422, "The Excel workbook is invalid.")

    try:
        with ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if (len(members) > MAX_ZIP_MEMBERS or
                    sum(item.file_size for item in members) > MAX_UNCOMPRESSED_BYTES):
                raise HTTPException(
                    413,
                    "Workbook exceeds the preview's ZIP expansion or member-count limit.",
                )
            for entry in members:
                if entry.flag_bits & 1:
                    raise HTTPException(422, "Encrypted workbook ZIP entries are unsupported.")
    except BadZipFile as exc:
        raise HTTPException(422, "The Excel workbook ZIP data is invalid.") from exc
    return suffix


def parse_sheets(name, data):
    """Return all worksheet DataFrames, in Excel tab order."""
    suffix = validate_upload(name, data)
    try:
        if suffix == ".csv":
            frames = {"CSV data": pd.read_csv(io.BytesIO(data))}
        else:
            with pd.ExcelFile(io.BytesIO(data), engine="openpyxl") as handle:
                if len(handle.sheet_names) > MAX_SHEETS:
                    raise HTTPException(
                        413, f"Prototype allows at most {MAX_SHEETS} Excel worksheets."
                    )
                frames = {
                    sheet: handle.parse(sheet_name=sheet)
                    for sheet in handle.sheet_names
                }
    except HTTPException:
        raise
    except (ValueError, UnicodeError, OSError, EOFError, ImportError, KeyError) as exc:
        raise HTTPException(
            422, "Could not read this dataset. Check its format and encoding."
        ) from exc
    except Exception as exc:
        raise HTTPException(422, "Unable to parse the uploaded dataset.") from exc

    if not frames:
        raise HTTPException(422, "The workbook has no readable worksheets.")
    rows_total = 0
    for frame in frames.values():
        rows_total += len(frame)
        if rows_total > MAX_ROWS or len(frame.columns) > MAX_COLUMNS:
            raise HTTPException(
                413,
                "Prototype limits: 100,000 rows across a workbook, up to "
                "200 columns per sheet, and up to 40 sheets. "
                "The CLI has no fixed row-count limit.",
            )
    return frames, suffix


def select_sheet(frames, sheet):
    if sheet in (None, ""):
        selected = next(iter(frames))
    elif sheet in frames:
        selected = sheet
    else:
        raise HTTPException(422, "Unknown worksheet. Select one of the workbook tabs.")
    return selected, frames[selected]
