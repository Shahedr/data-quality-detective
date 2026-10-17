"""Actual row/cell attribution and stateless spreadsheet pagination tests."""

import io

import pandas as pd
from fastapi.testclient import TestClient

from webapp.app import app

client = TestClient(app)


def _sample():
    with open("examples/messy_orders.csv", "rb") as f:
        return f.read()


def _post(file_content, *, issue="all", page=1, name="orders.csv", route="/api/rows"):
    body = {"page": str(page), "issue": issue} if route == "/api/rows" else {}
    return client.post(
        route,
        data=body,
        files={"file": (name, file_content, "text/csv")},
    )


def test_actual_cell_flags_for_sample_dataset():
    response = _post(_sample(), route="/api/analyze")
    assert response.status_code == 200, response.text
    result = response.json()
    grid = result["spreadsheet"]
    assert grid["total_rows"] == 12
    assert grid["total_matching_rows"] == 12
    assert grid["page"] == 1
    assert grid["pages"] == 1
    assert len(grid["columns"]) == 8
    rows = {row["row_number"]: row for row in grid["rows"]}
    cols = {col: i for i, col in enumerate(grid["columns"])}
    assert rows[2]["values"][cols["freight_cost"]] == "Included"
    assert "mixed" in rows[2]["cell_flags"][cols["freight_cost"]]
    assert rows[4]["values"][cols["order_date"]] == "not-a-date"
    assert "invalid_date" in rows[4]["cell_flags"][cols["order_date"]]
    assert rows[5]["values"][cols["customer_id"]] is None
    assert "missing" in rows[5]["cell_flags"][cols["customer_id"]]
    assert "missing" in rows[6]["cell_flags"][cols["freight_cost"]]
    assert "outlier" in rows[10]["cell_flags"][cols["quantity"]]
    assert rows[11]["row_flags"] == ["duplicate"]
    assert rows[12]["row_flags"] == ["duplicate"]
    # The CLI counts one *extra* duplicate; the grid shows both matching rows.
    assert result["summary"]["duplicate_rows"] == 1
    assert "Highlighted data excerpt" in result["report_html"]
    assert "not-a-date" in result["report_html"]
    assert "Included" in result["report_html"]
    assert "(blank)" in result["report_html"]


def test_filter_specific_rows_and_excludes_unrelated_rows():
    source = _sample()
    expected = {
        "duplicate": [11, 12],
        "missing": [5, 6],
        "invalid_date": [4],
        "mixed": [2],
    }
    for issue, row_numbers in expected.items():
        response = _post(source, issue=issue)
        assert response.status_code == 200, response.text
        grid = response.json()
        assert grid["total_matching_rows"] == len(row_numbers)
        assert [x["row_number"] for x in grid["rows"]] == row_numbers
    flagged = _post(source, issue="flagged").json()
    assert flagged["flagged_rows"] == flagged["total_matching_rows"]
    assert 11 in [row["row_number"] for row in flagged["rows"]]
    outliers = _post(source, issue="outlier").json()
    assert 10 in [row["row_number"] for row in outliers["rows"]]


def test_page_two_and_three_show_correct_source_row_and_flags():
    rows = [{"id": i + 1, "order_date": "2025-01-01"} for i in range(105)]
    rows[-1]["order_date"] = "invalid"
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    raw = buf.getvalue()

    p2 = _post(raw, page=2).json()
    assert p2["pages"] == 3
    assert p2["total_matching_rows"] == 105
    assert len(p2["rows"]) == 50
    assert p2["rows"][0]["row_number"] == 51
    p3 = _post(raw, page=3).json()
    assert len(p3["rows"]) == 5
    assert p3["rows"][-1]["row_number"] == 105
    assert "invalid_date" in p3["rows"][-1]["cell_flags"][1]
    filtered = _post(raw, issue="invalid_date").json()
    assert filtered["total_matching_rows"] == 1
    assert filtered["rows"][0]["row_number"] == 105


def test_excel_grid_flags_duplicated_and_missing_cells():
    buf = io.BytesIO()
    pd.DataFrame({
        "id": [1, 1, 2],
        "customer": ["A", "A", None],
        "amount": [10, 10, 11],
    }).to_excel(buf, index=False)
    result = _post(buf.getvalue(), name="book.xlsx", route="/api/analyze")
    assert result.status_code == 200, result.text
    grid = result.json()["spreadsheet"]
    assert grid["total_rows"] == 3
    assert grid["rows"][0]["row_flags"] == ["duplicate"]
    assert grid["rows"][1]["row_flags"] == ["duplicate"]
    assert "missing" in grid["rows"][2]["cell_flags"][1]


def test_invalid_grid_navigation_does_not_crash():
    src = _sample()
    assert _post(src, page=0).status_code == 422
    assert _post(src, page=999).status_code == 422
    assert _post(src, issue="invalid-type").status_code == 422


def test_malicious_cell_text_and_header_escaped_in_downloaded_html():
    header = "<img src=x onerror=alert(1)>"
    value = "<script>alert('x')</script>"
    content = f"name,{header}\n{value},5\n".encode()
    result = _post(content, route="/api/analyze")
    assert result.status_code == 200, result.text
    html = result.json()["report_html"]
    assert header not in html
    assert value not in html
    assert "&lt;img" in html
    # Values are safely inserted as text nodes in the browser grid.


def test_constant_columns_are_not_misrepresented_as_bad_cells():
    raw = b"id,status\n1,OK\n2,OK\n3,OK\n"
    grid = _post(raw).json()
    assert grid["flagged_rows"] == 0
    assert grid["total_matching_rows"] == 3
    assert all(not any(r["cell_flags"]) for r in grid["rows"])
    assert _post(raw, issue="flagged").json()["rows"] == []


def test_large_csv_paginates_without_returning_all_rows():
    count = 50_001
    content = ("id,amount\n" + "".join(f"{i},10\n" for i in range(count))).encode()
    result = _post(content, route="/api/analyze")
    assert result.status_code == 200, result.text
    grid = result.json()["spreadsheet"]
    assert grid["total_rows"] == count
    assert len(grid["rows"]) == 50
    last_page = _post(content, page=1001)
    assert last_page.status_code == 200
    grid = last_page.json()
    assert len(grid["rows"]) == 1
    assert grid["rows"][0]["row_number"] == 50_001
