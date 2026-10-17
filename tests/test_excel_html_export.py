"""Complete annotated HTML export and safe macro-enabled Excel input tests."""

import io
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi.testclient import TestClient
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

from webapp.app import app

client = TestClient(app)


def post(name, raw, path="/api/analyze"):
    return client.post(path, files={"file": (name, raw)})


def make_workbook(include_macro_marker=False, unsupported=False):
    book = Workbook()
    sheet = book.active
    sheet.title = "Orders"
    sheet.append(["id", "status", "region"])
    sheet.append([1, "Open", "North"])
    sheet.append([2, "Unlisted", "Invalid"])
    sheet.append([3, "Closed", "South"])

    lookup = book.create_sheet("Lists")
    lookup["A1"] = "North"
    lookup["A2"] = "South"

    status_validation = DataValidation(type="list", formula1='"Open,Closed"')
    sheet.add_data_validation(status_validation)
    status_validation.add("B2:B4")

    region_validation = DataValidation(
        type="list", formula1="='Lists'!$A$1:$A$2"
    )
    sheet.add_data_validation(region_validation)
    region_validation.add("C2:C4")

    if unsupported:
        dynamic = DataValidation(type="list", formula1="=INDIRECT($B2)")
        sheet.add_data_validation(dynamic)
        dynamic.add("A2:A4")
    book.active = 0
    stream = io.BytesIO()
    book.save(stream)
    book.close()
    if include_macro_marker:
        # Marker tests ZIP archive inspection, NOT VBA execution or a real macro.
        stream.seek(0, io.SEEK_END)
        with ZipFile(stream, "a", compression=ZIP_DEFLATED) as archive:
            archive.writestr("xl/vbaProject.bin", b"safe-test-placeholder-no-executable-vba")
    return stream.getvalue()


def test_html_export_contains_all_sample_rows_and_actual_issue_flags():
    with open("examples/messy_orders.csv", "rb") as f:
        raw = f.read()
    result = post("messy_orders.csv", raw, "/api/export/html")
    assert result.status_code == 200, result.text[:500]
    assert "attachment" in result.headers["content-disposition"]
    assert "messy_orders_full_report.html" in result.headers["content-disposition"]
    html = result.text
    assert "Full spreadsheet — all rows" in html
    assert '<tr class="duplicate"><td class="row-index">11</td>' in html
    assert '<tr class="duplicate"><td class="row-index">12</td>' in html
    assert "not-a-date" in html
    assert "Invalid date" in html
    assert "Included" in html
    assert "Mixed numeric/text value" in html
    assert '<td class="missing"' in html
    assert "Data row" in html
    # Source has twelve data rows and the complete export must include each.
    assert html.count('<td class="row-index">') == 12


def test_full_html_export_does_not_truncate_long_cells_and_escapes_html():
    raw = (
        "id,text\n1,<img src=x onerror=alert(1)>\n"
        + "2," + "Z" * 800 + "\n"
    ).encode()
    html = post("untrusted.csv", raw, "/api/export/html").text
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert "Z" * 800 in html
    assert html.count('<td class="row-index">') == 2


def test_html_export_contains_final_row_past_50000():
    count = 50_001
    rows = "id,value\n" + "".join(
        f"{i},ITEM-{i:05d}\n" for i in range(1, count + 1)
    )
    result = post("big.csv", rows.encode(), "/api/export/html")
    assert result.status_code == 200, result.text[:500]
    assert result.text.count('<td class="row-index">') == count
    assert "ITEM-50001" in result.text
    assert 'max-height:75vh' in result.text


def test_literal_and_range_excel_dropdowns_flag_actual_invalid_cells():
    data = make_workbook()
    response = post("orders.xlsx", data)
    assert response.status_code == 200, response.text[:500]
    payload = response.json()
    metadata = payload["workbook"]
    assert metadata["worksheet_analyzed"] == "Orders"
    assert metadata["sheets_in_workbook"] == 2
    assert metadata["dropdown_rules"] == 2
    assert metadata["dropdown_rules_unchecked"] == 0
    assert metadata["dropdown_invalid_cells"] == 2
    assert metadata["vba_executed"] is False

    grid = payload["spreadsheet"]["rows"]
    assert grid[0]["cell_flags"][1] == []
    assert grid[1]["cell_flags"][1] == ["dropdown_invalid"]
    assert grid[1]["cell_flags"][2] == ["dropdown_invalid"]
    assert "dropdown_invalid" not in grid[2]["cell_flags"][1]

    filtered = client.post(
        "/api/rows",
        files={"file": ("orders.xlsx", data)},
        data={"page": "1", "issue": "dropdown_invalid"},
    )
    assert filtered.status_code == 200, filtered.text[:500]
    assert filtered.json()["total_matching_rows"] == 1
    assert filtered.json()["rows"][0]["row_number"] == 2

    html = post("orders.xlsx", data, "/api/export/html").text
    assert "Value not in supported dropdown list" in html
    assert "Full spreadsheet — all rows" in html
    assert html.count('<td class="row-index">') == 3


def test_xlsm_accepts_cell_data_without_executing_macros():
    raw = make_workbook(include_macro_marker=True)
    response = post("macro_orders.xlsm", raw)
    assert response.status_code == 200, response.text[:500]
    result = response.json()
    assert result["summary"]["rows"] == 3
    meta = result["workbook"]
    assert meta["macro_enabled_format"] is True
    assert meta["vba_project_present"] is True
    assert meta["vba_executed"] is False
    assert any("never executed" in warning for warning in meta["warnings"])
    full = post("macro_orders.xlsm", raw, "/api/export/html")
    assert full.status_code == 200
    assert "VBA code executed: No" in full.text
    assert full.text.count('<td class="row-index">') == 3


def test_dynamic_list_rule_explicitly_reported_as_unchecked():
    response = post("dynamic.xlsx", make_workbook(unsupported=True))
    assert response.status_code == 200, response.text[:500]
    meta = response.json()["workbook"]
    assert meta["dropdown_rules"] == 3
    assert meta["dropdown_rules_unchecked"] == 1
    assert any("unsupported sources" in w for w in meta["warnings"])


def test_csv_has_no_excel_metadata():
    result = post("basic.csv", b"id,status\n1,ok\n2,ok\n")
    assert result.status_code == 200
    assert result.json()["workbook"] is None
