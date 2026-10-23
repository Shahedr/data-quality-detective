"""Free web interface to the dqdetect quality profiler.

CSV/Excel inputs are parsed as data only; macros, formulas and external Excel
connections are never executed by the web service. The public service is an
untrusted-file processing endpoint with strict input limits.
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
from webapp.workspace import (
    clean_options, clean_frames, cleaned_workbook, explore, workbook_health,
    template_audit, narrative,
    parse_audit_mapping, template_definitions,
)
from webapp.preserve import preserve_workbook
from webapp.largefiles import router as largefile_router, lifespan as largefile_lifespan
from webapp.workbook import (
    MAX_FILE_BYTES, MAX_ROWS, MAX_COLUMNS, parse_sheets, select_sheet
)

app = FastAPI(
    lifespan=largefile_lifespan,
    title="Data Quality Detective",
    description="Local CSV and multi-worksheet XLSX/XLSM quality auditor.",
    version="0.2.0-preview",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(largefile_router)

_ROOT = Path(__file__).resolve().parent


def _public_demo_only():
    """True ONLY for explicitly configured public sample-only deployments."""
    # Old DQD_PUBLIC_DEMO_ONLY settings from the prior paid-era preview must
    # never silently disable the public free webapp on Vercel.
    if os.getenv("VERCEL"):
        return os.getenv("DQD_FREE_UPLOADS_DISABLED", "").strip() == "1"
    return os.getenv("DQD_PUBLIC_DEMO_ONLY", "").strip() == "1"


def _sample_bytes():
    # Bundled, known example content; demo endpoints never read user uploads.
    return (_ROOT / "sample.csv").read_bytes()


def _review_xlsx_for_frames(frames, reviews, filename):
    profiles = {
        tab: profile_dataframe(frame, source_name=filename)
        for tab, frame in frames.items()
    }
    return build_review_workbook(frames, reviews, profiles, filename)




# Vercel's request-body limit is lower than the local 10 MB file limit.
# Cap the full multipart request BEFORE Starlette spools uploaded bytes to disk.
HOSTED_MAX_FILE_BYTES = 4 * 1024 * 1024
HOSTED_MAX_REQUEST_BYTES = HOSTED_MAX_FILE_BYTES + 64 * 1024
_UPLOAD_PATHS = frozenset({
    "/api/analyze", "/api/rows", "/api/export/html", "/api/export/xlsx",
    "/api/workspace", "/api/clean/preview", "/api/clean/export", "/api/large/uploads"
})


@app.middleware("http")
async def security_headers(request, call_next):
    path = request.url.path
    upload_path = path in _UPLOAD_PATHS or bool(re.fullmatch(r'/api/large/uploads/[A-Za-z0-9_-]+/download', path))
    if (not os.getenv('VERCEL') and (not request.client or
            request.client.host not in {'127.0.0.1', '::1', 'testclient'} or
            request.url.hostname not in {'127.0.0.1', 'localhost', '::1', 'testserver'})):
        response = JSONResponse({'detail': 'Local server accepts loopback requests only.'}, status_code=403)
    elif (request.method in {'POST', 'PUT', 'DELETE'} and request.headers.get('origin') and
          request.headers['origin'] != str(request.base_url).rstrip('/')):
        response = JSONResponse({'detail': 'Cross-origin requests are not allowed.'}, status_code=403)
    elif upload_path and request.method == "POST" and _public_demo_only():
        response = JSONResponse(
            {"detail": "Sample-only mode is enabled; uploads are unavailable."},
            status_code=403,
        )
    elif upload_path and request.method == "POST":
        limit = HOSTED_MAX_REQUEST_BYTES if os.getenv('VERCEL') else MAX_FILE_BYTES + 64 * 1024
        if path == '/api/large/uploads' or path.endswith('/download'):
            limit = 8192
        length = request.headers.get("content-length", "")
        if not length.isascii() or not length.isdecimal():
            response = JSONResponse({"detail": "Content-Length is required."}, status_code=411)
        elif int(length) > limit:
            response = JSONResponse(
                {"detail": "Public web uploads are limited to 4 MB." if os.getenv('VERCEL') else
                 "Use the chunked large-file route for files above 10 MiB."}, status_code=413
            )
        else:
            # Bound actual bytes before multipart parsing, even for a false Content-Length.
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > limit:
                    break
                body.extend(chunk)
            else:
                request._body = bytes(body)
                response = await call_next(request)
                body = None
            if body is not None:
                response = JSONResponse({'detail': 'Request body exceeds upload limit.'}, status_code=413)
    else:
        response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    # Native same-origin POST downloads need an Origin; no-referrer can make it null.
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "base-uri 'none'; object-src 'none'; frame-ancestors 'none'"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if os.getenv('VERCEL'):
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    if path == "/":
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; "
            "img-src 'self' data:; "
            "base-uri 'none'; object-src 'none'; "
            "form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests"
        )
    return response


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(_ROOT / "static" / "index.html", media_type="text/html")


@app.get("/spreadsheet.js", include_in_schema=False)
def spreadsheet_script():
    return FileResponse(
        _ROOT / "static" / "spreadsheet.js", media_type="application/javascript"
    )


@app.get("/workspace.js", include_in_schema=False)
def workspace_script():
    return FileResponse(_ROOT / "static" / "workspace.js", media_type="application/javascript")


@app.get("/app.js", include_in_schema=False)
def app_script():
    return FileResponse(_ROOT / "static" / "app.js", media_type="application/javascript")


@app.get("/preferences.js", include_in_schema=False)
def preferences_script():
    return FileResponse(_ROOT / "static" / "preferences.js", media_type="application/javascript")


@app.get("/privacy", include_in_schema=False)
@app.get("/cookies", include_in_schema=False)
@app.get("/terms", include_in_schema=False)
def privacy_information():
    return FileResponse(_ROOT / "static" / "privacy.html", media_type="text/html")


@app.post("/api/workspace")
async def workspace(file: UploadFile = File(...), sheet: str = Form(""), template: str = Form(""), mapping: str = Form("{}")):
    filename, data = await _get_upload(file)
    frames, _ = parse_sheets(filename, data)
    selected, frame = select_sheet(frames, sheet)
    profile = profile_dataframe(frame, source_name=filename)
    health = workbook_health(filename, data)
    # IDs such as 001 and literal NA must keep their source meaning in templates.
    if template:
        literal_frames, _ = clean_frames(filename, data, clean_options("{}"))
        _, literal_frame = select_sheet(literal_frames, sheet)
        checks = template_audit(literal_frame, template, parse_audit_mapping(mapping))
    else:
        checks = []
    return {"selected_sheet": selected, "charts": explore(frame), "health": health,
            "templates": template_definitions(),
            "template_checks": checks, "narrative": narrative(profile, health, template, checks)}


@app.post("/api/clean/preview")
async def clean_preview(file: UploadFile = File(...), options: str = Form("{}")):
    filename, data = await _get_upload(file)
    parsed = clean_options(options)
    if filename.lower().endswith((".xlsx", ".xlsm")):
        output, preview = preserve_workbook(filename, data, parsed)
        output.close()
        preview["notice"] = "Only selected literal cells change in a separate workbook copy. Formulas and all other workbook package parts, including VBA, are preserved. Row removal and edits to formula cells are blocked. Changed inputs can still change calculated results or macro behavior: review in Excel before relying on this copy. Original file remains unchanged."
    else:
        _, preview = clean_frames(filename, data, parsed)
    return preview


@app.post("/api/clean/export")
async def clean_export(file: UploadFile = File(...), options: str = Form("{}"),
                       fingerprint: str = Form(...), confirmed: bool = Form(False)):
    filename, data = await _get_upload(file)
    excel = filename.lower().endswith((".xlsx", ".xlsm"))
    if excel:
        output, preview = preserve_workbook(filename, data, clean_options(options))
    else:
        frames, preview = clean_frames(filename, data, clean_options(options))
    if not confirmed or fingerprint != preview["fingerprint"]:
        if excel:
            output.close()
        raise HTTPException(409, "Review a fresh preview and confirm it before downloading.")
    if not excel:
        output = cleaned_workbook(frames)
    extension = ".xlsm" if filename.lower().endswith(".xlsm") else ".xlsx"
    return StreamingResponse(stream_file_chunks(output),
        media_type=("application/vnd.ms-excel.sheet.macroEnabled.12" if extension == ".xlsm" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        headers={"Content-Disposition": f'attachment; filename="cleaned_review_copy{extension}"'})


@app.get("/health")
def health():
    return {"status": "ok", "product": "Data Quality Detective", "stage": "free"}


@app.get("/api/config")
def config():
    public = _public_demo_only()
    return {
        "mode": "public_demo" if public else ("free_web" if os.getenv("VERCEL") else "local"),
        "upload_allowed": not public,
        "max_upload_bytes": HOSTED_MAX_FILE_BYTES if os.getenv("VERCEL") else MAX_FILE_BYTES,
        "macro_execution_via_web": False,
        "large_upload_bytes": 0 if os.getenv('VERCEL') or public else 1024 ** 3,
        "public_demo": public,
        "release_sha": os.getenv("VERCEL_GIT_COMMIT_SHA", ""),
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
    if os.getenv("VERCEL") and len(data) > HOSTED_MAX_FILE_BYTES:
        raise HTTPException(413, "Public web uploads are limited to 4 MB.")
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


