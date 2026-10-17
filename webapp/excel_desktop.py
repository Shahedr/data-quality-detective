"""Minimal Windows desktop launcher for supervised Excel formula recalculation.

This GUI deliberately does NOT expose VBA execution. Macro runs must use the
separate CLI with the exact opt-in acknowledgement from NATIVE_EXCEL.md.
"""

from pathlib import Path
import queue
import sys
import threading
import webbrowser

from webapp.excel_native import run_native_audit


def launch():
    if sys.platform != "win32":
        raise RuntimeError("Desktop Excel validation requires Windows.")

    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("Data Quality Detective | Excel Native Validation")
    root.geometry("650x420")
    root.minsize(570, 380)
    root.configure(bg="#f5f7fc")

    file_var = tk.StringVar()
    output_var = tk.StringVar(
        value=str(Path.home() / "Documents" / "DataQualityDetectiveReports")
    )
    status_var = tk.StringVar(value="Choose an Excel workbook to audit.")
    results = queue.Queue()
    working = {"busy": False}

    outer = ttk.Frame(root, padding=24)
    outer.pack(fill="both", expand=True)
    ttk.Label(
        outer, text="Excel Native Validation",
        font=("Segoe UI", 19, "bold")
    ).pack(anchor="w", pady=(0, 7))
    ttk.Label(
        outer,
        text="Recalculate with real Microsoft Excel, compare formula values, "
             "and create HTML/JSON reports. Your source workbook is not overwritten.",
        wraplength=575,
    ).pack(anchor="w", pady=(0, 18))

    ttk.Label(outer, text="Excel workbook (.xlsx / .xlsm)").pack(anchor="w")
    frow = ttk.Frame(outer)
    frow.pack(fill="x", pady=(5, 14))
    ttk.Entry(frow, textvariable=file_var).pack(side="left", fill="x", expand=True)

    def choose_file():
        value = filedialog.askopenfilename(
            title="Select an Excel workbook",
            filetypes=[("Excel Workbooks", "*.xlsx *.xlsm")],
        )
        if value:
            file_var.set(value)

    ttk.Button(frow, text="Browse…", command=choose_file).pack(side="left", padx=(9, 0))

    ttk.Label(outer, text="Reports folder (must differ from workbook's folder)").pack(anchor="w")
    orow = ttk.Frame(outer)
    orow.pack(fill="x", pady=(5, 15))
    ttk.Entry(orow, textvariable=output_var).pack(side="left", fill="x", expand=True)

    def choose_output():
        value = filedialog.askdirectory(title="Choose report output directory")
        if value:
            output_var.set(value)

    ttk.Button(orow, text="Browse…", command=choose_output).pack(side="left", padx=(9, 0))
    ttk.Label(
        outer,
        text="Excel macros are disabled while this action opens the workbook. "
             "Excel add-ins and external sources can still cause side effects. "
             "Only analyze files you trust; native Excel is not a sandbox.",
        wraplength=575,
        foreground="#8b481b",
    ).pack(anchor="w", pady=(0, 15))

    action = ttk.Button(outer, text="Recalculate and Create Audit Report")
    action.pack(anchor="w", pady=(0, 12))
    ttk.Label(outer, textvariable=status_var, wraplength=570).pack(anchor="w")

    def start():
        if working["busy"]:
            return
        source = file_var.get().strip()
        destination = output_var.get().strip()
        if not source or not Path(source).is_file():
            messagebox.showerror("Select file", "Choose an existing XLSX or XLSM workbook.")
            return
        if not destination:
            messagebox.showerror("Select folder", "Choose a separate output directory.")
            return

        working["busy"] = True
        action.configure(state="disabled")
        status_var.set("Microsoft Excel is recalculating a workbook copy…")

        def job():
            try:
                output = run_native_audit(
                    source, destination, mode="recalculate"
                )
                results.put(("done", output))
            except Exception as exc:
                results.put(("error", str(exc)))

        threading.Thread(target=job, daemon=True).start()

    def poll():
        try:
            kind, payload = results.get_nowait()
        except queue.Empty:
            pass
        else:
            working["busy"] = False
            action.configure(state="normal")
            if kind == "error":
                status_var.set("Audit could not start.")
                messagebox.showerror("Excel audit failed", payload[:700])
            else:
                success = payload["excel_automation"] == "completed"
                location = Path(payload["report_folder"]) / "native_report.html"
                status_var.set(
                    ("Audit completed." if success else "Audit finished with errors.")
                    + " Review the HTML report and warnings."
                )
                if location.exists():
                    webbrowser.open(location.as_uri())
                if not success:
                    messagebox.showwarning(
                        "Native Excel audit issue",
                        "Microsoft Excel did not complete successfully. "
                        "Check the HTML/JSON reports for details.",
                    )
        root.after(200, poll)

    action.configure(command=start)
    root.after(200, poll)
    root.mainloop()


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description="Launch the supervised Windows Excel recalculation GUI."
    )
    parser.parse_args(argv)
    launch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
