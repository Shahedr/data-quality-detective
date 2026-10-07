from pathlib import Path

import pandas as pd


SUPPORTED_SUFFIXES = {".csv", ".xlsx"}


def _normalize_sheet(sheet):
    if sheet is None:
        return 0

    if isinstance(sheet, str) and sheet.isdigit():
        return int(sheet)

    return sheet


def load_data(path, sheet=None):
    source = Path(path)

    if not source.exists():
        raise FileNotFoundError(f"File not found: {source}")

    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise ValueError(
            f"Unsupported file type '{suffix}'. Supported types: {supported}"
        )

    if suffix == ".csv":
        return pd.read_csv(source)

    return pd.read_excel(source, sheet_name=_normalize_sheet(sheet))
