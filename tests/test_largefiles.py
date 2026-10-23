import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.app import app
from webapp import largefiles

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_jobs(monkeypatch):
    monkeypatch.delenv('VERCEL', raising=False)
    for job in largefiles._jobs.values():
        job['path'].unlink(missing_ok=True)
    largefiles._jobs.clear()
    yield
    for job in largefiles._jobs.values():
        job['path'].unlink(missing_ok=True)
    largefiles._jobs.clear()


def test_chunk_upload_auth_offsets_processing_and_deletion():
    data = b'id,name\n1,A\n2,\n'
    job = client.post('/api/large/uploads',json={'name':'data.csv','size':len(data)}).json()
    path='/api/large/uploads/'+job['id']
    headers={'X-Upload-Token':job['token'],'X-Upload-Offset':'0'}
    assert client.put(path,content=data,headers={'X-Upload-Offset':'0'}).status_code==404
    assert client.put(path,content=data[:8],headers=headers).status_code==200
    assert client.put(path,content=data,headers=headers).status_code==409
    assert client.post(path+'/complete',headers=headers).status_code==409
    headers['X-Upload-Offset']='8'
    assert client.put(path,content=data[8:],headers=headers).status_code==200
    assert client.post(path+'/complete',headers=headers).status_code==200
    result=client.get(path,headers=headers).json()
    assert result['status']=='complete' and result['result']['rows']==2
    assert result['result']['missing']=={'id':0,'name':1}
    assert result['result']['sha256']==hashlib.sha256(data).hexdigest()
    assert not largefiles._jobs[job['id']]['path'].exists()
    assert client.delete(path,headers=headers).status_code==200


def test_limits_cross_origin_hosted_and_invalid_file(monkeypatch):
    assert client.post('/api/large/uploads',json={'name':'data.csv','size':largefiles.MAX_BYTES+1}).status_code==422
    assert client.post('/api/large/uploads',json={'name':'data.exe','size':100}).status_code==422
    assert client.post('/api/large/uploads',json={'name':'data.csv','size':100},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post('/api/large/uploads',json={'name':'data.csv','size':100},headers={'Host':'evil.example'}).status_code==403
    monkeypatch.setenv('VERCEL','1')
    assert client.post('/api/large/uploads',json={'name':'data.csv','size':100}).status_code==404


def test_full_one_gib_csv_streaming_without_loading_whole_file(tmp_path):
    # Real bytes on disk: not a sparse file or a forged Content-Length.
    size=1024**3
    path=tmp_path/'one-gib.csv'
    header=b'value\n'
    row=b'x'*1023+b'\n'
    expected_rows=(size-len(header))//len(row)
    tail=size-len(header)-expected_rows*len(row)
    with path.open('wb') as target:
        target.write(header)
        block=row*1024
        blocks,remaining=divmod(expected_rows,1024)
        for _ in range(blocks):
            target.write(block)
        target.write(row*remaining)
        if tail:
            target.write(b'x'*(tail-1)+b'\n')
    assert path.stat().st_size==size
    result=largefiles.stream_csv(path)
    assert result['bytes']==size and result['rows']==expected_rows+bool(tail)
    assert result['missing']=={'value':0}
    job=client.post('/api/large/uploads',json={'name':'one-gib.csv','size':size}).json()
    endpoint='/api/large/uploads/'+job['id']
    with path.open('rb') as source:
        offset=0
        for chunk in iter(lambda:source.read(largefiles.CHUNK_BYTES),b''):
            response=client.put(endpoint,content=chunk,headers={'X-Upload-Token':job['token'],'X-Upload-Offset':str(offset)})
            assert response.status_code==200,response.text
            offset+=len(chunk)
    assert client.post(endpoint+'/complete',headers={'X-Upload-Token':job['token']}).status_code==200
    state=client.get(endpoint,headers={'X-Upload-Token':job['token']}).json()
    assert state['status']=='complete' and state['result']==result
    assert not largefiles._jobs[job['id']]['path'].exists()


def test_quota_chunk_size_and_failed_processing_delete_temporary_bytes():
    data=b'one,two\ninvalid-row\n'
    job=client.post('/api/large/uploads',json={'name':'bad.csv','size':len(data)}).json()
    endpoint='/api/large/uploads/'+job['id']
    token={'X-Upload-Token':job['token']}
    assert client.post('/api/large/uploads',json={'name':'another.csv','size':10}).status_code==429
    assert client.put(endpoint,content=b'x'*(largefiles.CHUNK_BYTES+1),headers={**token,'X-Upload-Offset':'0'}).status_code==413
    assert client.put(endpoint,content=data,headers={**token,'X-Upload-Offset':'0'}).status_code==200
    client.post(endpoint+'/complete',headers=token)
    assert client.get(endpoint,headers=token).json()['status']=='failed'
    assert not largefiles._jobs[job['id']]['path'].exists()
