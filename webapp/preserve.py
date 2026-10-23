"""Patch only reviewed literal cells; retain every other OOXML part verbatim."""
import io
from copy import copy
import posixpath
import re
from html import escape
from defusedxml import ElementTree as ET
from zipfile import ZipFile

from fastapi import HTTPException
from openpyxl.utils import get_column_letter

from webapp.workspace import CleanOptions, clean_frames, validate_excel_value


def preserve_workbook(name, data, options):
    if options.remove_duplicates:
        raise HTTPException(422, "Row removal is disabled for Excel: it can break formulas, VBA and named ranges. Use the audit to review duplicates in Excel.")
    frames, preview = clean_frames(name, data, options)
    original, _ = clean_frames(name, data, CleanOptions(sheet=options.sheet))
    selected = preview["sheet"]
    before, after = original[selected], frames[selected]
    changes = {}
    for col in range(len(after.columns)):
        for row in range(len(after)):
            old, new = before.iat[row, col], after.iat[row, col]
            if isinstance(old, str) and old != new:
                validate_excel_value(new)
                changes[f"{get_column_letter(col + 1)}{row + 2}"] = str(new)
    if not changes:
        return io.BytesIO(data), preview
    with ZipFile(io.BytesIO(data)) as src:
        names = src.namelist()
        if len(set(names)) != len(names):
            raise HTTPException(422, "Duplicate workbook package parts are unsupported.")
        if any(p.startswith("_xmlsignatures/") or "vbaprojectsignature" in p.lower() for p in names):
            raise HTTPException(422, "Signed workbooks cannot be cleaned without invalidating their signatures. Download the unchanged original instead.")
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        workbook = ET.fromstring(src.read("xl/workbook.xml"))
        relationships = ET.fromstring(src.read("xl/_rels/workbook.xml.rels"))
        tab = next(s for s in workbook.findall("m:sheets/m:sheet", ns) if s.attrib["name"] == selected)
        rel_id = tab.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        relation = next(r for r in relationships if r.attrib["Id"] == rel_id)
        target = relation.attrib["Target"]
        path = posixpath.normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
        if not path.startswith("xl/worksheets/") or relation.attrib.get("TargetMode") == "External":
            raise HTTPException(422, "Unsupported worksheet relationship; original remains unchanged.")
        xml = src.read(path).decode("utf-8")
        pending = set(changes)
        pattern = re.compile(r'<(?P<tag>(?:[A-Za-z_][\w.-]*:)?c)\b(?P<attrs>[^>]*?)(?:\s*/>|>(?P<body>.*?)</(?P=tag)\s*>)', re.S)
        def replace(match):
            attrs = match["attrs"]
            ref = re.search(r'\br\s*=\s*([\x22\x27])(.*?)\1', attrs)
            coordinate = ref[2] if ref else None
            if coordinate not in changes:
                return match[0]
            body = match["body"] or ""
            if re.search(r'<(?:[\w.-]+:)?f\b', body):
                raise HTTPException(422, f"{coordinate} contains a formula. Formula cells cannot be cleaned.")
            if any(tag.split(":")[-1] not in {"v", "is", "t"}
                   for tag in re.findall(r'<([\w:.-]+)\b', body)):
                raise HTTPException(422, f"{coordinate} contains rich text or unsupported cell features. It cannot be changed safely.")
            # Preserve style and metadata attributes, replacing only the value representation.
            attrs = re.sub(r'\s+t\s*=\s*([\x22\x27]).*?\1', '', attrs)
            prefix = match["tag"][:-1]
            value = escape(changes[coordinate], quote=False)
            pending.discard(coordinate)
            return f'<{match["tag"]}{attrs} t="inlineStr"><{prefix}is><{prefix}t xml:space="preserve">{value}</{prefix}t></{prefix}is></{match["tag"]}>'
        patched = pattern.sub(replace, xml).encode("utf-8")
        if pending:
            raise HTTPException(422, "Some cells could not be preserved safely. No changed workbook was generated.")
        output = io.BytesIO()
        with ZipFile(output, "w") as dst:
            dst.comment = src.comment
            for item in src.infolist():
                dst.writestr(copy(item), patched if item.filename == path else src.read(item.filename))
        output.seek(0)
        # Confirm every untouched part is byte-identical before offering the copy.
        with ZipFile(output) as result:
            if any(result.read(p) != src.read(p) for p in names if p != path):
                raise HTTPException(500, "Workbook preservation verification failed.")
        output.seek(0)
        return output, preview
