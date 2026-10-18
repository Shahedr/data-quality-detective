"""Local browser workbook auditor built on the dqdetect profiling engine.

Prototype only. Do not expose to the public internet without an independent
security review, authentication, upload isolation, and resource controls.
Never execute arbitrary Excel macros or external workbook connections.
"""

import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from dqdetect.profiler import profile_dataframe
from dqdetect.report import render_html, render_json
from webapp.excel import inspect_excel
from webapp.export import full_html_chunks, full_workbook_html_chunks
from webapp.xlsx_export import build_review_workbook, stream_file_chunks
from webapp.inspect import append_annotated_excerpt, inspect_dataframe, ISSUE_FILTERS
from webapp.vba import audit_vba
from webapp.xlsx_export import build_review_workbook, stream_file_chunks
from webapp.workbook import (
    MAX_FILE_BYTES, MAX_ROWS, MAX_COLUMNS, parse_sheets, select_sheet
)

app = FastAPI(
    title="Data Quality Detective",
    description="Local CSV and multi-worksheet XLSX/XLSM quality auditor.",
    version="0.2.0-preview",
    docs_url=None,
    redoc_url=None,
)

_ROOT = Path(__file__).resolve().parent


def _public_demo_only():
    """True ONLY for explicitly configured public sample-only deployments."""
    # Fail closed on Vercel even if project variables are misconfigured.
    return bool(os.environ.get("VERCEL")) or os.environ.get("DQD_PUBLIC_DEMO_ONLY", "").strip() == "1"


def _sample_bytes():
    # Bundled, known example content; demo endpoints never read user uploads.
    return (_ROOT / "sample.csv").read_bytes()


def _review_xlsx_for_frames(frames, reviews, filename):
    profiles = {
        tab: profile_dataframe(frame, source_name=filename)
        for tab, frame in frames.items()
    }
    return build_review_workbook(frames, reviews, profiles, filename)




@app.middleware("http")
async def security_headers(request, call_next):
    if _public_demo_only() and request.url.path in {
        "/api/analyze", "/api/rows", "/api/export/html", "/api/export/xlsx"
    }:
        response = JSONResponse(
            {"detail": "Public preview accepts no uploads. Use the bundled sample; "
             "run the local app to analyze your own workbooks."},
            status_code=403,
        )
    else:
        response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(_ROOT / "static" / "index.html", media_type="text/html")


@app.get("/spreadsheet.js", include_in_schema=False)
def spreadsheet_script():
    return FileResponse(
        _ROOT / "static" / "spreadsheet.js", media_type="application/javascript"
    )


@app.get("/health")
def health():
    return {"status": "ok", "product": "Data Quality Detective", "stage": "preview"}


@app.get("/api/config")
def config():
    public = _public_demo_only()
    return {
        "mode": "public_demo" if public else "local",
        "upload_allowed": not public,
        "macro_execution_via_web": False,
        "public_demo": public,
    }


@app.get("/api/demo/analyze")
def demo_analyze():
    if not _public_demo_only():
        raise HTTPException(404, "Public demo endpoint is disabled locally.")
    return JSONResponse(analyze_bytes("sample.csv", _sample_bytes()))


@app.get("/api/demo/rows")
def demo_rows(page: int = Query(1, ge=1), issue: str = Query("all")):
    if not _public_demo_only():
        raise HTTPException(404, "Public demo endpoint is disabled locally.")
    return JSONResponse(inspect_bytes("sample.csv", _sample_bytes(), page=page, issue=issue))


@app.get("/api/demo/export/html")
def demo_export_html():
    if not _public_demo_only():
        raise HTTPException(404, "Public demo endpoint is disabled locally.")
    frames, _ = parse_sheets("sample.csv", _sample_bytes())
    df = next(iter(frames.values()))
    profile = profile_dataframe(df, source_name="sample.csv")
    return StreamingResponse(
        full_html_chunks(profile, df), media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="sample_full_report.html"'},
    )


@app.get("/api/demo/export/xlsx")
def demo_export_xlsx():
    if not _public_demo_only():
        raise HTTPException(404, "Public demo endpoint is disabled locally.")
    frames, _ = parse_sheets("sample.csv", _sample_bytes())
    output = _review_xlsx_for_frames(frames, {}, "sample.csv")
    return StreamingResponse(
        stream_file_chunks(output),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="sample_audit_review.xlsx"'},
    )



def _read_dataset(name: str, data: bytes, sheet=None, all_reviews=False):
    """Load bounded workbook and review the selected worksheet (or all)."""
    frames, suffix = parse_sheets(name, data)
    selected, df = select_sheet(frames, sheet)
    reviews = {}
    if suffix in {".xlsx", ".xlsm"}:
        sheets_to_check = list(frames) if all_reviews else [selected]
        for tab in sheets_to_check:
            try:
                reviews[tab] = inspect_excel(
                    data, frames[tab],
                    is_xlsm=(suffix == ".xlsm"),
                    worksheet_name=tab,
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=422,
                    detail="Unable to inspect Excel workbook or list validation rules.",
                ) from exc
    return df, reviews.get(selected), frames, selected, suffix, reviews


