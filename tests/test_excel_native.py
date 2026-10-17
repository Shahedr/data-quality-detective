"""CI-safe tests for Excel native adapter: mocked COM, never launch Excel."""

import io
import json
from pathlib import Path

import pytest
from openpyxl import Workbook
from webapp.excel_native import (
    NativeExcelError, TRUST_PHRASE, _render_html, run_native_audit,
)


class FakeCell:
    def __init__(self, value):
        self.Value2 = value


class FakeWorksheet:
    def __init__(self, values):
        self.values = values

    def Range(self, cell):
        return FakeCell(self.values[cell])


class FakeSheets:
    def __init__(self, sheets):
        self.sheets = sheets

    def __call__(self, name):
        return FakeWorksheet(self.sheets[name])


class FakeWorkbook:
    def __init__(self, values):
        self.Worksheets = FakeSheets(values)
        self.save_called = False
        self.closed = False

    def Save(self):
        self.save_called = True

    def Close(self, SaveChanges=False):
        self.closed = True


class FakeWorkbooks:
    def __init__(self, workbook):
        self.workbook = workbook
        self.paths = []
        self.kwargs = []

    def Open(self, path, **kwargs):
        self.paths.append(Path(path))
        self.kwargs.append(kwargs)
        return self.workbook


class FakeExcel:
    def __init__(self, values, raises_run=False):
        self.Workbooks = FakeWorkbooks(FakeWorkbook(values))
        self.AutomationSecurity = None
        self.EnableEvents = None
        self.AskToUpdateLinks = None
        self.Visible = None
        self.DisplayAlerts = None
        self.recalculated = False
        self.macro = None
        self.quitted = False
        self.raises_run = raises_run

    def CalculateFullRebuild(self):
        self.recalculated = True

    def Run(self, qualified):
        if self.raises_run:
            raise RuntimeError("Macro execution blocked by Trust Center")
        self.macro = qualified
        return "OK"

    def Quit(self):
        self.quitted = True


def workbook_file(tmp_path, filename="test.xlsx", formula="=A2*3"):
    source = tmp_path / filename
    book = Workbook()
    ws = book.active
    ws.title = "Orders"
    ws.append(["id", "cost"])
    ws.append([2, formula])
    book.save(source)
    book.close()
    return source


def test_recalculate_native_uses_macro_disabled_excel_on_copy(tmp_path):
    source = workbook_file(tmp_path)
    before = source.read_bytes()
    excel = FakeExcel({"Orders": {"B2": 6}})
    output = tmp_path / "reports"

    result = run_native_audit(source, output, dispatch=lambda _: excel)
    assert result["excel_automation"] == "completed"
    assert result["mode"] == "recalculate"
    assert result["macro_executed"] is False
    assert result["formula_results_changed"] == 1
    assert result["changed_details"][0]["cell"] == "B2"
    assert result["changed_details"][0]["after"] == 6
    assert excel.AutomationSecurity == 3
    assert excel.EnableEvents is False
    assert excel.AskToUpdateLinks is False
    assert excel.Visible is False
    assert excel.DisplayAlerts is False
    assert excel.recalculated is True
    assert excel.macro is None
    assert excel.Workbooks.kwargs[0]["UpdateLinks"] == 0
    assert excel.Workbooks.workbook.save_called is True
    assert excel.Workbooks.workbook.closed is True
    assert excel.quitted is True
    assert source.read_bytes() == before
    working = excel.Workbooks.paths[0]
    assert working != source
    assert working.exists()
    folder = Path(result["report_folder"])
    assert folder.joinpath("native_report.html").exists()
    assert json.loads(folder.joinpath("native_report.json").read_text())["mode"] == "recalculate"


def test_macro_requires_named_explicit_consent_and_does_not_auto_run(tmp_path):
    src = workbook_file(tmp_path, "trusted.xlsm")
    out = tmp_path / "reports"
    with pytest.raises(NativeExcelError, match="exact"):
        run_native_audit(src, out, mode="macro", macro_name="Module1.Review")
    with pytest.raises(NativeExcelError, match="ordinary VBA"):
        run_native_audit(src, out, mode="macro", macro_name="Shell('oops')",
                         confirmation=TRUST_PHRASE)
    assert not out.exists()


def test_macro_uses_trust_center_ui_and_explicit_qualified_name(tmp_path):
    src = workbook_file(tmp_path, "trusted.xlsm")
    excel = FakeExcel({"Orders": {"B2": 6}})
    result = run_native_audit(
        src, tmp_path / "reports", mode="macro",
        macro_name="Module1.Review", confirmation=TRUST_PHRASE,
        dispatch=lambda _: excel,
    )
    assert result["excel_automation"] == "completed"
    assert result["macro_executed"] is True
    assert result["macro_return_value"] == "OK"
    assert excel.AutomationSecurity == 2
    assert excel.EnableEvents is False
    assert excel.Visible is True
    assert excel.DisplayAlerts is True
    assert excel.macro == "'trusted.xlsm'!Module1.Review"


def test_trust_center_macro_block_is_recorded_as_failed_not_success(tmp_path):
    src = workbook_file(tmp_path, "trusted.xlsm")
    excel = FakeExcel({"Orders": {"B2": 6}}, raises_run=True)
    result = run_native_audit(
        src, tmp_path / "reports", mode="macro",
        macro_name="Module1.Review", confirmation=TRUST_PHRASE,
        dispatch=lambda _: excel,
    )
    assert result["excel_automation"] == "failed"
    assert result["macro_executed"] is False
    assert "blocked" in result["warnings"][-1]
    assert excel.Workbooks.workbook.closed is True
    assert excel.quitted is True
    report = json.loads(
        Path(result["report_folder"], "native_report.json").read_text()
    )
    assert report["macro_executed"] is False


def test_original_folder_not_allowed_as_audit_output(tmp_path):
    source = workbook_file(tmp_path)
    with pytest.raises(NativeExcelError, match="separate output"):
        run_native_audit(source, tmp_path, dispatch=lambda _: FakeExcel({}))


def test_offline_native_report_html_escapes_dynamic_content():
    report = {
        "mode": "recalculate",
        "started_utc": "2026-10-17",
        "source_filename": '<script>alert("x")</script>.xlsx',
        "excel_automation": "completed",
        "formulas_inventory_count": 1,
        "formula_results_changed": 1,
        "macro_executed": False,
        "limitations": "none",
        "warnings": ['<img src=x onerror=alert("x")>'],
        "changed_details": [{
            "sheet": "Orders", "cell": "B2",
            "formula": "=2+3", "before": None,
            "after": '<script>alert("x")</script>',
        }],
    }
    html = _render_html(report)
    assert "<script>alert" not in html
    assert '<img src=x onerror=' not in html
    assert "&lt;script&gt;" in html


def test_macro_mode_rejects_unnecessary_macro_option_on_recalc(tmp_path):
    source = workbook_file(tmp_path)
    with pytest.raises(NativeExcelError, match="only accepted"):
        run_native_audit(source, tmp_path / "output",
                         mode="recalculate", macro_name="Module1.DoIt")



def test_desktop_gui_wrapper_imports_without_windows_runtime():
    """Importing the module alone must not launch or require a GUI."""
    import webapp.excel_desktop as desktop
    assert callable(desktop.launch)
    assert callable(desktop.main)
