"""Optional read-only VBA source inspection. NEVER executes workbook macros.

oletools is required for static VBA extraction/triage. Detection-only works
without the extra. Automated analysis cannot certify a macro as safe or correct.
"""

def audit_vba(filename, data, project_present):
    result = {
        "vba_project_present": bool(project_present),
        "vba_executed": False,
        "source_scan_status": "no_vba" if not project_present else "not_installed",
        "modules": [],
        "findings": [],
        "finding_counts": {"autoexec": 0, "suspicious": 0, "ioc": 0, "other": 0},
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
        for _, _, module_name, source in parser.extract_macros():
            if len(modules) >= 100:
                break
            # Do not return the raw macro source: it may contain credentials.
            modules.append({
                "name": str(module_name)[:120],
                "source_lines": len(str(source).splitlines()),
            })
        result["modules"] = modules
        result["source_scan_status"] = "scanned"
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
            if len(result["findings"]) < 60:
                result["findings"].append({
                    "category": category[:60],
                    "keyword": str(keyword)[:180],
                    "explanation": str(description)[:280],
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
