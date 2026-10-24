"""Local chunked uploads and streaming read-only CSV/Excel inspection.

Never mounted on Vercel. Public storage, worker isolation and access control must
be provisioned before exposing this adapter outside localhost.
"""
import csv
import hashlib
import os
import secrets
import shutil
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from webapp.largeworkbook import stream_workbook

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, Form, Query
from fastapi.responses import StreamingResponse
import anyio
from pydantic import BaseModel, ConfigDict, Field
from webapp.workspace import CleanOptions
from webapp.largeclean import clean_csv, clean_excel
from webapp.largegrid import GridIndex, read_rows

router = APIRouter(prefix="/api/large")
MAX_BYTES = 1024 ** 3
CHUNK_BYTES = 4 * 1024 ** 2
TTL_SECONDS = 3600
_temporary = tempfile.TemporaryDirectory(prefix="dqd-large-test-")
_root = Path(_temporary.name)
_lock = threading.Lock()
_jobs = {}
MAX_RECORD_BYTES = 1024 * 1024


@asynccontextmanager
async def lifespan(app):
    stop = threading.Event()
    def sweep():
        while not stop.wait(30):
            with _lock:
                cleanup()
    worker = threading.Thread(target=sweep, daemon=True)
    worker.start()
    try:
        yield
    finally:
        stop.set()
        worker.join(timeout=2)
        with _lock:
            for job in _jobs.values():
                job['cancel'].set()
                if job['status'] not in {'processing', 'queued'}:
                    remove_files(job)


class UploadSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(min_length=1, max_length=200)
    size: int = Field(gt=0, le=MAX_BYTES)
    clean: CleanOptions | None = None


def remove_files(job):
    job['path'].unlink(missing_ok=True)
    if job.get('output'):
        job['output'].unlink(missing_ok=True)
    for key in ('grid', 'clean_grid'):
        if job.get(key):
            job[key].unlink(missing_ok=True)
            job[key].with_name(job[key].name+'-journal').unlink(missing_ok=True)


def local_only(request):
    if (os.getenv("VERCEL") or not request.client or
            request.client.host not in {"127.0.0.1", "::1", "testclient"} or
            request.url.hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}):
        raise HTTPException(404, "Large-file test adapter is local-only.")
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-origin requests are not allowed.")


def job_for(identifier, token):
    job = _jobs.get(identifier)
    if not job or not token or not token.isascii() or not secrets.compare_digest(job["token"], token):
        raise HTTPException(404, "Upload not found.")
    return job


def cleanup():
    for identifier, job in list(_jobs.items()):
        expired_download = (job['status'] == 'downloading' and not job.get('download_active') and
                            time.time()-job.get('download_requested', time.time()) > 60)
        if expired_download or (time.time() - job["created"] > TTL_SECONDS and job["status"] not in {'processing', 'queued', 'downloading'}):
            remove_files(job)
            del _jobs[identifier]


@router.post("/uploads")
def create_upload(spec: UploadSpec, request: Request):
    local_only(request)
    suffix = Path(spec.name).suffix.lower()
    if suffix not in {'.csv', '.xlsx', '.xlsm'}:
        raise HTTPException(422, "Choose a CSV, XLSX or XLSM file.")
    with _lock:
        cleanup()
        if any(j["status"] in {"uploading", "queued", "processing", 'review', 'downloading'} for j in _jobs.values()):
            raise HTTPException(429, "One large-file job may run at a time in this test adapter.")
        if shutil.disk_usage(_root).free < spec.size * (4 if spec.clean else 1) + 256 * 1024 ** 2:
            raise HTTPException(507, "Not enough temporary disk space.")
        identifier, token = secrets.token_urlsafe(24), secrets.token_urlsafe(32)
        path = _root / identifier
        path.touch(mode=0o600)
        _jobs[identifier] = {"token": token, "path": path, "size": spec.size, "received": 0,
                             "created": time.time(), "status": "uploading", "result": None,
                             "suffix": suffix, "cancel": threading.Event(), 'clean': spec.clean,
                             'output': _root / (identifier+'.cleaned'+suffix) if spec.clean else None,
                             'grid': _root / (identifier+'.grid.sqlite'),
                             'clean_grid': _root / (identifier+'.clean-grid.sqlite') if spec.clean else None}
        # Bound retained report metadata even if many small jobs finish in an hour.
        finished = [key for key, value in _jobs.items() if value['status'] in {'complete', 'failed', 'cancelled'}]
        for key in finished[:-20]:
            remove_files(_jobs[key])
            del _jobs[key]
    return {"id": identifier, "token": token, "chunk_bytes": CHUNK_BYTES, "max_bytes": MAX_BYTES}


