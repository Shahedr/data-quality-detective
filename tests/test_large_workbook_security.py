import threading
import time
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from webapp.app import app
from webapp import largefiles
from webapp.largeworkbook import stream_workbook


def make_book(tmp_path):
    path = tmp_path / 'source.xlsx'
    book = Workbook()
    book.active.append(['name', 'total'])
    book.active.append([' Alice ', '=1+2'])
    book.create_sheet('Hidden').sheet_state = 'hidden'
    book.save(path)
    book.close()
    return path


def test_stream_excel_formula_hidden_and_unchanged(tmp_path):
    path = make_book(tmp_path)
    before = path.read_bytes()
    result = stream_workbook(path)
    assert result['kind'] == 'Excel'
    assert result['sheets'][0] == {'name': 'Sheet', 'state': 'visible', 'stored_rows': 2,
                                  'columns': 2, 'stored_cells': 4, 'formulas': 1, 'cached_errors': 0,
                                  'preview': {'columns': ['A', 'B'], 'rows': [{'row_number': 1, 'values': ['name', 'total']}, {'row_number': 2, 'values': [' Alice ', '=1+2']}]}}
    assert result['sheets'][1]['state'] == 'hidden'
    assert not result['vba_present']
    assert path.read_bytes() == before


@pytest.mark.parametrize('payload', [
    b'<!DOCTYPE x [<!ENTITY x "unsafe">]><worksheet>&x;</worksheet>',
    b'<worksheet>' + b'<x>'*65 + b'</x>'*65 + b'</worksheet>',
    b'<worksheet><row><c r="XFE1"/></row></worksheet>',
    b'<worksheet><row><c r="A1"><v>' + b'x'*(1024**2+1) + b'</v></c></row></worksheet>',
    b'<worksheet attribute="' + b'>'*(1024**2+1) + b'"/>',
], ids=['entity', 'depth', 'column', 'cell-text', 'huge-attribute'])
def test_hostile_worksheet_xml_is_rejected(tmp_path, payload):
    path = make_book(tmp_path)
    replacement = tmp_path / 'hostile.xlsx'
    with ZipFile(path) as src, ZipFile(replacement, 'w') as dst:
        for item in src.infolist():
            dst.writestr(item, payload if item.filename == 'xl/worksheets/sheet1.xml' else src.read(item.filename))
    with pytest.raises(Exception):
        stream_workbook(replacement)


def test_stream_cancel_and_oversized_quoted_csv_record(tmp_path):
    path = tmp_path / 'bad.csv'
    path.write_text('one\n"' + ('x'*600000 + '\n')*2 + '"\n')
    with pytest.raises(ValueError, match='record exceeds'):
        largefiles.stream_csv(path)
    def cancelled():
        raise InterruptedError('cancelled')
    with pytest.raises(InterruptedError):
        largefiles.stream_csv(path, cancelled)


def test_local_request_boundaries_and_actual_body_limit(monkeypatch):
    monkeypatch.delenv('VERCEL', raising=False)
    client = TestClient(app)
    assert client.post('/api/analyze', content=b'x', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.get('/api/config', headers={'Host': 'evil.example'}).status_code == 403
    assert client.post('/api/analyze', content=b'x'*(11*1024**2), headers={'Content-Length': '1'}).status_code == 413
    assert client.post('/api/analyze', content=iter([b'a'])).status_code == 411
    assert client.post('/api/large/uploads', content=b'x'*9000, headers={'Content-Length': '1'}).status_code == 413


def test_excel_upload_and_processing_cancel(tmp_path, monkeypatch):
    monkeypatch.delenv('VERCEL', raising=False)
    client = TestClient(app)
    data = make_book(tmp_path).read_bytes()
    job = client.post('/api/large/uploads', json={'name': 'source.xlsm', 'size': len(data)}).json()
    endpoint = '/api/large/uploads/' + job['id']
    token = {'X-Upload-Token': job['token']}
    assert client.put(endpoint, content=data, headers={**token, 'X-Upload-Offset': '0'}).status_code == 200
    assert client.post(endpoint+'/complete', headers=token).status_code == 200
    assert client.get(endpoint, headers=token).json()['result']['kind'] == 'Excel'
    assert client.delete(endpoint, headers=token).status_code == 200
    job = client.post('/api/large/uploads', json={'name': 'source.csv', 'size': 5}).json()
    current = largefiles._jobs[job['id']]
    current['status'] = 'processing'
    endpoint = '/api/large/uploads/' + job['id']
    token = {'X-Upload-Token': job['token']}
    assert client.delete(endpoint, headers=token).json() == {'cancelling': True}
    assert current['cancel'].is_set()
    current['status'] = 'uploading'
    assert client.delete(endpoint, headers=token).status_code == 200


def test_scheduled_expiry_removes_abandoned_upload(tmp_path, monkeypatch):
    path = tmp_path / 'stale'
    path.write_bytes(b'sensitive')
    monkeypatch.setattr(largefiles, '_jobs', {'old': {'created': time.time()-4000,
                        'status': 'uploading', 'path': path, 'cancel': threading.Event()}})
    largefiles.cleanup()
    assert not path.exists() and not largefiles._jobs


def test_cancelled_worker_really_deletes_source(tmp_path, monkeypatch):
    path = tmp_path / 'cancelled.csv'
    path.write_bytes(b'id\n1\n')
    cancelled = threading.Event()
    cancelled.set()
    job = {'path': path, 'status': 'queued', 'suffix': '.csv', 'cancel': cancelled}
    monkeypatch.setattr(largefiles, '_jobs', {'cancelled': job})
    largefiles.process('cancelled')
    assert job['status'] == 'cancelled'
    assert not path.exists()
