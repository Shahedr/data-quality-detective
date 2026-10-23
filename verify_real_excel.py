"""Explicit Windows integration check, outside CI; only generated fixture code runs."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pythoncom
from win32com.client import DispatchEx

from webapp.preserve import preserve_workbook
from webapp.workspace import CleanOptions

ROOT = Path('reports/real-excel').resolve()
MACRO = '''Public Function DQDVerification() As Long
    DQDVerification = 42
End Function'''


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    report = {'fixture_macro_source': MACRO, 'formula_check': 'pending', 'vba_check': 'pending'}
    pythoncom.CoInitialize()
    excel = book = None
    try:
        excel = DispatchEx('Excel.Application')
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.EnableEvents = False
        excel.AskToUpdateLinks = False
        excel.AutomationSecurity = 3
        report['excel_version'] = excel.Version
        book = excel.Workbooks.Add()
        sheet = book.Worksheets(1)
        sheet.Name = 'Orders'
        sheet.Range('A1:D1').Value = (('name', 'quantity', 'price', 'total'),)
        sheet.Range('A2:C2').Value = ((' Alice ', 3, 7),)
        sheet.Range('D2').Formula = '=B2*C2'
        sheet.Range('D2').NumberFormat = '0.00'
        hidden = book.Worksheets.Add()
        hidden.Name = 'Hidden'
        hidden.Visible = 0
        source = ROOT / 'original.xlsx'
        book.SaveAs(str(source), FileFormat=51)
        book.Close(False)
        book = None
        before = source.read_bytes()
        output, _ = preserve_workbook(source.name, before, CleanOptions(sheet='Orders', columns=['name'], trim=True))
        cleaned = ROOT / 'cleaned.xlsx'
        cleaned.write_bytes(output.getvalue())
        output.close()
        book = excel.Workbooks.Open(str(cleaned), UpdateLinks=0)
        excel.CalculateFullRebuild()
        sheet = book.Worksheets('Orders')
        assert sheet.Range('A2').Value2 == 'Alice'
        assert sheet.Range('D2').Formula == '=B2*C2'
        assert sheet.Range('D2').Value2 == 21
        assert sheet.Range('D2').NumberFormat == '0.00'
        assert book.Worksheets('Hidden').Visible == 0
        assert source.read_bytes() == before
        report['formula_check'] = 'passed: cleaned copy opens, recalculates to 21, formula/style/hidden sheet preserved; source unchanged'
        try:
            module = book.VBProject.VBComponents.Add(1)
            module.Name = 'DQDTestModule'
            module.CodeModule.AddFromString(MACRO)
        except Exception as exc:
            report['vba_check'] = 'blocked: VBA project access disabled by existing Excel policy; no Trust Center settings were changed'
            report['vba_reason'] = str(exc)[:600]
        else:
            sheet.Range('A2').Value2 = ' Alice '
            macro_source = ROOT / 'original.xlsm'
            book.SaveAs(str(macro_source), FileFormat=52)
            book.Close(False)
            book = None
            original = macro_source.read_bytes()
            output, _ = preserve_workbook(macro_source.name, original, CleanOptions(sheet='Orders', columns=['name'], trim=True))
            macro_copy = ROOT / 'cleaned.xlsm'
            macro_copy.write_bytes(output.getvalue())
            output.close()
            with ZipFile(macro_source) as a, ZipFile(macro_copy) as b:
                assert a.read('xl/vbaProject.bin') == b.read('xl/vbaProject.bin')
            # Follow existing policy; never lower security or trust a directory.
            excel.AutomationSecurity = 2
            book = excel.Workbooks.Open(str(macro_copy), UpdateLinks=0)
            assert excel.Run("'cleaned.xlsm'!DQDTestModule.DQDVerification") == 42
            assert book.Worksheets('Orders').Range('A2').Value2 == 'Alice'
            assert macro_source.read_bytes() == original
            report['vba_check'] = 'passed: reviewed fixture returns 42 after preserved cleaning; VBA binary and source unchanged'
        report['source_sha256'] = hashlib.sha256(before).hexdigest()
    finally:
        if book is not None:
            book.Close(False)
        if excel is not None:
            excel.Quit()
        pythoncom.CoUninitialize()
        (ROOT / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['vba_check'].startswith('passed:') else 2


if __name__ == '__main__':
    raise SystemExit(main())
