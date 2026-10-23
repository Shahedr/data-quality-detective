"""Run a reviewed official greeting macro after both preservation export paths.

Interactive Excel check: the operator must dismiss the greeting. Existing
Trust Center policy is followed; this never accesses VBProject or changes policy.
"""
import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pythoncom
from win32com.client import DispatchEx
import xlsxwriter

from webapp.largeclean import clean_excel
from webapp.preserve import preserve_workbook
from webapp.workspace import CleanOptions

ROOT = Path('reports/real-excel').resolve()
FIXTURE_HASH = '0ced1464b3677e98f5e3a8c5d80135e18dc98dca39299f1a8cfd2a00999fbf9f'


def main():
    fixture = ROOT/'vbaProject.bin'
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == FIXTURE_HASH
    source = ROOT/'reviewed_original.xlsm'
    with xlsxwriter.Workbook(source) as book:
        book.add_vba_project(str(fixture))
        sheet = book.add_worksheet('Orders')
        sheet.write_row('A1', ['name', 'total'])
        sheet.write('A2', ' Alice ')
        sheet.write_formula('B2', '=1+2')
        book.add_worksheet('Hidden').hide()
    original = source.read_bytes()
    small = ROOT/'cleaned_small.xlsm'
    output, _ = preserve_workbook(source.name, original, CleanOptions(sheet='Orders', columns=['name'], trim=True))
    small.write_bytes(output.getvalue())
    output.close()
    large = ROOT/'cleaned_large.xlsm'
    clean_excel(source, large, CleanOptions(sheet='Orders', columns=['A'], trim=True), lambda: None)
    for path in [small, large]:
        with ZipFile(source) as a, ZipFile(path) as b:
            assert a.read('xl/vbaProject.bin') == b.read('xl/vbaProject.bin') == fixture.read_bytes()
    report = {'fixture_source': 'https://github.com/jmcnamara/XlsxWriter/blob/main/examples/vbaProject.bin',
              'fixture_sha256': FIXTURE_HASH, 'reviewed_macro': 'Sub say_hello(): MsgBox("Hello from Python!"): End Sub',
              'formula_paths': [], 'vba_execution': 'pending', 'trust_center_changed': False}
    excel = workbook = None
    pythoncom.CoInitialize()
    try:
        excel = DispatchEx('Excel.Application')
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.EnableEvents = False
        excel.AskToUpdateLinks = False
        excel.AutomationSecurity = 3
        for path in [small, large]:
            workbook = excel.Workbooks.Open(str(path), UpdateLinks=0)
            excel.CalculateFullRebuild()
            assert workbook.Worksheets('Orders').Range('A2').Value2 == 'Alice'
            assert workbook.Worksheets('Orders').Range('B2').Formula == '=1+2'
            assert workbook.Worksheets('Orders').Range('B2').Value2 == 3
            assert workbook.Worksheets('Hidden').Visible == 0
            workbook.Close(False)
            workbook = None
            report['formula_paths'].append(path.name)
        excel.AutomationSecurity = 2
        excel.Visible = True
        excel.DisplayAlerts = True
        workbook = excel.Workbooks.Open(str(large), UpdateLinks=0)
        report['has_vba_project'] = bool(workbook.HasVBProject)
        if '--approve-in-excel' in sys.argv:
            print('Review cleaned_large.xlsm in Excel. If Excel offers Enable Content, approve only this reviewed fixture. Do not change global policy. Type RUN here when ready, or CANCEL.', flush=True)
            if input().strip() != 'RUN':
                raise RuntimeError('Cancelled at per-workbook approval checkpoint')
        print('Excel is testing the reviewed greeting macro. Dismiss Hello from Python! with OK if shown.', flush=True)
        try:
            excel.Run("'cleaned_large.xlsm'!Module1.say_hello")
            report['vba_execution'] = 'passed: preserved Module1.say_hello completed in Microsoft Excel'
        except Exception as exc:
            report['vba_execution'] = 'blocked by existing Excel policy or execution error'
            report['reason'] = str(exc)[:700]
        assert source.read_bytes() == original
        report['source_unchanged'] = True
    finally:
        if workbook is not None:
            workbook.Close(False)
        if excel is not None:
            excel.Quit()
        pythoncom.CoUninitialize()
        (ROOT/'vba-preservation-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['vba_execution'].startswith('passed:') else 2


if __name__ == '__main__':
    raise SystemExit(main())