@router.put("/uploads/{identifier}")
async def upload_chunk(identifier: str, request: Request, x_upload_token: str = Header(""), x_upload_offset: int = Header(...)):
    local_only(request)
    with _lock:
        job = job_for(identifier, x_upload_token)
        if job['status'] != 'uploading' or x_upload_offset != job['received']:
            raise HTTPException(409, "Upload offset or state mismatch.")
    # One request buffers at most one bounded chunk; the full file stays on disk.
    content = bytearray()
    async for part in request.stream():
        if len(content) + len(part) > CHUNK_BYTES:
            raise HTTPException(413, "Upload chunk exceeds 4 MiB.")
        content.extend(part)
    with _lock:
        job = job_for(identifier, x_upload_token)
        if job["status"] != "uploading" or x_upload_offset != job["received"]:
            raise HTTPException(409, "Upload offset or state mismatch; retry from the reported offset.")
        if not content or job["received"] + len(content) > job["size"]:
            raise HTTPException(413, "Chunk exceeds declared file size or is empty.")
        with job["path"].open("ab") as target:
            target.write(content)
        job["received"] += len(content)
        job['created'] = time.time()
        return {"received": job["received"]}


def csv_rows(path, check=lambda: None, summary=None, row_sink=None):
    csv.field_size_limit(1024 * 1024)
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        record_size = 0
        def bounded_lines():
            nonlocal record_size
            while True:
                check()
                line = source.readline(MAX_RECORD_BYTES + 1)
                if not line:
                    return
                record_size += len(line.encode('utf-8'))
                if record_size > MAX_RECORD_BYTES:
                    raise ValueError('CSV record exceeds 1 MiB.')
                yield line
        rows = csv.reader(bounded_lines(), strict=True)
        columns = next(rows, [])
        record_size = 0
        if not columns or len(columns) > 200 or len(set(columns)) != len(columns) or any(not c.strip() or len(c) > 200 for c in columns):
            raise ValueError("CSV needs a nonempty header with unique names and at most 200 columns.")
        if summary is not None:
            summary.update(columns=len(columns), missing=dict.fromkeys(columns, 0), rows=0,
                           preview={'columns': columns[:20], 'rows': []})
        yield columns
        count = 0
        for row in rows:
            record_size = 0
            if not row:
                continue
            if len(row) != len(columns):
                raise ValueError(f"Row {count + 2} has a different number of columns.")
            count += 1
            if summary is not None:
                summary['rows'] += 1
                if len(summary['preview']['rows']) < 20:
                    summary['preview']['rows'].append({'row_number': count+1, 'values': [v[:500] for v in row[:20]]})
                for column, value in zip(columns, row):
                    summary['missing'][column] += not value.strip()
            if row_sink:
                row_sink('', count+1, {i: value[:500] for i, value in enumerate(row)})
            yield row


def file_hash(path, check):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(CHUNK_BYTES), b''):
            check()
            digest.update(chunk)
    return digest.hexdigest()


