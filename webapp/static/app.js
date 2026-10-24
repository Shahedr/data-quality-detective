
"use strict";
const $=id=>document.getElementById(id);
let lastReport=null;
let currentFile=null;
let running=false;
let demoMode=false;
const SAMPLE_CSV=[
"order_id,order_date,customer_id,region,quantity,unit_price,freight_cost,status",
"1,2025-01-03,C001,Midwest,1,39.99,12.50,Shipped",
"2,2025-01-04,C002,South,2,24.50,Included,Delivered",
"3,2025-01-05,C003,West,1,19.00,8.75,Delivered",
"4,not-a-date,C004,Midwest,3,15.00,10.00,Delivered",
"5,2025-01-08,,Northeast,1,999.00,45.00,Returned",
"6,2025-01-09,C006,South,1,22.00,,Delivered",
"7,2025-01-10,C007,West,2,18.00,9.25,Delivered",
"8,2025-01-11,C008,Midwest,1,20.00,10.50,Delivered",
"9,2025-01-12,C009,South,1,21.00,11.00,Delivered",
"10,2025-01-13,C010,West,50,20.00,1500.00,Delivered",
"11,2025-01-14,C011,Midwest,1,20.50,10.00,Delivered",
"11,2025-01-14,C011,Midwest,1,20.50,10.00,Delivered"].join("\n");
function setStatus(message,isError=false){$("status").textContent=message;$("status").className=isError?"error":"";}
function item(tag,text,className){const el=document.createElement(tag);el.textContent=String(text);if(className)el.className=className;return el;}
function showReport(data){
  lastReport=data;
  const switcher=$("workbookSwitch"),select=$("sheetSelect"),overview=$("sheetOverview");
  overview.replaceChildren();
  select.replaceChildren();
  const tabs=data.worksheets||[];
  if(tabs.length){
    switcher.classList.remove("hidden");
    $("workbookTotals").textContent=tabs.length+" worksheets · "+data.workbook_total_rows.toLocaleString()+" data rows total";
    for(const sheet of tabs){
      const opt=document.createElement("option");
      opt.value=sheet.name;opt.textContent=sheet.name+(sheet.visibility!=="visible"?" (hidden)":"");
      select.append(opt);
      const badge=item("span",sheet.name+" · "+sheet.rows.toLocaleString()+" rows"+
        " · "+sheet.formula_cells+" formulas"+
        " · "+sheet.invalid_dropdown_cells+" dropdown errors",
        "sheet-pill"+(sheet.name===data.selected_sheet?" active":""));
      overview.append(badge);
    }
    select.value=data.selected_sheet;
  }else{switcher.classList.add("hidden");}
  const note=$("workbookNotice");
  note.replaceChildren();
  if(data.workbook){
    const w=data.workbook;
    note.classList.remove("hidden");
    note.append(item("h3","Excel worksheet audit"));
    note.append(item("p","Worksheet: "+w.worksheet_analyzed+
      " · visibility: "+w.worksheet_visibility+
      " · Excel tables: "+w.excel_tables+
      " · formulas: "+w.formula_cells_count+
      " · broken formula references: "+w.broken_formula_refs+
      " · dropdown rules: "+w.dropdown_rules+
      " · invalid dropdown values: "+w.dropdown_invalid_cells));
    for(const rule of w.dropdown_rules_detail||[]){
      const choices=rule.allowed_values.length
        ? " · choices: "+rule.allowed_values.slice(0,12).join(", ")+(rule.allowed_values_truncated?" …":"")
        : "";
      note.append(item("p","List "+rule.ranges+" — "+rule.source+choices));
    }
    for(const warning of w.warnings)note.append(item("p",warning));
  }else{note.classList.add("hidden");}
  const macro=$("macroNotice");
  macro.replaceChildren();
  if(data.vba_audit&&data.vba_audit.vba_project_present){
    const audit=data.vba_audit;
    macro.classList.remove("hidden");
    macro.append(item("h3","VBA static audit — no execution"));
    macro.append(item("p","Source scan: "+audit.source_scan_status+
      " · modules: "+audit.modules.length+
      " · auto-run patterns: "+audit.finding_counts.autoexec+
      " · scanner suspicious-pattern hits: "+audit.finding_counts.suspicious+
      " · code-keyword matches: "+(audit.finding_counts.code_matches||0)+
      " · comment/text-only or unverified: "+(audit.finding_counts.context_only||0)+
      " · heuristic-only: "+(audit.finding_counts.heuristic||0)+
      " · indicators of compromise: "+audit.finding_counts.ioc));
    macro.append(item("p",audit.limitations));
    for(const module of audit.modules.slice(0,25))
      macro.append(item("div","Module: "+module.name+" · "+module.source_lines+" lines","audit-finding"));
    for(const finding of audit.findings.slice(0,25))
      macro.append(item("div",finding.category+": "+finding.keyword+" — "+finding.explanation+" · Evidence: "+(finding.evidence||"scanner heuristic"),"audit-finding"));
  }else{macro.classList.add("hidden");}
  if(data.spreadsheet)window.DQDSpreadsheet.start(
    currentFile,data.spreadsheet,data.columns,data.selected_sheet||"",demoMode
  );
  const s=data.summary;
  $("source").textContent="Source: "+s.source;
  for(const [id,key] of [["rows","rows"],["cols","columns"],["dupes","duplicate_rows"],["missing","columns_with_missing"]]){$(id).textContent=Number(s[key]).toLocaleString();}
  const metrics=[["Duplicate rows","duplicate_rows"],["Columns with missing data","columns_with_missing"],["Constant columns","constant_columns"],["Mixed numeric/text columns","mixed_numeric_text_columns"],["Invalid-date columns","date_columns_with_invalid_values"],["Columns with outliers","numeric_columns_with_outliers"]];
  const max=Math.max(1,...metrics.map(v=>Number(s[v[1]])||0));
  $("issues").replaceChildren();
  for(const [label,key] of metrics){
    const container=item("div","","bar-row");const heading=item("div","","bar-label");
    heading.append(item("span",label),item("span",s[key]));
    const track=item("div","","track");const fill=item("div","","fill");fill.style.width=((Number(s[key])||0)/max*100)+"%";
    track.append(fill);container.append(heading,track);$("issues").append(container);
  }
  $("recommendations").replaceChildren();
  for(const recommendation of data.recommendations){$("recommendations").append(item("li",recommendation));}
  $("columns").replaceChildren();
  for(const column of data.columns){
    const tr=document.createElement("tr");
    for(const val of [column.column,column.dtype,column.missing_count+" ("+column.missing_pct+"%)",column.unique_count,column.outlier_count]){
      tr.append(item("td",val));
    }
    const flags=document.createElement("td");
    for(const flag of (column.issues.length?column.issues:["No issues"])){flags.append(item("span",flag,flag==="No issues"?"flag ok":"flag"));}
    tr.append(flags);$("columns").append(tr);
  }
  $("results").classList.remove("hidden");
  window.DQDWorkspace.start(currentFile, data.selected_sheet || "", data.columns, demoMode);
}

