# Windows Excel-native audits — supervised local component

The browser auditor inspects workbook data without executing VBA. **This
separate Windows-only command-line tool** adds real Microsoft Excel formula
recalculation and an optional, explicitly approved VBA macro run. It is **not
called from a web upload or API**.

## Supported and verified status

- **Implemented:** launch an independent Excel COM instance using `pywin32`,
  open a *working copy*, recalculate formulas with `CalculateFullRebuild`, compare
  Excel's values to the original saved formula caches, save the working copy,
  and write JSON + standalone HTML audit reports. Source and copy SHA-256
  fingerprints provide audit traceability.
- **Macro mode:** launch Excel visibly, follow its existing Trust Center
  policies, and request **one explicitly named VBA macro**. Requires an exact
  acknowledgement phrase. Macro source is not modified.
- **CI verified:** mocked Excel-automation tests on the supported Python matrix.
- **Not yet physically verified:** actual Excel COM automation on your Windows
  installation; macro behavior depends on your Excel version, trusted sources,
  permissions, add-ins and the workbook. A successful mock test does not prove
  every real workbook will behave correctly.

## Prerequisites

Microsoft Excel desktop installed on **Windows**, Python 3.10+, your GitHub ZIP
project folder, and the optional native dependency installed from that folder:

```powershell
python -m pip install -e ".[web,excel-native,macro-audit]"
```

Keep your original workbook closed and backed up.

## One-click Windows desktop interface

To choose the file and reports directory through familiar Windows browse
dialogs, launch:

```powershell
python -m webapp.excel_desktop
```

Select your XLSX or XLSM workbook, select a **different** output directory,
and click **Recalculate and Create Audit Report**. When Excel returns, the
GUI opens the local HTML report. This window only exposes formula recalculation
with macros disabled during automated opening; it intentionally does not expose
macro execution. Note that the desktop interface can wait indefinitely if
Excel itself becomes unresponsive.

## Formula recalculation (macros disabled during automated opening)

```powershell
python -m webapp.excel_native --file "C:\Data\workbook.xlsm" --output-dir "C:\DQD-Reports" --mode recalculate
```

Replace the example file path with your real file path. The output directory
**must differ from the source workbook directory**. The tool creates a new
unique `excel_native_...` run directory containing the workbook **copy**,
`native_report.json`, and `native_report.html`.

Normal recalculation mode sets `AutomationSecurity` to Excel's
`msoAutomationSecurityForceDisable`, disables events, and prevents automatic
link updates while opening. It does not intentionally execute VBA macros.
**Excel add-ins, XLM macro prompts, external workbook behavior, or formulas
using external services can still present risk**, and this is not an isolation
boundary. Review the file source before running.

It inventories up to 20,000 formulas and records how many formula results
differ from the original saved caches, with up to 2,000 concrete cell changes.
A result change may simply reflect stale original calculation caches.
It does not prove formula logic is correct.

## Explicit VBA macro execution (high risk)

**Only on VBA you own, have reviewed, and trust. Run first in a disposable
Windows VM or sandbox**, not on a production/work computer holding sensitive
information. Copying a workbook is not a security sandbox: a macro can edit
other files, invoke system commands, or reach the internet.

For a trusted macro such as `Module1.ReviewData`:

```powershell
python -m webapp.excel_native --file "C:\Data\trusted.xlsm" --output-dir "C:\DQD-Reports" --mode macro --macro-name "Module1.ReviewData" --confirm-trust "I UNDERSTAND VBA CAN RUN SYSTEM COMMANDS"
```

- Microsoft Excel is opened **visibly** in a new Excel instance.
- The tool **never switches Trust Center to enable all macros**, does not
  modify trusted locations or user registry settings, and does not enable
  programmatic VBA-project editing. It follows **your current Trust Center
  setting**, including any prompts or restrictions.
- The designated `Application.Run` macro runs **only if permitted by Excel**.
  Excel may block it; this is a failure that the tool reports. Never weaken
  Trust Center security merely to get a green result.
- Events are disabled during opening, but once a macro starts, it has normal
  user privileges and may itself invoke any VBA or system calls. There is no
  timeout or guaranteed isolation in this release. If Excel freezes, the tool
  may remain blocked; use a disposable VM with a checkpoint.
- The working copy's saved contents **may still include the original macros**.
  The **HTML/JSON reports** include no executable VBA.
- If the macro modifies the original file indirectly, the SHA-256 check should
  detect that after execution (but cannot prevent the modification).

## Product boundaries

This is a **developer preview and local test harness**, not a production-grade
untrusted VBA execution sandbox. Production support would require dedicated
disposable Windows VMs, restricted identities, no network, egress monitoring,
explicit approvals, execution timeouts, per-job teardown, audit logs and
operational/legal review. It does not guarantee compatibility with ActiveX,
external links, add-ins, Excel events, digitally signed VBA, XLM macros, custom
UDFs, or every spreadsheet feature. There is no automatic macro execution
from the local browser or a hosted SaaS service.
