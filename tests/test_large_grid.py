import io
from zipfile import ZipFile

from fastapi.testclient import TestClient
from openpyxl import Workbook

from test_large_cleaning import upload, jobs
from webapp.app import app
from webapp import largefiles


def test_csv_grid_pages_columns_cleaned_output_and_auth():
    client = TestClient(app)
    headers = ','.join('field'+str(i) for i in range(25))
    data = (headers+'\n'+''.join(','.join(['  value  ']+[str(i)]*24)+'\n' for i in range(125))).encode()
    job, endpoint, token, state = upload(client, 'grid.csv', data, {'columns': ['field0'], 'trim': True})
    assert state['status'] == 'review', state
    assert client.get(endpoint+'/rows').status_code == 404
    original = client.get(endpoint+'/rows', headers=token).json()
    assert original['total'] == 126 and len(original['rows']) == 50
    assert original['rows'][1]['values'][0] == '  value  '
    cleaned = client.get(endpoint+'/rows?cleaned=true', headers=token).json()
    assert cleaned['rows'][1]['values'][0] == 'value'
    later = client.get(endpoint+'/rows?offset=100&column=20', headers=token).json()
    assert later['rows'][0] == {'row_number': 101, 'values': ['99']*5}
    assert client.get(endpoint+'/rows?column=-1', headers=token).status_code == 422
    assert client.get(endpoint+'/rows', headers={**token, 'Origin': 'https://evil.example'}).status_code == 403
    index = largefiles._jobs[job['id']]['grid']
    assert index.exists()
    client.delete(endpoint, headers=token)
    assert not index.exists()
    assert client.get(endpoint+'/rows', headers=token).status_code == 404


def test_excel_grid_worksheets_formulas_shared_strings_and_cleaned_preview():
    book = Workbook()
    book.active.title = 'Orders'
    book.active.append(['name', 'formula'])
    for i in range(70):
        book.active.append([' Alice ', '=1+2'])
    book.create_sheet('Hidden').append(['<script>alert(1)</script>'])
    book['Hidden'].sheet_state = 'hidden'
    buffer = io.BytesIO()
    book.save(buffer)
    # Model the shared-string representation Excel commonly writes.
    shared = io.BytesIO()
    with ZipFile(io.BytesIO(buffer.getvalue())) as source, ZipFile(shared, 'w') as target:
        for entry in source.infolist():
            content = source.read(entry.filename)
            if entry.filename == 'xl/worksheets/sheet1.xml':
                content = content.replace(b'<c r="A2" t="inlineStr"><is><t xml:space="preserve"> Alice </t></is></c>', b'<c r="A2" t="s"><v>0</v></c>')
            target.writestr(entry, content)
        target.writestr('xl/sharedStrings.xml', '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t> Alice </t></si></sst>')
    client = TestClient(app)
    job, endpoint, token, state = upload(client, 'grid.xlsm', shared.getvalue(), {'sheet': 'Orders', 'columns': ['A'], 'trim': True})
    assert state['status'] == 'review', state
    page = client.get(endpoint+'/rows?sheet=Orders&offset=50', headers=token).json()
    assert page['rows'][0] == {'row_number': 51, 'values': [' Alice ', '=1+2']}
    original = client.get(endpoint+'/rows?sheet=Orders', headers=token).json()
    assert original['rows'][1]['values'][0] == ' Alice '
    cleaned = client.get(endpoint+'/rows?sheet=Orders&cleaned=true', headers=token).json()
    assert cleaned['rows'][1]['values'] == ['Alice', '=1+2']
    hidden = client.get(endpoint+'/rows?sheet=Hidden&cleaned=true', headers=token).json()
    assert hidden['rows'][0]['values'] == ['<script>alert(1)</script>']
    assert client.get(endpoint+'/rows?sheet=Unknown', headers=token).status_code == 422
    assert len(state['result']['sheets'][0]['preview']['rows']) == 20