async function initializeMode(){
  try{
    const response=await fetch("/api/config",{cache:"no-store"});
    if(!response.ok)return;
    const mode=await response.json();
    demoMode=!!mode.public_demo;
    if(!demoMode){
      const hosted=mode.mode==="free_web";
      $("modeTag").textContent=hosted?"FREE WEB TOOL":"FREE LOCAL WORKSPACE";
      document.querySelector("#drop .muted").textContent=hosted
        ?"CSV, XLSX or XLSM · max 4 MB per file · 100,000 data rows · 40 sheets"
        :"CSV, XLSX or XLSM · up to 1 GB locally · detailed reports up to 10 MB";
      $("dataNotice").textContent=hosted
        ?"Free, with no account required. Online analysis uploads your file for processing. For confidential or sensitive files, use the local app on your own computer. See the privacy notice for storage and retention details."
        :"Your files stay on this computer. Choose or drop a file up to 1 GB here. Files over 10 MB automatically open the large-file overview and cleaning tools; smaller files get the detailed report, charts and grid.";
      return;
    }
    document.getElementById("modeTag").textContent="PUBLIC SAMPLE DEMO";
    document.querySelector(".lead").textContent=
      "Explore the Data Quality Detective dashboard with bundled sample data. No personal file uploads are allowed in this public preview.";
    $("choose").classList.add("hidden");
    $("sample").textContent="Explore interactive demo";
    $("fileTitle").textContent="Try a sample data audit";
    document.querySelector("#drop .muted").textContent=
      "Fictional data only · no uploads · no macro execution";
    $("dataNotice").textContent=
      "This public preview processes only the supplied sample. To check your own Excel or CSV files, use the local desktop application.";
    setStatus("Demo ready. Select “Explore interactive demo” to begin.");
  }catch(_){
    setStatus("Unable to load demo configuration. Try refreshing.",true);
  }
}
async function analyzeDemo(){
  if(running)return;
  running=true;$("sample").disabled=true;
  setStatus("Analyzing example data…");
  $("results").classList.add("hidden");
  window.DQDSpreadsheet.stop();
  window.DQDWorkspace.stop();
  try{
    const response=await fetch("/api/demo/analyze",{cache:"no-store"});
    const data=await response.json();
    if(!response.ok)throw Error(data.detail||"Example analysis unavailable.");
    currentFile=new File([SAMPLE_CSV],"sample.csv",{type:"text/csv"});
    showReport(data);
    setStatus("Demo loaded. Explore the issues and download example reports.");
  }catch(error){
    setStatus("Demo failed: "+(error.message||"Unknown error"),true);
  }finally{running=false;$("sample").disabled=false;}
}
async function analyzeFile(file,sheet=""){
  if(demoMode){setStatus("Public demo uploads are disabled. Please use the example.",true);return;}
  if(running)return;
  if(!file)return;
  const maxBytes=document.getElementById("modeTag").textContent==="FREE WEB TOOL"?4*1024*1024:10*1024*1024;
  if(file.size>maxBytes){
    if(maxBytes===10*1024*1024&&window.DQDLargeFiles){
      setStatus("Opening large-file inspection. Charts, templates and the detailed grid are available for files up to 10 MB.");
      return window.DQDLargeFiles.inspect(file);
    }
    setStatus("Public upload limit: 4 MB. Use the local app for files up to 1 GB.",true);return;
  }
  running=true;$("choose").disabled=true;$("sample").disabled=true;
  setStatus("Analyzing "+file.name+" …");
  $("fileTitle").textContent=file.name;
  $("results").classList.add("hidden");
  window.DQDSpreadsheet.stop();
  window.DQDWorkspace.stop();
  const body=new FormData();body.append("file",file);body.append("sheet",sheet);
  try{
    const response=await fetch("/api/analyze",{method:"POST",body,cache:"no-store"});
    const payload=await response.json();
    if(!response.ok)throw new Error(typeof payload.detail==="string"?payload.detail:"Analysis failed.");
    currentFile=file;showReport(payload);setStatus("Analysis complete. Review the highlighted spreadsheet rows below.");
  }catch(error){setStatus(error.message||"Unable to analyze file.",true);}
  finally{running=false;$("choose").disabled=false;$("sample").disabled=false;}
}
$("sheetSelect").addEventListener("change",()=>{if(currentFile)analyzeFile(currentFile,$("sheetSelect").value);});
$("choose").addEventListener("click",()=> $("upload").click());
$("upload").addEventListener("change",e=>analyzeFile(e.target.files[0]));
$("sample").addEventListener("click",()=>demoMode?analyzeDemo():analyzeFile(new File([SAMPLE_CSV],"messy_orders.csv",{type:"text/csv"})));
$("drop").addEventListener("dragover",e=>{e.preventDefault();$("drop").classList.add("dragover");});
$("drop").addEventListener("dragleave",()=> $("drop").classList.remove("dragover"));
$("drop").addEventListener("drop",e=>{e.preventDefault();$("drop").classList.remove("dragover");if(!demoMode&&e.dataTransfer.files.length)analyzeFile(e.dataTransfer.files[0]);});
function download(content,kind,extension){
  const blob=new Blob([content],{type:kind});
  const url=URL.createObjectURL(blob);const a=document.createElement("a");
  a.href=url;a.download=(lastReport?.summary?.source||"dataset").replace(/\.(csv|xlsx)$/i,"")+"_report."+extension;
  document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$("downloadJson").addEventListener("click",()=>{if(lastReport)download(JSON.stringify(lastReport.report_json,null,2),"application/json","json");});
$("downloadOriginal").addEventListener("click",()=>{if(!currentFile)return;const url=URL.createObjectURL(currentFile);const a=document.createElement("a");a.href=url;a.download=currentFile.name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);});
$("downloadXlsx").addEventListener("click",async()=>{
  if(!lastReport||!currentFile)return;
  const button=$("downloadXlsx");
  button.disabled=true;
  const previous=button.textContent;
  button.textContent="Preparing Excel audit…";
  setStatus("Creating a separate, color-coded Excel review file…");
  try{
    const body=new FormData();body.append("file",currentFile);
    const response=await fetch(demoMode?"/api/demo/export/xlsx":"/api/export/xlsx",demoMode?{method:"GET",cache:"no-store"}:{method:"POST",body,cache:"no-store"});
    if(!response.ok){
      let message="Unable to create Excel review report.";
      try{const e=await response.json();if(e.detail)message=e.detail;}catch(_){}
      throw Error(message);
    }
    const blob=await response.blob();
    const filename=(currentFile.name||"dataset").replace(/\.(csv|xlsx|xlsm)$/i,"")+"_audit_review.xlsx";
    const url=URL.createObjectURL(blob);
    const link=document.createElement("a");link.href=url;link.download=filename;
    document.body.append(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),5000);
    setStatus("Excel audit downloaded. Open the separate review workbook; the original is untouched.");
  }catch(error){setStatus("Excel export failed: "+(error.message||"Unknown error"),true);}
  finally{button.disabled=false;button.textContent=previous;}
});
$("downloadHtml").addEventListener("click",async()=>{
  if(!lastReport||!currentFile)return;
  const button=$("downloadHtml");
  button.disabled=true;
  const previous=button.textContent;
  button.textContent="Preparing complete spreadsheet…";
  setStatus("Creating full HTML export. Very large sheets can take time.");
  try{
    const body=new FormData();body.append("file",currentFile);
    const response=await fetch(demoMode?"/api/demo/export/html":"/api/export/html",demoMode?{method:"GET",cache:"no-store"}:{method:"POST",body,cache:"no-store"});
    if(!response.ok){
      let message="Failed to export spreadsheet.";
      try{const e=await response.json();if(e.detail)message=e.detail;}catch(_){}
      throw Error(message);
    }
    const blob=await response.blob();
    const filename=(currentFile.name||"dataset").replace(/\.(csv|xlsx|xlsm)$/i,"")+"_full_report.html";
    const url=URL.createObjectURL(blob);
    const link=document.createElement("a");link.href=url;link.download=filename;
    document.body.append(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),5000);
    setStatus("Full spreadsheet HTML export downloaded.");
  }catch(error){setStatus("HTML export failed: "+(error.message||"Unknown error"),true);}
  finally{button.disabled=false;button.textContent=previous;}
});
initializeMode();
