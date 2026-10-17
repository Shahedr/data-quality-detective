"""End-to-end tests for the local browser MVP API."""

import io

import pandas as pd
from fastapi.testclient import TestClient

from webapp.app import MAX_FILE_BYTES, app

client = TestClient(app)


def test_home_page_and_health():
    home = client.get("/")
    assert home.status_code == 200
    assert "Data Quality Detective" in home.text
    assert "Choose file" in home.text
    assert client.get("/health").json()["status"] == "ok"


def test_example_csv_produces_real_quality_report():
    with open("examples/messy_orders.csv", "rb") as source:
        content = source.read()

    response = client.post(
        "/api/analyze",
        files={"file": ("messy_orders.csv", content, "text/csv")},
    )

    assert response.status_code == 200, response.text
    result = response.json()
    summary = result["summary"]
    assert summary["rows"] == 12
    assert summary["columns"] == 8
    assert summary["duplicate_rows"] == 1
    assert summary["columns_with_missing"] == 2
    assert summary["mixed_numeric_text_columns"] == 1
    assert summary["date_columns_with_invalid_values"] == 1
    assert summary["numeric_columns_with_outliers"] == 2
    assert result["report_json"]["summary"] == summary
    assert "<!doctype html>" in result["report_html"].lower()
    assert len(result["columns"]) == 8


def test_web_app_handles_50001_rows_csv():
    count = 50_001
    df = pd.DataFrame({"id": range(count), "score": [20.0] * count})
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    response = client.post(
        "/api/analyze",
        files={"file": ("large.csv", buffer.getvalue(), "text/csv")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["rows"] == count


def test_web_app_handles_excel():
    buffer = io.BytesIO()
    pd.DataFrame({"order_id": [1, 2, 2], "amount": [10, 11, 11]}).to_excel(
        buffer, index=False
    )
    response = client.post(
        "/api/analyze",
        files={"file": ("orders.xlsx", buffer.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["duplicate_rows"] == 1


def test_rejects_unsupported_formats():
    response = client.post(
        "/api/analyze", files={"file": ("data.json", b"{}", "application/json")}
    )
    assert response.status_code == 415


def test_rejects_oversized_uploads():
    response = client.post(
        "/api/analyze",
        files={"file": ("large.csv", b"a" * (MAX_FILE_BYTES + 1), "text/csv")},
    )
    assert response.status_code == 413


def test_rejects_empty_and_malformed_workbook():
    empty = client.post("/api/analyze", files={"file": ("empty.csv", b"")})
    invalid = client.post(
        "/api/analyze", files={"file": ("broken.xlsx", b"not-a-workbook")}
    )
    assert empty.status_code == 400
    assert invalid.status_code == 422


def test_rejects_100001_rows():
    content = "id\n" + "\n".join(str(i) for i in range(100_001)) + "\n"
    response = client.post(
        "/api/analyze", files={"file": ("too_many.csv", content.encode())}
    )
    assert response.status_code == 413


def test_user_column_text_is_escaped_in_html_report():
    csv_bytes = b'<img src=x onerror=alert(1)>,value\none,10\ntwo,11\n'
    response = client.post(
        "/api/analyze", files={"file": ("untrusted.csv", csv_bytes)}
    )
    assert response.status_code == 200
    html = response.json()["report_html"]
    assert "&lt;img" in html
    assert '<img src=x onerror=alert(1)>' not in html
