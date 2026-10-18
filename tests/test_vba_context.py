"""VBA heuristic triage should distinguish code from comments and strings."""

import sys
import types

from webapp.vba import _code_without_comments_and_strings, audit_vba


def test_vba_clean_lexer_ignores_comments_strings_and_escaped_quotes():
    source = (
        "Option Explicit\n"
        "' Shell cmd is not called\n"
        "Rem Shell comment\n"
        'message = "Shell ""not real"""\n'
        "Call DoWork()\n"
    )
    clean = _code_without_comments_and_strings(source)
    assert "Shell" not in clean
    assert "Call DoWork()" in clean


def test_report_explains_comment_only_shell_and_hex_heuristic(monkeypatch):
    class FakeParser:
        def __init__(self, filename, data):
            self.filename = filename
            self.data = data

        def detect_vba_macros(self):
            return True

        def extract_macros(self):
            return [(
                "root", "VBA/Module1", "DQDTestModule",
                "Option Explicit\n"
                "' This macro does not call Shell\n"
                "Sub DQD_TestMacro()\n"
                '  Range("B10").Value = "Success"\n'
                "End Sub\n",
            )]

        def analyze_macros(self):
            return [
                ("Suspicious", "Shell", "May launch system commands"),
                ("Suspicious", "Hex Strings", "May indicate obfuscation"),
            ]

        def close(self):
            pass

    fake_package = types.ModuleType("oletools")
    fake_module = types.ModuleType("oletools.olevba")
    fake_module.VBA_Parser = FakeParser
    monkeypatch.setitem(sys.modules, "oletools", fake_package)
    monkeypatch.setitem(sys.modules, "oletools.olevba", fake_module)

    audit = audit_vba("test.xlsm", b"dummy-data", True)
    assert audit["source_scan_status"] == "scanned"
    assert audit["finding_counts"]["suspicious"] == 2
    assert audit["finding_counts"]["code_matches"] == 0
    assert audit["finding_counts"]["context_only"] == 1
    assert audit["finding_counts"]["heuristic"] == 1
    assert audit["findings"][0]["evidence"] == "comment/text-only or unverified"
    assert audit["findings"][1]["evidence"] == "scanner heuristic"
    assert audit["vba_executed"] is False


def test_report_preserves_real_shell_statement_as_code_match(monkeypatch):
    class RealCodeParser:
        def __init__(self, filename, data):
            pass

        def detect_vba_macros(self):
            return True

        def extract_macros(self):
            return [(
                "root", "VBA/Module1", "Module1",
                "Sub RunMe()\n    Shell \"cmd.exe\"\nEnd Sub\n"
            )]

        def analyze_macros(self):
            return [("Suspicious", "Shell", "May launch executable")]

        def close(self):
            pass

    package = types.ModuleType("oletools")
    module = types.ModuleType("oletools.olevba")
    module.VBA_Parser = RealCodeParser
    monkeypatch.setitem(sys.modules, "oletools", package)
    monkeypatch.setitem(sys.modules, "oletools.olevba", module)

    audit = audit_vba("macro.xlsm", b"test", True)
    assert audit["finding_counts"]["code_matches"] == 1
    assert audit["findings"][0]["evidence"] == "code keyword found"
