import io
import json
import re
from zipfile import ZipFile

import pytest
from defusedxml import ElementTree as ET
from openpyxl import Workbook, load_workbook
from fastapi import HTTPException
from fastapi.testclient import TestClient

from webapp.largeclean import clean_excel
from webapp.preserve import preserve_workbook
from webapp.workspace import CleanOptions
from webapp.richtext import MAIN, NS
from webapp.richtext import preserve_runs
from webapp.app import app


def rich_workbook(storage, text=None):
    book = Workbook()
    book.active.title = 'Orders'
    book.active.append(['name', 'unchanged'])
    book.active.append([' placeholder ', ' placeholder '])
    book.active.append(['001', '=A2'])
    book.active['A2'].number_format = '@'
    book.create_sheet('Hidden').sheet_state = 'hidden'
    raw = io.BytesIO()
    book.save(raw)
    book.close()
    runs = text or '<r><rPr><b/><color rgb="FFFF0000"/><rFont val="Arial"/><sz val="14"/></rPr><t xml:space="preserve">  Mi</t></r><r><rPr><i/><u val="single"/><strike/></rPr><t xml:space="preserve">XeD ß &amp; &lt; </t></r><r><rPr><vertAlign val="superscript"/></rPr><t xml:space="preserve">TeSt  </t></r>'
    output = io.BytesIO()
    with ZipFile(raw) as source, ZipFile(output, 'w') as dest:
        for part in source.infolist():
            data = source.read(part.filename)
            if storage == 'shared' and part.filename == '[Content_Types].xml':
                data = data.replace(b'</Types>', b'<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>')
            if storage == 'shared' and part.filename == 'xl/_rels/workbook.xml.rels':
                data = data.replace(b'</Relationships>', b'<Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml" Id="richStrings"/></Relationships>')
            if part.filename == 'xl/worksheets/sheet1.xml':
                for coordinate in ['A2', 'B2']:
                    replacement = f'<c r="{coordinate}"'+(' s="1"' if coordinate == 'A2' else '')
                    replacement += ' t="s"><v>0</v></c>' if storage == 'shared' else ' t="inlineStr"><is>'+runs+'</is></c>'
                    data = re.sub(rb'<c r="'+coordinate.encode()+rb'".*?</c>', lambda _: replacement.encode(), data)
            dest.writestr(part, data)
        if storage == 'shared':
            dest.writestr('xl/sharedStrings.xml', f'<sst xmlns="{MAIN}"><si>{runs}</si></sst>')
        dest.writestr('xl/vbaProject.bin', b'test macro bytes - never executed')
        dest.writestr('customXml/item1.xml', b'<keep>untouched</keep>')
    return output.getvalue(), runs


def clean(backend, data, options, tmp_path):
    if backend == 'website':
        options.columns = ['name']
        return preserve_workbook('book.xlsm', data, options)[0].getvalue()
    source, target = tmp_path/'source.xlsm', tmp_path/'cleaned.xlsm'
    source.write_bytes(data)
    options.columns = ['A']
    stats = clean_excel(source, target, options, lambda: None)
    assert stats['cells_changed'] == 1
    assert source.read_bytes() == data
    assert not target.with_suffix('.sqlite').exists()
    return target.read_bytes()


