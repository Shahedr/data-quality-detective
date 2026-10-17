"""Browser MVP built on the same profiling engine as the dqdetect CLI.

Prototype only. Before exposing to untrusted internet traffic, add authentication,
rate limiting, deployment-level resource limits, and an abuse/privacy review.
"""

import io
import json
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from dqdetect.profiler import profile_dataframe
from dqdetect.report import render_html, render_json
from webapp.inspect import append_annotated_excerpt, inspect_dataframe, ISSUE_FILTERS

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 200

app = FastAPI(
    title="Data Quality Detective",
    description="Local browser preview for CSV/Excel data profiling.",
    version="0.1.0-preview",
    docs_url=None,
    redoc_url=None,
)

_ROOT = Path(__file__).resolve().parent


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(_ROOT / "static" / "index.html", media_type="text/html")


@app.get("/spreadsheet.js", include_in_schema=False)
def spreadsheet_script():
    return FileResponse(
        _ROOT / "static" / "spreadsheet.js",
        media_type="application/javascript",
    )


@app.get("/health")
def health():
    return {"status": "ok", "product": "Data Quality Detective", "stage": "preview"}


def _read_dataset(name: str, data: bytes):
    """Parse and enforce the local preview limits without saving user datasets."""
    suffix = Path(name).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise HTTPException(
            status_code=415, detail="Supported upload formats: .csv and .xlsx."
        )
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413, detail="File exceeds the 10 MB prototype upload limit."
        )
    if suffix == ".xlsx" and not data.startswith(b"PK"):
        raise HTTPException(status_code=422, detail="The Excel workbook is invalid.")

    try:
        buffer = io.BytesIO(data)
        if suffix == ".csv":
            df = pd.read_csv(buffer)
        else:
            df = pd.read_excel(buffer, engine="openpyxl")
    except (ValueError, UnicodeError, OSError, EOFError, ImportError, KeyError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Could not read this dataset. Check its format and encoding.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail="Unable to parse the uploaded dataset."
        ) from exc

    if df.shape[0] > MAX_ROWS or df.shape[1] > MAX_COLUMNS:
        raise HTTPException(
            status_code=413,
            detail="Prototype limit: 100,000 rows and 200 columns. "
            "The standalone CLI has no fixed row-count limit.",
        )
    return df


def analyze_bytes(name: str, data: bytes) -> dict:
    """Generate dashboard, actual flagged rows, and downloadable annotated report."""
    df = _read_dataset(name, data)
    try:
        profile = profile_dataframe(df, source_name=Path(name).name)
        report_json = json.loads(render_json(profile))
        return {
            "summary": profile["summary"],
            "columns": profile["columns"],
            "recommendations": report_json["recommendations"],
            "report_json": report_json,
            "report_html": append_annotated_excerpt(render_html(profile), df),
            "spreadsheet": inspect_dataframe(df),
        }
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422, detail="Could not profile this dataset."
        ) from exc


def inspect_bytes(name: str, data: bytes, page=1, issue="all") -> dict:
    """Stateless paging: reloads the selected file each request, no server cache."""
    if issue not in ISSUE_FILTERS or page < 1:
        raise HTTPException(status_code=422, detail="Invalid page or issue filter.")
    df = _read_dataset(name, data)
    try:
        return inspect_dataframe(df, page=page, issue=issue)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status_code=400, detail="Choose a file to analyze.")
    try:
        data = await file.read(MAX_FILE_BYTES + 1)
    finally:
        await file.close()
    return JSONResponse(analyze_bytes(filename, data))


@app.post("/api/rows")
async def inspect_rows(
    file: UploadFile = File(...),
    page: int = Form(1),
    issue: str = Form("all"),
):
    """Returns one grid page; the browser re-sends its local file for each page."""
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status_code=400, detail="Choose a file to inspect.")
    try:
        data = await file.read(MAX_FILE_BYTES + 1)
    finally:
        await file.close()
    return JSONResponse(inspect_bytes(filename, data, page=page, issue=issue))