def _workbook_macro_audit(name, data, review, suffix):
    if suffix not in {".xlsx", ".xlsm"}:
        return None
    if review is None:
        return None
    return audit_vba(
        name, data,
        project_present=review["metadata"]["vba_project_present"]
    )


def analyze_bytes(name: str, data: bytes, sheet=None) -> dict:
    """Build sheet-specific dashboard plus all-sheet overview and VBA triage."""
    df, review, frames, selected, suffix, reviews = _read_dataset(
        name, data, sheet, all_reviews=True
    )
    try:
        profiles = {
            tab: profile_dataframe(frame, source_name=Path(name).name)
            for tab, frame in frames.items()
        }
        profile = profiles[selected]
        report_json = json.loads(render_json(profile))
        overview = []
        for tab, frame in frames.items():
            metadata = reviews[tab]["metadata"] if tab in reviews else None
            overview.append({
                "name": tab,
                "rows": len(frame),
                "columns": len(frame.columns),
                "duplicate_rows": profiles[tab]["summary"]["duplicate_rows"],
                "columns_with_missing": profiles[tab]["summary"]["columns_with_missing"],
                "formula_cells": metadata["formula_cells_count"] if metadata else 0,
                "invalid_dropdown_cells": metadata["dropdown_invalid_cells"] if metadata else 0,
                "excel_tables": metadata["excel_tables"] if metadata else 0,
                "visibility": metadata["worksheet_visibility"] if metadata else "visible",
            })
        macro = _workbook_macro_audit(name, data, review, suffix)
        return {
            "summary": profile["summary"],
            "columns": profile["columns"],
            "recommendations": report_json["recommendations"],
            "report_json": report_json,
            "report_html": append_annotated_excerpt(
                render_html(profile), df,
                dropdown_masks=review["masks"] if review else None,
            ),
            "spreadsheet": inspect_dataframe(
                df, dropdown_masks=review["masks"] if review else None,
            ),
            "workbook": review["metadata"] if review else None,
            "worksheets": overview if suffix in {".xlsx", ".xlsm"} else [],
            "selected_sheet": selected if suffix in {".xlsx", ".xlsm"} else None,
            "workbook_total_rows": sum(len(frame) for frame in frames.values()),
            "vba_audit": macro,
        }
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Could not profile this dataset.") from exc


def inspect_bytes(name: str, data: bytes, page=1, issue="all", sheet=None) -> dict:
    """Reload the chosen sheet for stateless virtual-scrolling page access."""
    if issue not in ISSUE_FILTERS or page < 1:
        raise HTTPException(status_code=422, detail="Invalid page or issue filter.")
    df, review, _, selected, suffix, _ = _read_dataset(name, data, sheet)
    try:
        result = inspect_dataframe(
            df, page=page, issue=issue,
            dropdown_masks=review["masks"] if review else None,
        )
        result["selected_sheet"] = selected if suffix in {".xlsx", ".xlsm"} else None
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _get_upload(file):
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status_code=400, detail="Choose a file to analyze.")
    try:
        data = await file.read(MAX_FILE_BYTES + 1)
    finally:
        await file.close()
    return filename, data


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), sheet: str = Form("")):
    filename, data = await _get_upload(file)
    return JSONResponse(analyze_bytes(filename, data, sheet=sheet))


@app.post("/api/rows")
async def inspect_rows(
    file: UploadFile = File(...),
    page: int = Form(1),
    issue: str = Form("all"),
    sheet: str = Form(""),
):
    filename, data = await _get_upload(file)
    return JSONResponse(inspect_bytes(
        filename, data, page=page, issue=issue, sheet=sheet
    ))


@app.post("/api/export/xlsx")
async def export_review_xlsx(file: UploadFile = File(...)):
    """Download a separate annotated, macro-free review XLSX workbook."""
    filename, data = await _get_upload(file)
    _, review, frames, _, suffix, reviews = _read_dataset(
        filename, data, all_reviews=True
    )
    try:
        profiles = {
            tab: profile_dataframe(frame, source_name=filename)
            for tab, frame in frames.items()
        }
        macro = _workbook_macro_audit(filename, data, review, suffix)
        output = build_review_workbook(frames, reviews, profiles, filename, macro)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422, detail="Unable to build annotated Excel review report."
        ) from exc
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(filename).stem)[:70] or "data"
    return StreamingResponse(
        stream_file_chunks(output),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{stem}_audit_review.xlsx"'},
    )


@app.post("/api/export/html")
async def export_complete_html(file: UploadFile = File(...)):
    """Stream all sheets in a standalone read-only HTML export."""
    filename, data = await _get_upload(file)
    df, review, frames, _, suffix, reviews = _read_dataset(
        filename, data, all_reviews=True
    )
    try:
        profiles = {
            tab: profile_dataframe(frame, source_name=filename)
            for tab, frame in frames.items()
        }
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Could not profile this dataset.") from exc

    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(filename).stem)[:70] or "data"
    if suffix == ".csv":
        stream = full_html_chunks(profiles[next(iter(frames))], df)
    else:
        macro = _workbook_macro_audit(filename, data, review, suffix)
        stream = full_workbook_html_chunks(profiles, frames, reviews, macro)
    return StreamingResponse(
        stream, media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{stem}_full_report.html"'},
    )