@pytest.mark.parametrize('backend', ['website', 'local'])
@pytest.mark.parametrize('storage', ['inline', 'shared'])
@pytest.mark.parametrize('case, expected', [('keep', 'MiXeD ß & < TeSt'), ('upper', 'MIXED SS & < TEST'), ('lower', 'mixed ß & < test')])
def test_clean_copy_retains_rich_runs_and_all_untouched_parts(backend, storage, case, expected, tmp_path):
    original, runs = rich_workbook(storage)
    result = clean(backend, original, CleanOptions(sheet='Orders', trim=True, case=case), tmp_path)
    with ZipFile(io.BytesIO(original)) as source, ZipFile(io.BytesIO(result)) as target:
        assert source.namelist() == target.namelist()
        for name in source.namelist():
            if name != 'xl/worksheets/sheet1.xml':
                assert source.read(name) == target.read(name), name
        before, after = source.read('xl/worksheets/sheet1.xml'), target.read('xl/worksheets/sheet1.xml')
        # The same shared string is also referenced by B2, which must not change.
        assert re.search(rb'<c r="B2".*?</c>', before)[0] == re.search(rb'<c r="B2".*?</c>', after)[0]
        cell = ET.fromstring(after).find('.//m:c[@r="A2"]', NS)
        assert cell.attrib['s'] == '1'
        actual = cell.find('m:is', NS).findall('m:r', NS)
        old = ET.fromstring(f'<is xmlns="{MAIN}">{runs}</is>').findall('m:r', NS)
        assert len(actual) == len(old)
        for a, b in zip(actual, old):
            assert ET.tostring(a.find('m:rPr', NS)) == ET.tostring(b.find('m:rPr', NS))
        assert ''.join(r.find('m:t', NS).text or '' for r in actual) == expected
        assert actual[0].find('m:t', NS).text == expected[:2]
        assert actual[-1].find('m:t', NS).text == expected[-4:]
    book = load_workbook(io.BytesIO(result), rich_text=True)
    assert str(book['Orders']['A2'].value) == expected
    assert str(book['Orders']['B2'].value) == '  MiXeD ß & < TeSt  '
    assert book['Orders']['B3'].value == '=A2'
    assert book['Hidden'].sheet_state == 'hidden'
    book.close()


@pytest.mark.parametrize('backend', ['website', 'local'])
@pytest.mark.parametrize('storage', ['inline', 'shared'])
def test_rich_date_rewrite_is_rejected_instead_of_losing_formatting(backend, storage, tmp_path):
    original, _ = rich_workbook(storage, '<r><rPr><b/></rPr><t>31/12/</t></r><r><rPr><i/></rPr><t>2025</t></r>')
    with pytest.raises((ValueError, HTTPException)) as exc:
        clean(backend, original, CleanOptions(sheet='Orders', date_format='%d/%m/%Y'), tmp_path)
    assert 'formatting' in str(exc.value)


@pytest.mark.parametrize('text,new,case', [(' ΟΣ ', 'ος', 'lower'), (' İß ', 'i̇ß', 'lower'), (' ß ', 'SS', 'upper'), ('   ', '', 'keep')])
def test_unicode_and_whitespace_keep_character_run_boundaries(text, new, case):
    root = ET.fromstring(f'<is xmlns="{MAIN}"><r><rPr><b/></rPr><t>{text[:2]}</t></r><r><rPr><i/></rPr><t>{text[2:]}</t></r></is>')
    output = ET.fromstring(preserve_runs(root, new, CleanOptions(trim=True, case=case)))
    assert ''.join(n.text or '' for n in output.findall('m:r/m:t', NS)) == new
    assert output.find('m:r/m:rPr/m:b', NS) is not None
    assert output.findall('m:r', NS)[1].find('m:rPr/m:i', NS) is not None


def test_website_preview_and_approved_download_preserve_rich_text():
    data, _ = rich_workbook('shared')
    client = TestClient(app)
    options = json.dumps({'sheet': 'Orders', 'columns': ['name'], 'trim': True})
    preview = client.post('/api/clean/preview', files={'file': ('rich.xlsm', data)}, data={'options': options})
    assert preview.status_code == 200, preview.text
    assert preview.json()['copy_preview']['rows'][0][0] == 'MiXeD ß & < TeSt'
    download = client.post('/api/clean/export', files={'file': ('rich.xlsm', data)},
                           data={'options': options, 'confirmed': 'true', 'fingerprint': preview.json()['fingerprint']})
    assert download.status_code == 200, download.text
    book = load_workbook(io.BytesIO(download.content), rich_text=True)
    assert book['Orders']['A2'].value[0].font.b is True
    assert str(book['Orders']['A2'].value) == 'MiXeD ß & < TeSt'
    book.close()
