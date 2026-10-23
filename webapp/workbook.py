"""Bounded multi-worksheet ingestion for the local workbook auditor.

Reads cell values (not live formulas/macros) from all worksheets, while keeping
a combined workbook limit to avoid silently bypassing the single-sheet cap.
"""

import io
import csv
import posixpath
import hashlib
import threading
from collections import OrderedDict
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from fastapi import HTTPException
from defusedxml.sax import make_parser
from defusedxml import ElementTree as ET
from webapp.largeworkbook import CheckedReader, SheetOverview
from webapp.zipguard import check_directory

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 200
MAX_SHEETS = 40
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_ZIP_MEMBERS = 2000
MAX_CELLS = 1_000_000
_validated = OrderedDict()
_validation_lock = threading.Lock()


def validate_upload(name, data):
    suffix = Path(name).suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xlsm"}:
        raise HTTPException(415, "Supported upload formats: .csv, .xlsx and .xlsm.")
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, "File exceeds the 10 MB prototype upload limit.")
    if suffix == ".csv":
        # Check dimensions before pandas allocates a rectangular table.
        csv.field_size_limit(1024*1024)
        try:
            with io.TextIOWrapper(io.BytesIO(data), encoding='utf-8-sig', newline='') as source:
                rows = csv.reader(source, strict=True)
                columns = None
                count = 0
                for row in rows:
                    if not row:
                        continue
                    if columns is None:
                        columns = len(row)
                    else:
                        count += 1
                        columns = max(columns, len(row))
                    if len(row) > MAX_COLUMNS or count > MAX_ROWS or (count+1)*max(columns, len(row)) > MAX_CELLS:
                        raise HTTPException(413, 'Detailed CSV workspace exceeds its row, column or 1,000,000-cell limit. Use large-file processing.')
        except (UnicodeError, csv.Error) as exc:
            raise HTTPException(422, 'Unable to read bounded UTF-8 CSV data.') from exc
        return suffix
    if not data.startswith(b"PK"):
        raise HTTPException(422, "The Excel workbook is invalid.")

    # Cache only validation hashes, never workbook contents or analysis results.
    cache_key = (hashlib.sha256(data).digest(), MAX_ROWS, MAX_COLUMNS, MAX_SHEETS,
                 MAX_CELLS, MAX_UNCOMPRESSED_BYTES, MAX_ZIP_MEMBERS)
    with _validation_lock:
        if cache_key in _validated:
            _validated.move_to_end(cache_key)
            return suffix

    try:
        check_directory(io.BytesIO(data), MAX_ZIP_MEMBERS, 2*1024**2)
        with ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(set(archive.namelist())) != len(members):
                raise ValueError('Duplicate workbook package parts')
            if (len(members) > MAX_ZIP_MEMBERS or
                    sum(item.file_size for item in members) > MAX_UNCOMPRESSED_BYTES):
                raise HTTPException(
                    413,
                    "Workbook exceeds the preview's ZIP expansion or member-count limit.",
                )
            for entry in members:
                if entry.flag_bits & 1:
                    raise HTTPException(422, "Encrypted workbook ZIP entries are unsupported.")
                if entry.filename.endswith('.xml') and not entry.filename.startswith('xl/worksheets/') and entry.file_size > 16*1024**2:
                    raise HTTPException(413, 'Workbook metadata exceeds the detailed workspace limit. Use large-file processing.')
            metadata = 'xl/_rels/workbook.xml.rels'
            if archive.getinfo(metadata).file_size > 1024**2:
                raise ValueError('Workbook metadata exceeds limit')
            relations = {r.attrib['Id']: r for r in ET.fromstring(archive.read(metadata))}
            if archive.getinfo('xl/workbook.xml').file_size > 1024**2:
                raise ValueError('Workbook metadata exceeds limit')
            namespace = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for sheet in ET.fromstring(archive.read('xl/workbook.xml')).findall('m:sheets/m:sheet', namespace):
                relation = relations[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
                target = relation.attrib['Target']
                target = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/'+target)
                kind = relation.attrib.get('Type', '').rsplit('/', 1)[-1]
                expected = 'xl/worksheets/' if kind == 'worksheet' else 'xl/chartsheets/' if kind == 'chartsheet' else None
                if relation.attrib.get('TargetMode') == 'External' or not expected or not target.startswith(expected):
                    raise ValueError('Unsupported worksheet location or relationship')
            rows = sheets = cells = 0
            for entry in members:
                if entry.filename.startswith('xl/worksheets/') and entry.filename.endswith('.xml'):
                    sheets += 1
                    if sheets > MAX_SHEETS:
                        raise HTTPException(413, 'Worksheet count exceeds the workspace limit.')
                    overview = SheetOverview(MAX_ROWS+1, MAX_COLUMNS)
                    parser = make_parser()
                    parser.setContentHandler(overview)
                    with archive.open(entry) as source:
                        parser.parse(CheckedReader(source, lambda: None))
                    rows += max(0, overview.max_row-1)
                    cells += overview.max_row*max(1, overview.columns)
                    if cells > MAX_CELLS:
                        raise HTTPException(413, 'Detailed workspace allows at most 1,000,000 cells. Use large-file processing.')
                    if rows > MAX_ROWS:
                        raise HTTPException(413, 'Row limit exceeded across a workbook.')
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(422, 'Workbook package or worksheet exceeds safe ingestion limits.') from exc
    with _validation_lock:
        _validated[cache_key] = True
        if len(_validated) > 32:
            _validated.popitem(last=False)
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
