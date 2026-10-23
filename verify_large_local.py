"""Real 1 GiB CSV and worksheet uploads over loopback HTTP, with memory evidence."""
import hashlib
import json
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED

import httpx
import psutil
from openpyxl import Workbook

SIZE = 1024 ** 3
ROOT = Path('reports').resolve()


def fixtures(folder):
    csv = folder / 'one-gib.csv'
    digest = hashlib.sha256()
    with csv.open('wb') as target:
        header = b'value\n'
        target.write(header)
        digest.update(header)
        remaining = SIZE-len(header)
        block = (b'x'*1023+b'\n')*1024
        while remaining:
            data = block[:min(remaining, len(block))]
            if remaining < len(block):
                data = data[:-1]+b'\n'
            target.write(data)
            digest.update(data)
            remaining -= len(data)
    yield csv, {'rows': (SIZE-6+1023)//1024, 'sha256': digest.hexdigest()}
    csv.unlink()
    small = folder / 'base.xlsx'
    book = Workbook()
    book.save(small)
    book.close()
    large = folder / 'one-gib.xlsx'
    with ZipFile(small) as source, ZipFile(large, 'w', compression=ZIP_STORED) as result:
        for entry in source.infolist():
            if entry.filename != 'xl/worksheets/sheet1.xml':
                result.writestr(entry.filename, source.read(entry.filename))
        with result.open('xl/worksheets/sheet1.xml', 'w', force_zip64=True) as worksheet:
            worksheet.write(b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>')
            for row in range(1, 100001):
                worksheet.write(f'<row r="{row}"><c r="A{row}" t="inlineStr"><is><t>'.encode()+b'x'*10000+b'</t></is></c></row>')
            worksheet.write(b'</sheetData></worksheet>')
        # Make the complete package exactly 1 GiB; most bytes are real worksheet cells.
        overhead = 30+len('customXml/padding.bin')+46+len('customXml/padding.bin')+22
        padding = SIZE-result.fp.tell()-sum(46+len(e.filename.encode()) for e in result.infolist())-overhead
        with result.open('customXml/padding.bin', 'w') as target:
            while padding:
                block = b'0'*min(padding, 1024**2)
                target.write(block)
                padding -= len(block)
    assert large.stat().st_size == SIZE, large.stat().st_size
    yield large, {'stored_rows': 100000, 'stored_cells': 100000}


def main():
    cleaning = '--clean' in sys.argv
    ROOT.mkdir(exist_ok=True)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    log = (ROOT/'large-http-server.log').open('w')
    server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'webapp.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-proxy-headers'], stdout=log, stderr=log)
    stop = threading.Event()
    peak = [0]
    def monitor():
        process = psutil.Process(server.pid)
        while not stop.wait(.05):
            try:
                processes = [process] + process.children(recursive=True)
                peak[0] = max(peak[0], sum(item.memory_info().rss for item in processes))
            except psutil.NoSuchProcess:
                return
    worker = threading.Thread(target=monitor, daemon=True)
    worker.start()
    evidence = []
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=120, trust_env=False) as client:
            for _ in range(100):
                try:
                    if client.get('/health').status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                time.sleep(.1)
            else:
                raise RuntimeError('Local test server failed to start')
            with tempfile.TemporaryDirectory(prefix='dqd-1gib-proof-') as folder:
                for path, expected in fixtures(Path(folder)):
                    started = time.monotonic()
                    options = {'columns': ['value'] if path.suffix == '.csv' else ['A'], 'sheet': '' if path.suffix == '.csv' else 'Sheet', 'case': 'upper'} if cleaning else None
                    response = client.post('/api/large/uploads', json={'name': path.name, 'size': path.stat().st_size, 'clean': options})
                    response.raise_for_status()
                    job = response.json()
                    endpoint = '/api/large/uploads/'+job['id']
                    token = {'X-Upload-Token': job['token']}
                    digest = hashlib.sha256()
                    with path.open('rb') as source:
                        offset = 0
                        for chunk in iter(lambda: source.read(job['chunk_bytes']), b''):
                            digest.update(chunk)
                            response = client.put(endpoint, content=chunk, headers={**token, 'X-Upload-Offset': str(offset)})
                            response.raise_for_status()
                            offset += len(chunk)
                    client.post(endpoint+'/complete', headers=token).raise_for_status()
                    while True:
                        state = client.get(endpoint, headers=token).json()
                        if state['status'] not in {'queued', 'processing'}:
                            break
                        time.sleep(.1)
                    assert state['status'] == ('review' if cleaning else 'complete'), state
                    result = state['result']
                    assert result['bytes'] == SIZE and result['sha256'] == digest.hexdigest()
                    if path.suffix == '.csv':
                        assert result['rows'] == expected['rows'] and result['sha256'] == expected['sha256']
                    else:
                        assert all(result['sheets'][0][k] == v for k,v in expected.items())
                    if cleaning:
                        preview = result['cleaning']
                        assert preview['cells_changed'] == (expected['rows'] if path.suffix == '.csv' else 99999)
                        output_hash, output_size = hashlib.sha256(), 0
                        with client.stream('POST', endpoint+'/download', data={'token': job['token'], 'fingerprint': preview['fingerprint'], 'confirmed': 'true'}) as download:
                            download.raise_for_status()
                            for block in download.iter_bytes(4*1024**2):
                                output_hash.update(block)
                                output_size += len(block)
                        assert output_hash.hexdigest() == preview['output_sha256'] and output_size == preview['output_bytes']
                    client.delete(endpoint, headers=token).raise_for_status()
                    assert client.get(endpoint, headers=token).status_code == 404
                    evidence.append({'format': path.suffix, 'bytes': SIZE, 'seconds': round(time.monotonic()-started, 2),
                                     'peak_server_rss_bytes': peak[0], 'result': result})
                    print(json.dumps({'format': path.suffix, 'bytes': SIZE, 'seconds': evidence[-1]['seconds'], 'peak_server_rss_bytes': peak[0], 'cells_changed': result.get('cleaning', {}).get('cells_changed')}), flush=True)
                    if '--csv-only' in sys.argv:
                        break
            assert peak[0] < 512*1024**2, 'Server exceeded 512 MiB memory budget'
    finally:
        stop.set()
        worker.join(timeout=2)
        for child in psutil.Process(server.pid).children(recursive=True):
            child.terminate()
        server.terminate()
        server.wait(timeout=15)
        log.close()
        filename = 'large-cleaning-csv-speed.json' if '--csv-only' in sys.argv else 'large-cleaning-verification.json' if cleaning else 'large-http-verification.json'
        (ROOT/filename).write_text(json.dumps(evidence, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