def stream_csv(path, check=lambda: None, row_sink=None):
    summary = {}
    for _ in csv_rows(path, check, summary, row_sink):
        pass
    return {**summary,
                "sha256": file_hash(path, check), "bytes": path.stat().st_size,
                "kind": "CSV", "notice": "Complete-file row and missing-value overview. Preview full-file cleaning to prepare a separate CSV copy. Browse the spreadsheet in blocks of rows; charts and audit templates use the smaller-file workspace. Original file was not modified."}


def process(identifier):
    with _lock:
        job = _jobs[identifier]
        job["status"] = "processing"
    grid = cleaned_grid = None
    try:
        if job['cancel'].is_set():
            raise InterruptedError('Cancelled')
        grid = GridIndex(job['grid'])
        if job.get('clean'):
            cleaned_grid = GridIndex(job['clean_grid'])
        deadline = time.monotonic() + 900
        disk_check = time.monotonic()
        def check():
            nonlocal disk_check
            if job['cancel'].is_set():
                raise InterruptedError('Cancelled')
            if time.monotonic() > deadline:
                raise TimeoutError('Processing time limit reached')
            if time.monotonic()-disk_check > 1:
                disk_check = time.monotonic()
                if shutil.disk_usage(_root).free < 256*1024**2:
                    raise ValueError('Insufficient temporary disk space')
        if job['suffix'] == '.csv' and job.get('clean'):
            result = {'kind': 'CSV', 'bytes': job['path'].stat().st_size,
                      'notice': 'Complete-file CSV cleaning with original row and missing-value counts. Original unchanged.'}
        else:
            result = stream_csv(job['path'], check, grid.row) if job['suffix'] == '.csv' else stream_workbook(job['path'], check, grid.row, grid.string)
        if job.get('clean'):
            options = job['clean']
            preview = (clean_csv(job['path'], job['output'], options, csv_rows(job['path'], check, result, grid.row), check, cleaned_grid.row)
                       if job['suffix'] == '.csv' else clean_excel(job['path'], job['output'], options, check, cleaned_grid.row))
            if job['suffix'] == '.csv':
                result['sha256'] = file_hash(job['path'], check)
            preview['output_bytes'] = job['output'].stat().st_size
            preview['output_sha256'] = file_hash(job['output'], check)
            preview['fingerprint'] = hashlib.sha256((result['sha256']+options.model_dump_json()+preview['output_sha256']).encode()).hexdigest()
            result['cleaning'] = preview
        grid.close()
        grid = None
        if cleaned_grid:
            cleaned_grid.close()
            cleaned_grid = None
        with _lock:
            job["result"], job["status"] = result, 'review' if job.get('clean') else "complete"
    except InterruptedError:
        with _lock:
            job['result'], job['status'] = None, 'cancelled'
    except Exception as exc:
        with _lock:
            message = str(exc)[:300] if isinstance(exc, ValueError) else exc.detail if isinstance(exc, HTTPException) else 'Unable to process file within safety limits. Check format, encoding, record size or workbook expansion. Processing is limited to 15 minutes.'
            job["result"], job["status"] = {"error": message}, "failed"
    finally:
        if grid:
            grid.close(commit=False)
        if cleaned_grid:
            cleaned_grid.close(commit=False)
        job["path"].unlink(missing_ok=True)
        if job['status'] in {'failed', 'cancelled'}:
            remove_files(job)
        if job['status'] in {'failed', 'cancelled'} and job.get('output'):
            job['output'].unlink(missing_ok=True)


@router.post("/uploads/{identifier}/complete")
def complete_upload(identifier: str, request: Request, background_tasks: BackgroundTasks, x_upload_token: str = Header("")):
    local_only(request)
    with _lock:
        job = job_for(identifier, x_upload_token)
        if job["status"] != "uploading" or job["received"] != job["size"]:
            raise HTTPException(409, "Upload is incomplete or already submitted.")
        job["status"] = "queued"
    background_tasks.add_task(process, identifier)
    return {"status": "queued"}


