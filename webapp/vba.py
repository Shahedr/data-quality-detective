"""Optional read-only VBA source inspection. NEVER executes workbook macros.

oletools is required for static VBA extraction/triage. Detection-only works
without the extra. Automated analysis cannot certify a macro as safe or correct.
"""

import re


def _code_without_comments_and_strings(source):
    """Strip comment and literal text for a best-effort keyword context check.

    This is not a complete VBA lexer/parser. A missing direct keyword cannot
    prove that the code is safe or free of dynamic invocation.
    """
    clean_lines = []
    for line in str(source).splitlines():
        if re.match(r"^\s*Rem(?:\s|$)", line, re.IGNORECASE):
            continue
        parts = []
        index = 0
        quoted = False
        while index < len(line):
            char = line[index]
            if char == '"':
                if quoted and index + 1 < len(line) and line[index + 1] == '"':
                    parts.extend([" ", " "])
                    index += 2
                    continue
                quoted = not quoted
                parts.append(" ")
            elif not quoted and char == "'":
                break
            elif quoted:
                parts.append(" ")
            else:
                parts.append(char)
            index += 1
        clean_lines.append("".join(parts))
    return "\n".join(clean_lines)


def _finding_context(category, keyword, clean_source):
    """Classify the kind of textual support for a scanner finding."""
    if category not in {"AutoExec", "Suspicious"}:
        return "scanner heuristic"
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", keyword):
        return "scanner heuristic"
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(keyword) + r"(?![A-Za-z0-9_])"
    if re.search(pattern, clean_source, re.IGNORECASE):
        return "code keyword found"
    return "comment/text-only or unverified"


def audit_vba(filename, data, project_present):
    result = {
        "vba_project_present": bool(project_present),
        "vba_executed": False,
        "source_scan_status": "no_vba" if not project_present else "not_installed",
        "modules": [],
        "findings": [],
        "finding_counts": {"autoexec": 0, "suspicious": 0, "ioc": 0, "other": 0,
                           "code_matches": 0, "context_only": 0, "heuristic": 0},
        "limitations": (
            "Static inspection only. Macros have not been compiled, executed, "
            "debugged, sandboxed, or verified for correct behavior."
        ),
    }
    if not project_present:
        return result

    try:
        from oletools.olevba import VBA_Parser
    except ImportError:
        result["limitations"] += (
            ' Install the optional ".[web,macro-audit]" extra for VBA source '
            "extraction and suspicious-pattern triage."
        )
        return result

    parser = None
    try:
        parser = VBA_Parser(filename, data=data)
        if not parser.detect_vba_macros():
            result["source_scan_status"] = "unreadable_or_empty_project"
            return result
        modules = []
        cleaned_sources = []
        for _, _, module_name, source in parser.extract_macros():
            if len(modules) >= 100:
                break
            # Do not return the raw macro source: it may contain credentials.
            cleaned_sources.append(_code_without_comments_and_strings(source))
            modules.append({
                "name": str(module_name)[:120],
                "source_lines": len(str(source).splitlines()),
            })
        result["modules"] = modules
        result["source_scan_status"] = "scanned"
        combined_code = "\n".join(cleaned_sources)
        for category, keyword, description in (parser.analyze_macros() or []):
            category = str(category)
            if category == "AutoExec":
                bucket = "autoexec"
            elif category == "Suspicious":
                bucket = "suspicious"
            elif category == "IOC":
                bucket = "ioc"
            else:
                bucket = "other"
            result["finding_counts"][bucket] += 1
            evidence = _finding_context(category, str(keyword), combined_code)
            if evidence == "code keyword found":
                result["finding_counts"]["code_matches"] += 1
            elif evidence == "comment/text-only or unverified":
                result["finding_counts"]["context_only"] += 1
            else:
                result["finding_counts"]["heuristic"] += 1
            if len(result["findings"]) < 60:
                result["findings"].append({
                    "category": category[:60],
                    "keyword": str(keyword)[:180],
                    "explanation": str(description)[:280],
                    "evidence": evidence,
                })
    except Exception:
        result["source_scan_status"] = "scan_failed"
        result["limitations"] += (
            " The VBA source could not be inspected; do not interpret missing "
            "findings as evidence of safety."
        )
    finally:
        if parser is not None:
            parser.close()
    return result
