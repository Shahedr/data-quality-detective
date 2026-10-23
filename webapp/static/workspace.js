/* Stateless review tools: no local storage, external chart service or AI provider. */
"use strict";
window.DQDWorkspace = (() => {
  let file, sheet, report, preview, controller, version = 0;
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const byId = id => document.getElementById(id);
  const root = el("section", undefined, "panel workspace-panel hidden");
  root.id = "workspaceTools";
  root.setAttribute("aria-label", "Review workspace");
  // Script loads before the dashboard's inline code; results already exists.
  byId("results").append(root);
  const style = el("style");
  style.textContent = `.workspace-panel{padding:24px;margin-top:20px}.workspace-panel section{border-top:1px solid #e5eaf3;padding:24px 0}.workspace-panel h3{margin:0 0 12px}.workspace-panel select,.workspace-panel input[type=text]{padding:9px;border:1px solid #cfd8ed;border-radius:8px;max-width:100%}.workspace-panel label{display:inline-flex;align-items:center;gap:8px;margin:7px 16px 7px 0;font-size:14px}.workspace-panel p{line-height:1.6;color:#566681}.workspace-columns{display:flex;flex-wrap:wrap;max-height:180px;overflow:auto;border:1px solid #dbe2ef;padding:10px;border-radius:10px}.workspace-chart{display:grid;grid-template-columns:minmax(90px,1fr) 2fr 60px;gap:10px;align-items:center;margin:12px 0;font-size:13px}.workspace-chart progress{width:100%;height:20px;accent-color:#3157c3}.workspace-report{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;line-height:1.7;color:#46556f}.workspace-status{min-height:24px}.workspace-panel button{margin:5px}.workspace-panel summary{cursor:pointer;font-weight:700;padding:10px 0}.workspace-preview{max-height:300px;overflow:auto}.workspace-panel :focus-visible{outline:3px solid #4267ce;outline-offset:3px}`;
  document.head.append(style);
  function button(text, action) {
    const b = el("button", text, "secondary"); b.type = "button";
    b.addEventListener("click", action); return b;
  }
  function select(id, choices) {
    const s = el("select"); s.id = id;
    for (const [value, text] of choices) { const o = el("option", text); o.value = value; s.append(o); }
    return s;
  }
  function label(text, input) { const l = el("label", text); l.append(input); return l; }
  function check(id, text) { const input = el("input"); input.type = "checkbox"; input.id = id; return label(text, input); }
  function section(title) { const s = el("section"); s.append(el("h3", title)); root.append(s); return s; }
  function status(text, error = false) { const s = byId("workspaceStatus"); if(s) {s.textContent = text; s.style.color = error ? "#b43535" : "#3157c3";} }
  async function request(path, fields = {}, signal) {
    const body = new FormData(); body.append("file", file);
    for (const [key, value] of Object.entries(fields)) body.append(key, value);
    const response = await fetch(path, {method:"POST", body, cache:"no-store", signal});
    if (!response.ok) {
      let message = "Unable to complete the request. Please retry.";
      try {const data = await response.json(); if(typeof data.detail === "string") message = data.detail;} catch (_) {}
      throw Error(message);
    }
    return response;
  }
  function download(blob, name) {
    const url = URL.createObjectURL(blob), a = el("a"); a.href = url; a.download = name;
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 5000);
  }
  function chart(container, values, total) {
    container.replaceChildren();
    if (!values.length) {container.append(el("p", "No values available for this chart.")); return;}
    for (const value of values) {
      const row = el("div", undefined, "workspace-chart"), bar = el("progress");
      bar.max = Math.max(1, total); bar.value = value.count;
      bar.setAttribute("aria-label", `${value.label}: ${value.count}`);
      row.append(el("span", value.label), bar, el("span", Number(value.count).toLocaleString())); container.append(row);
    }
  }
  function renderCharts() {
    const c = report.charts.find(c => c.column === byId("explorerColumn").value);
    if (!c) return;
    chart(byId("missingChart"), report.charts.map(c => ({label:c.column,count:c.missing})), c.total);
    chart(byId("valueChart"), c.distribution || c.common_values || [], c.total);
    byId("chartCaption").textContent = c.distribution ? "Numeric distribution (finite values only)" : "Eight most common non-missing values";
  }
  async function loadReport() {
    const mine = version;
    status("Building charts, workbook health and your written report…");
    const b = byId("runTemplate"); b.disabled = true; byId("auditTemplate").disabled = true;
    byId('auditDateFormat').disabled=true;for(const input of root.querySelectorAll('[data-audit-field]'))input.disabled=true;
    byId("downloadNarrative").disabled = true;
    try {
      const columns = Object.fromEntries([...root.querySelectorAll('[data-audit-field]')].map(input=>[input.dataset.auditField,input.value]));
      const response = await request("/api/workspace", {sheet, template:byId("auditTemplate").value, mapping:JSON.stringify({columns,date_format:byId('auditDateFormat').value})}, controller.signal);
      const data = await response.json(); if (mine !== version) return;
      report = data; renderCharts();
      const h = data.health, health = byId("healthSummary"); health.replaceChildren();
      health.append(el("p", h.notice));
      if (h.available) {
        health.append(el("p", `${h.sheets.length} sheets · ${h.formulas} formulas · ${h.broken_references} broken references · ${h.saved_errors} saved errors · ${h.external_link_parts} external link parts · VBA ${h.macro_present ? "present" : "not found"}`));
        for (const s of h.sheets) health.append(el("div", `${s.name}: ${s.visibility}`));
        for (const f of h.findings) health.append(el("div", `${f.sheet}!${f.cell} — ${f.finding}`));
        if (h.findings_truncated) health.append(el("p", "Showing first 100 findings; totals include all findings."));
      }
      const checks = byId("templateResults"); checks.replaceChildren();
      const mappingBox=byId('auditMapping');mappingBox.replaceChildren();
      for(const field of data.templates[byId('auditTemplate').value] || []) {
        const match=data.template_checks.find(check=>check.field===field.key);
        const input=select('auditField_'+field.key,[['','Not mapped — do not check'],...data.charts.map(c=>[c.column,c.column])]);
        input.dataset.auditField=field.key;input.value=match?.column||'';
        input.addEventListener('change',invalidateAudit);
        mappingBox.append(label(field.label,input));
      }
      if(data.template_checks.length)checks.append(el('p',`${data.template_checks.filter(c=>c.status!=='not_checked').length} of ${data.template_checks.length} checks applied. Review the column matches before relying on this audit.`));
      for (const check of data.template_checks) checks.append(el("p", `${check.column ? check.column+' — ' : ''}${check.rule}. ${check.status==='passed'?'No issues found':check.status==='review'?'Review needed':'Not checked'}${check.count !== undefined ? ` (${check.count} rows; source row examples: ${check.source_rows.join(", ") || "none"})` : ". " + check.message}`));
      byId("writtenReport").textContent = data.narrative;
      byId("downloadNarrative").disabled = false;
      status("Workspace ready. Cleaning is optional and starts with a preview.");
    } catch (error) { if(mine === version && error.name !== "AbortError") status(error.message, true); }
    finally {if(mine === version) {b.disabled = false; byId("auditTemplate").disabled = false;byId('auditDateFormat').disabled=false;for(const input of root.querySelectorAll('[data-audit-field]'))input.disabled=false;}}
  }
  function invalidateAudit(){byId('templateResults').replaceChildren(el('p','Column mapping changed. Run audit to update the results.'));byId('writtenReport').textContent='Run audit to update the report for these column choices.';byId('downloadNarrative').disabled=true;}
  function options() {
    return {sheet, columns:[...root.querySelectorAll("input[data-column]:checked")].map(n => n.dataset.column), trim:byId("cleanTrim").checked,
      case:byId("cleanCase").value, date_format:byId("cleanDate").value, remove_duplicates:byId("cleanDuplicates").checked};
  }
  function invalidate() {preview = null; byId("confirmClean").checked = false; byId("downloadClean").disabled = true; byId("cleanPreview").replaceChildren();}
  async function previewClean() {
    const mine = version, opts = JSON.stringify(options()), b = byId("previewClean");
    invalidate(); b.disabled = true; status("Preparing your cleaning preview…");
    try {
      const response = await request("/api/clean/preview", {options:opts}, controller.signal);
      const data = await response.json(); if(mine !== version || opts !== JSON.stringify(options())) return;
      preview = {data, options:opts};
      const box = byId("cleanPreview");
      if(data.copy_preview) {
        box.append(el('h4','Preview of the cleaned copy'));
        box.append(el('p','First 20 data rows and 20 columns of the selected worksheet; cell text is capped at 500 characters. Formula results use saved values and are not recalculated. Formatting and macros are not shown.'));
        const sample=el('table'), sampleHead=el('tr');
        sampleHead.append(el('th','Output row'));
        for(const name of data.copy_preview.columns)sampleHead.append(el('th',name));
        const sampleHeader=el('thead');sampleHeader.append(sampleHead);sample.append(sampleHeader);
        const sampleBody=el('tbody');
        data.copy_preview.rows.forEach((values,index)=>{const row=el('tr');row.append(el('td',index+2));for(const value of values)row.append(el('td',value===null?'(blank)':value));sampleBody.append(row);});
        sample.append(sampleBody);const scroll=el('div');scroll.style.overflowX='auto';scroll.append(sample);box.append(scroll);
      }
      box.append(el("p", `${data.rows_before} → ${data.rows_after} rows · ${data.cells_changed} changed cells · ${data.duplicates_removed} duplicates removed · ${data.invalid_dates_unchanged} invalid dates unchanged.`));
      box.append(el("p", data.notice));
      if (data.preview_truncated) box.append(el("p", "Preview shows at most 100 changes and 100 removed row locations; totals include all changes."));
      if (data.removed_source_rows.length) box.append(el("p", "Removed original spreadsheet rows: " + data.removed_source_rows.join(", ")));
      const table = el("table"), head = el("tr");
      for(const text of ["Source row", "Column", "Before", "After"]) head.append(el("th", text));
      const thead = el("thead");thead.append(head);table.append(thead);
      const body = el("tbody");
      for(const change of data.changes) {const row = el("tr");for(const v of [change.row,change.column,change.before,change.after]) row.append(el("td",v));body.append(row);}
      table.append(body);box.append(table);status("Review the preview and export limitations, then confirm to download a separate copy.");
    } catch(error) {if(mine === version && error.name !== "AbortError") status(error.message,true);}
    finally {if(mine === version)b.disabled = false;}
  }
  async function exportClean() {
    if(!preview || !byId("confirmClean").checked) return;
    const mine = version, b = byId("downloadClean"), approved = preview; b.disabled = true;
    try {
      const response = await request("/api/clean/export", {options:approved.options, fingerprint:approved.data.fingerprint, confirmed:"true"}, controller.signal);
      const blob = await response.blob();if(mine !== version) return;
      download(blob, /\.xlsm$/i.test(file.name) ? "cleaned_review_copy.xlsm" : "cleaned_review_copy.xlsx");status("Downloaded a separate cleaned copy. Original file unchanged.");
    } catch(error) {if(mine === version && error.name !== "AbortError")status(error.message,true);}
    finally {if(mine === version)b.disabled = !preview || !byId("confirmClean").checked;}
  }
  function stop() {version++;controller?.abort();report = preview = null;root.classList.add("hidden");}
  function start(newFile, newSheet, columns, demo) {
    stop(); if(demo || !newFile) return;
    file = newFile;sheet = newSheet;controller = new AbortController();root.replaceChildren();root.classList.remove("hidden");
    root.append(el("h2", "What would you like to do?"), el("p", "Open one tool below. Your original file stays unchanged."));
    const worksheetOptions = [...byId('sheetSelect').options].map(option=>[option.value, option.textContent]);
    if(worksheetOptions.length){
      const worksheet = select('workspaceSheet', worksheetOptions);worksheet.value=sheet;
      worksheet.addEventListener('change',()=>{
        byId('sheetSelect').value=worksheet.value;
        byId('sheetSelect').dispatchEvent(new Event('change'));
      });
      root.append(label('Choose worksheet for these tools',worksheet));
    }
    const statusNode = el("p", "", "workspace-status");statusNode.id = "workspaceStatus";statusNode.setAttribute("role","status");statusNode.setAttribute("aria-live","polite");root.append(statusNode);
    const templates = section("1. Choose an audit template");
    templates.append(el("p", "Choose a review type. We suggest familiar column names, then you can match each field to any column in your file. Unclear matches stay unmapped; you never need to rename your spreadsheet. Email screening does not verify delivery."));
    templates.append(label("Template",select("auditTemplate", [["","General review"],["sales","Sales report"],["inventory","Inventory sheet"],["customers","Customer list"]])));
    byId("auditTemplate").addEventListener("change",()=>{byId('auditMapping').replaceChildren();loadReport();});
    const mappingBox=el('div');mappingBox.id='auditMapping';templates.append(mappingBox);
    const dates=select('auditDateFormat',[['%Y-%m-%d','YYYY-MM-DD'],['%m/%d/%Y','MM/DD/YYYY'],['%d/%m/%Y','DD/MM/YYYY']]);dates.addEventListener('change',invalidateAudit);templates.append(label('Dates in this file',dates));
    const run = button("Run audit",loadReport);run.id="runTemplate";templates.append(run);
    const results = el("div");results.id="templateResults";templates.append(results);
    const explorer = section("2. Explore the data");
    const choose = select("explorerColumn",columns.map(c=>[c.column,c.column]));choose.addEventListener("change",()=>report && renderCharts());
    explorer.append(label("Column",choose),el("h4","Missing values by column"));
    for(const [id,tag] of [["missingChart","div"],["chartCaption","h4"],["valueChart","div"]]) {const node=el(tag);node.id=id;explorer.append(node);}
    const health=section("3. Workbook health");const summary=el("div");summary.id="healthSummary";health.append(summary);
    const writer=section("4. Plain-English report");const text=el("div", "", "workspace-report");text.id="writtenReport";writer.append(text);
    const save=button("Download written report",()=>{if(report)download(new Blob([report.narrative],{type:"text/plain;charset=utf-8"}),"data_quality_review.txt");});save.id="downloadNarrative";save.disabled=true;writer.append(save);
    const clean=section("5. Prepare a cleaned copy");
    clean.append(el("p", "Select columns for text/date changes. Dates require an explicit input format; invalid dates stay unchanged. Duplicate removal compares full rows after changes, keeping the first match on the selected sheet."));
    const excel = /\.(xlsx|xlsm)$/i.test(file.name);
    clean.append(el("p", excel ? "Excel downloads preserve formulas, VBA, worksheet visibility and other workbook parts. Only reviewed literal cells change. Row deletion and formula edits are blocked. Changing inputs can affect formula results and macro behavior; review the copy in Excel." : "CSV downloads are separate values-only XLSX copies. Your original CSV stays unchanged."));
    const fields=el("fieldset");fields.append(el("legend","Columns to transform"));const choices=el("div",undefined,"workspace-columns");
    for(const col of columns){const input=el("input");input.type="checkbox";input.dataset.column=col.column;choices.append(label(col.column,input));}fields.append(choices);clean.append(fields);
    clean.append(check("cleanTrim","Trim surrounding spaces"),label("Text case",select("cleanCase",[["keep","Keep case"],["lower","lowercase"],["upper","UPPERCASE"]])),label("Date input format",select("cleanDate",[["","Do not change dates"],["%Y-%m-%d","YYYY-MM-DD"],["%m/%d/%Y","MM/DD/YYYY → ISO"],["%d/%m/%Y","DD/MM/YYYY → ISO"]])),check("cleanDuplicates","Remove full-row duplicates"));
    if(excel) {byId("cleanDuplicates").disabled = true;byId("cleanDuplicates").parentElement.title = "Row removal can break formulas and VBA and is disabled for Excel.";}
    for(const input of clean.querySelectorAll("input,select")) input.addEventListener("change",invalidate);
    const p=button("Preview cleaned copy",previewClean);p.id="previewClean";clean.append(p);
    const box=el("div",undefined,"workspace-preview");box.id="cleanPreview";box.setAttribute("aria-live","polite");clean.append(box);
    clean.append(check("confirmClean","I reviewed these changes and will verify the separate copy before using it"));
    byId("confirmClean").addEventListener("change",()=>byId("downloadClean").disabled=!preview||!byId("confirmClean").checked);
    const d=button("Download cleaned copy",exportClean);d.id="downloadClean";d.disabled=true;clean.append(d);
    for(const tool of [templates,explorer,health,writer,clean]) {
      const details = el("details"), heading = tool.querySelector("h3");
      const summary = el("summary",heading.textContent.replace(/^\d+\. /,""));
      heading.remove();tool.replaceWith(details);details.append(summary,tool);
    }
    loadReport();
  }
  return {start, stop};
})();