@router.get("/uploads/{identifier}")
def upload_status(identifier: str, request: Request, x_upload_token: str = Header("")):
    local_only(request)
    with _lock:
        cleanup()
        job = job_for(identifier, x_upload_token)
        return {key: job[key] for key in ("status", "received", "size", "result")}


@router.get('/uploads/{identifier}/rows')
def grid_rows(identifier: str, request: Request, x_upload_token: str = Header(''),
              sheet: str = Query('', max_length=200), offset: int = Query(0, ge=0),
              column: int = Query(0, ge=0, le=16383), cleaned: bool = False):
    local_only(request)
    with _lock:
        cleanup()
        job = job_for(identifier, x_upload_token)
        if job['status'] not in {'complete', 'review'} or not job['grid'].exists():
            raise HTTPException(409, 'The spreadsheet is not ready to browse.')
        result = job['result']
        if result['kind'] == 'CSV':
            names = list(result['missing'])
            total, columns = result['rows']+1, len(names)
            if cleaned and result.get('cleaning'):
                total = result['cleaning']['rows_after']+1
            sheet = ''
        else:
            selected = next((item for item in result['sheets'] if item['name'] == sheet), None)
            if selected is None:
                raise HTTPException(422, 'Choose an existing worksheet.')
            total, columns, names = selected['max_row'], selected['columns'], None
        index = job['grid']
        if cleaned:
            if not result.get('cleaning'):
                raise HTTPException(409, 'Prepare a cleaned preview first.')
            if result['kind'] == 'CSV' or sheet == result['cleaning'].get('sheet'):
                index = job['clean_grid']
        # CSV headings are stored in metadata rather than duplicated in the index.
        csv_header = names is not None and offset == 0
        rows = read_rows(index, job['grid'], sheet, max(0, offset-(names is not None)), 49 if csv_header else 50, column, columns, total if names is None else None)
        if csv_header:
            rows.insert(0, {'row_number': 1, 'values': names[column:column+20]})
        job['created'] = time.time()
        return {'rows': rows, 'total': total, 'columns_total': columns, 'offset': offset, 'column': column}


@router.delete("/uploads/{identifier}")
def delete_upload(identifier: str, request: Request, x_upload_token: str = Header("")):
    local_only(request)
    with _lock:
        job = job_for(identifier, x_upload_token)
        if job["status"] in {"processing", "queued"}:
            job['cancel'].set()
            return {"cancelling": True}
        if job['status'] == 'downloading':
            raise HTTPException(409, 'Wait for the download to finish.')
        remove_files(job)
        del _jobs[identifier]
    return {"deleted": True}


@router.post('/uploads/{identifier}/download')
def download_cleaned(identifier: str, request: Request, token: str = Form(...), fingerprint: str = Form(...), confirmed: bool = Form(False)):
    local_only(request)
    with _lock:
        job = job_for(identifier, token)
        if (job['status'] != 'review' or not confirmed or not fingerprint.isascii() or
                not secrets.compare_digest(job['result']['cleaning']['fingerprint'], fingerprint)):
            raise HTTPException(409, 'Review and confirm this exact preview before downloading.')
        job['status'] = 'downloading'
        job['download_requested'], job['download_active'] = time.time(), False
    async def chunks():
        with job['output'].open('rb') as source:
            while block := await anyio.to_thread.run_sync(source.read, CHUNK_BYTES):
                yield block
    class CleanedDownload(StreamingResponse):
        async def __call__(self, scope, receive, send):
            job['download_active'] = True
            try:
                with anyio.fail_after(900):
                    await super().__call__(scope, receive, send)
            finally:
                with anyio.CancelScope(shield=True):
                    await self.body_iterator.aclose()
                with _lock:
                    job['output'].unlink(missing_ok=True)
                    job['status'], job['download_active'] = 'complete', False
    return CleanedDownload(chunks(), media_type='application/octet-stream', headers={
        'Content-Disposition': 'attachment; filename="cleaned_review_copy'+job['suffix']+'"',
        'Content-Length': str(job['result']['cleaning']['output_bytes'])})
