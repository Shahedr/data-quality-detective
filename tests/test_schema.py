import pandas as pd
import pytest

from dqdetect.schema import load_schema, validate_schema


def test_schema_validation_passes_for_expected_structure():
    df = pd.DataFrame(
        {
            "order_id": [1, 2],
            "order_date": ["2026-01-01", "2026-01-02"],
            "region": ["Midwest", "West"],
        }
    )
    rules = {
        "required_columns": ["order_id", "order_date"],
        "column_types": {
            "order_id": "numeric",
            "order_date": "date",
            "region": "text",
        },
        "allow_extra_columns": True,
    }

    result = validate_schema(df, rules)

    assert result["valid"] is True
    assert result["missing_required_columns"] == []
    assert result["type_mismatches"] == []


def test_schema_validation_flags_missing_and_type_mismatch():
    df = pd.DataFrame(
        {
            "order_id": ["A", "B"],
            "extra": [1, 2],
        }
    )
    rules = {
        "required_columns": ["order_id", "order_date"],
        "column_types": {"order_id": "numeric"},
        "allow_extra_columns": False,
    }

    result = validate_schema(df, rules)

    assert result["valid"] is False
    assert result["missing_required_columns"] == ["order_date"]
    assert result["unexpected_columns"] == ["extra"]
    assert result["type_mismatches"][0]["column"] == "order_id"


def test_load_schema_rejects_unknown_type(tmp_path):
    path = tmp_path / "schema.json"
    path.write_text(
        '{"column_types": {"amount": "currency"}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported schema type"):
        load_schema(path)
