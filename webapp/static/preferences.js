"use strict";
(() => {
  const style = document.createElement("style");
  style.textContent = `:root{color-scheme:light}:root[data-theme=dark]{color-scheme:dark;background:#111827;color:#e5e7eb}html[data-theme=dark] body{background:#111827;color:#e5e7eb}html[data-theme=dark] header,html[data-theme=dark] .panel,html[data-theme=dark] .secondary,html[data-theme=dark] select,html[data-theme=dark] input,html[data-theme=dark] .sheet-row,html[data-theme=dark] .grid-scroll{background:#1f2937;color:#e5e7eb;border-color:#475569}html[data-theme=dark] .drop,html[data-theme=dark] th,html[data-theme=dark] .sheet-header-cell,html[data-theme=dark] .sheet-number{background:#273449;color:#f3f4f6}html[data-theme=dark] .sheet-cell{color:#e5e7eb}html[data-theme=dark] .sheet-cell[class*=cell-]{color:#17233a}html[data-theme=dark] p,html[data-theme=dark] .muted,html[data-theme=dark] .notice,html[data-theme=dark] td,html[data-theme=dark] .workspace-report,html[data-theme=dark] .bar-label span:first-child,html[data-theme=dark] .metric-label,html[data-theme=dark] .metric-note,html[data-theme=dark] .file-sub,html[data-theme=dark] .rec-panel li{color:#cbd5e1}html[data-theme=dark] .sheet-row:nth-child(even){background:#243247}.top{height:auto;min-height:75px;flex-wrap:wrap;gap:12px;padding-top:12px;padding-bottom:12px}.theme-button{padding:8px 12px;border:1px solid #94a3b8;border-radius:8px;background:transparent;color:inherit}.workspace-panel details{border-top:1px solid #94a3b8;padding:10px 0}.workspace-panel details section{border-top:0;padding-top:10px}.privacy-note{padding:12px;margin:16px 0;border:1px solid #94a3b8;border-radius:10px;font-size:13px}a:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid #60a5fa;outline-offset:3px}`;
  document.head.append(style);
  style.textContent += 'html[data-theme=dark] #status,html[data-theme=dark] #workspaceStatus{color:#93c5fd!important}html[data-theme=dark] #status.error{color:#fca5a5!important}';
  style.textContent += '.theme-button{position:fixed;right:18px;bottom:18px;z-index:1000;min-height:44px;background:#fff;color:#17233a;border:2px solid #3157c3;box-shadow:0 4px 18px #0003;font-weight:700}html[data-theme=dark] .theme-button{background:#1f2937;color:#f3f4f6;border-color:#93c5fd}footer{padding-bottom:90px}';
  style.textContent += 'html[data-theme=dark] #sheetSelect,html[data-theme=dark] #workspaceSheet,html[data-theme=dark] #largeFiles select,html[data-theme=dark] select option{background:#273449;color:#f8fafc;border-color:#94a3b8}#workspaceSheet,#largeFiles select{padding:10px;border:1px solid #94a3b8;border-radius:8px;min-height:44px;max-width:100%}html[data-theme=dark] .sheet-pill{background:#273449;color:#e2e8f0;border:1px solid #64748b}html[data-theme=dark] .sheet-pill.active{background:#1e40af;color:#fff;border:2px solid #93c5fd}html[data-theme=dark] .workbook-notice{background:#1f2937;color:#e5e7eb}html[data-theme=dark] .workbook-notice p{color:#cbd5e1}';
  const button = document.createElement("button");button.className="theme-button";
  button.type="button";button.setAttribute("aria-label","Switch between light and dark theme");
  let dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  function render(){document.documentElement.dataset.theme=dark?"dark":"light";button.textContent=dark?"☀ Switch to light":"☾ Switch to dark";button.setAttribute("aria-pressed",String(dark));}
  button.addEventListener("click",()=>{dark=!dark;render();});document.querySelector(".top").append(button);render();
  const footer=document.querySelector("footer .shell");
  for(const [path,title] of [["privacy","Privacy"],["cookies","Cookies"],["terms","Usage terms"]]){const a=document.createElement("a");a.href="/"+path;a.textContent=title;footer.append(document.createTextNode(" · "),a);}
  const note=document.createElement("div");note.className="privacy-note";
  note.textContent="No advertising or analytics cookies. Read our privacy notice before uploading a file. Your theme choice lasts until you reload this page.";
  document.querySelector("main").prepend(note);
  // Keep the first review screen short; detailed grids remain available on demand.
  for(const selector of ["#gridPanel",".table-panel"]){const panel=document.querySelector(selector);if(!panel)continue;const details=document.createElement("details"),summary=document.createElement("summary");summary.textContent=selector==="#gridPanel"?"View spreadsheet and highlighted cells":"View column details";details.className="panel";details.style.padding="16px";panel.replaceWith(details);details.append(summary,panel);if(selector==="#gridPanel")details.addEventListener("toggle",()=>{if(details.open)panel.querySelector('.grid-scroll').dispatchEvent(new Event('scroll'));});}
  document.getElementById('downloadXlsx').textContent='↓ Separate audit report (no formulas/VBA)';
  const reports=document.createElement('details'),reportTitle=document.createElement('summary');reportTitle.textContent='Download reports';reports.append(reportTitle);
  const exportHelp=document.createElement('p');exportHelp.textContent='Reports are separate analysis documents. Use Original file for the unchanged workbook, or Prepare a cleaned copy for reviewed Excel edits.';reports.append(exportHelp);
  document.querySelector('.downloads').append(reports);
  for(const id of ['downloadJson','downloadHtml','downloadXlsx'])reports.append(document.getElementById(id));
  const large=document.createElement('details');large.className='panel';large.style.padding='18px';
  large.id='largeFiles';
  const title=document.createElement('summary');title.textContent='Large files · up to 1 GB · on this computer';large.append(title);
  const help=document.createElement('p');help.textContent='Inspect and clean CSV, XLSX and XLSM files on this computer. Start with a complete-file overview, then preview selected changes and download a separate copy. CSV supports duplicate removal; Excel preserves formulas and VBA and skips formula edits. Browse every stored row and switch worksheets below. Charts and audit templates remain available for smaller files.';large.append(help);
  const input=document.createElement('input');input.type='file';input.accept='.csv,.xlsx,.xlsm';input.setAttribute('aria-label','Choose large file');large.append(input);
  const selectedName=document.createElement('p');large.append(selectedName);
  const start=document.createElement('button');start.textContent='Inspect large file';start.className='secondary';large.append(start);
  const cancel=document.createElement('button');cancel.textContent='Cancel and delete temporary file';cancel.disabled=true;cancel.className='secondary';large.append(cancel);
  const save=document.createElement('button');save.textContent='Download overview';save.disabled=true;save.className='secondary';large.append(save);
  const status=document.createElement('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');large.append(status);
  const sheetLabel=document.createElement('label');sheetLabel.textContent='Choose worksheet ';sheetLabel.hidden=true;
  const sheets=document.createElement('select');sheets.setAttribute('aria-label','Choose worksheet in large file');sheetLabel.append(sheets);large.append(sheetLabel);
  const sheetPreview=document.createElement('section');large.append(sheetPreview);
  const result=document.createElement('pre');result.style.whiteSpace='pre-wrap';large.append(result);document.querySelector('main').append(large);
  let activeJob, reviewJob, browseJob, selectedFile, cancelled=false, overview;
  let gridOffset=0, gridColumn=0, gridGeneration=0;
  const cleaning=document.createElement('details');cleaning.hidden=true;large.append(cleaning);
  const cleanTitle=document.createElement('summary');cleanTitle.textContent='Prepare a cleaned large-file copy';cleaning.append(cleanTitle);
  const cleanHelp=document.createElement('p');cleaning.append(cleanHelp);
  const fields=document.createElement('fieldset'),legend=document.createElement('legend');legend.textContent='Columns to clean';fields.append(legend);cleaning.append(fields);
  const excelColumns=document.createElement('input');excelColumns.type='text';excelColumns.maxLength=1000;excelColumns.setAttribute('aria-label','Excel column letters to clean');cleaning.append(excelColumns);
  function cleanCheck(text){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';label.append(input,document.createTextNode(' '+text+' '));cleaning.append(label);return input;}
  const trim=cleanCheck('Trim surrounding spaces');
  function cleanSelect(text,choices){const label=document.createElement('label');label.textContent=text+' ';const select=document.createElement('select');for(const [value,title] of choices){const option=document.createElement('option');option.value=value;option.textContent=title;select.append(option);}label.append(select);cleaning.append(label);return select;}
  const casing=cleanSelect('Text case',[['keep','Keep case'],['lower','lowercase'],['upper','UPPERCASE']]);
  const date=cleanSelect('Date input format',[['','Do not change dates'],['%Y-%m-%d','YYYY-MM-DD'],['%m/%d/%Y','MM/DD/YYYY'],['%d/%m/%Y','DD/MM/YYYY']]);
  const duplicates=cleanCheck('Remove duplicate full rows (CSV only)');
  const previewButton=document.createElement('button');previewButton.textContent='Preview full-file cleaning';previewButton.className='secondary';cleaning.append(previewButton);
  const previewText=document.createElement('pre');previewText.style.whiteSpace='pre-wrap';cleaning.append(previewText);
  const cleanedSheetPreview=document.createElement('section');cleaning.append(cleanedSheetPreview);
  const confirm=cleanCheck('I reviewed this preview and accept the separate cleaned copy');
  const exportButton=document.createElement('button');exportButton.textContent='Download approved cleaned copy';exportButton.className='secondary';exportButton.disabled=true;cleaning.append(exportButton);
  confirm.addEventListener('change',()=>{exportButton.disabled=!confirm.checked||!reviewJob||!overview?.cleaning;});
  function invalidateClean(){cleanedSheetPreview.replaceChildren();if(overview)delete overview.cleaning;confirm.checked=false;exportButton.disabled=true;previewText.textContent='Options changed. Prepare a fresh preview before downloading.';}
  for(const control of [fields,excelColumns,trim,casing,date,duplicates,sheets])control.addEventListener('change',invalidateClean);
  previewButton.addEventListener('click',()=>{const excel=overview?.kind==='Excel';const columns=excel?excelColumns.value.split(',').map(value=>value.trim().toUpperCase()).filter(Boolean):[...fields.querySelectorAll('input:checked')].map(input=>input.value);inspectLarge(selectedFile,{sheet:excel?sheets.value:'',columns,trim:trim.checked,case:casing.value,date_format:date.value,remove_duplicates:duplicates.checked});});
  exportButton.addEventListener('click',()=>{
    if(!confirm.checked||!reviewJob||!overview?.cleaning)return;
    const form=document.createElement('form');form.method='POST';form.action='/api/large/uploads/'+reviewJob.id+'/download';form.hidden=true;
    for(const [name,value] of Object.entries({token:reviewJob.token,fingerprint:overview.cleaning.fingerprint,confirmed:'true'})){const input=document.createElement('input');input.name=name;input.value=value;form.append(input);}
    document.body.append(form);form.submit();form.remove();exportButton.disabled=true;confirm.checked=false;status.textContent='Download requested. Check browser downloads. The temporary copy is deleted when the transfer finishes.';
  });
  style.textContent += '.large-preview-scroll{overflow:auto;max-height:420px;border:1px solid #94a3b8;border-radius:8px;margin:12px 0}.large-preview-scroll table{border-collapse:collapse;width:max-content;min-width:100%}.large-preview-scroll caption{text-align:left;padding:12px;font-weight:700}.large-preview-scroll th,.large-preview-scroll td{border:1px solid #94a3b8;padding:8px;max-width:240px;min-width:100px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.large-preview-scroll th{position:sticky;top:0;background:#edf2fc}.large-preview-scroll .large-changed{background:#dcfce7;color:#14532d!important}html[data-theme=dark]{--missing-preview:#7f1d1d}html[data-theme=dark] .large-preview-scroll .large-changed{background:#14532d;color:#f0fdf4!important}';
  function renderSheet(container, preview, title){
    container.replaceChildren();
    if(!preview)return;
    const scroll=document.createElement('div');scroll.className='large-preview-scroll';
    const table=document.createElement('table'),caption=document.createElement('caption');caption.textContent=title;table.append(caption);
    const head=document.createElement('thead'),heading=document.createElement('tr');
    for(const name of ['Sheet row',...preview.columns]){const cell=document.createElement('th');cell.scope='col';cell.textContent=name;heading.append(cell);}head.append(heading);table.append(head);
    const body=document.createElement('tbody');
    for(const row of preview.rows){
      const tr=document.createElement('tr'),number=document.createElement('th');number.scope='row';number.textContent=row.row_number;tr.append(number);
      preview.columns.forEach((column,index)=>{const cell=document.createElement('td'),value=row.values[index]??'';cell.textContent=value===''?'(blank)':value;if(value==='')cell.style.backgroundColor='var(--missing-preview,#fff1f2)';
        cell.title=column+row.row_number;
        tr.append(cell);
      });body.append(tr);
    }
    table.append(body);scroll.append(table);container.append(scroll);
    const note=document.createElement('p');note.className='muted';note.textContent='First 20 rows and 20 columns only; each cell is limited to 500 characters. Scroll sideways for more columns. Excel formulas are shown as text and are not recalculated. Counts cover the complete file.';container.append(note);
  }
  function renderOverview(){
    if(!overview)return;
    renderSheet(sheetPreview, overview.kind==='CSV'?overview.preview:overview.sheets.find(sheet=>sheet.name===sheets.value)?.preview, 'Spreadsheet preview');
    if(overview.kind==='CSV'){
      result.textContent='Data rows: '+overview.rows.toLocaleString()+'\nColumns: '+overview.columns+'\n\nBlank values\n'+Object.entries(overview.missing).map(([name,count])=>name+': '+count.toLocaleString()).join('\n')+'\n\n'+overview.notice;
    }else{
      const selected=overview.sheets.filter(sheet=>sheets.value===''||sheet.name===sheets.value);
      result.textContent=selected.map(sheet=>sheet.name+' ('+sheet.state+')\n'+sheet.stored_rows.toLocaleString()+' stored rows · '+sheet.stored_cells.toLocaleString()+' stored cells\n'+sheet.formulas.toLocaleString()+' formulas · '+sheet.cached_errors.toLocaleString()+' cached errors').join('\n\n')+'\n\nVBA present: '+(overview.vba_present?'Yes':'No')+'\n'+overview.notice;
    }
  }
  const gridControls=document.createElement('div');sheetPreview.before(gridControls);
  function gridButton(label, action){const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=label;button.addEventListener('click',action);gridControls.append(button);return button;}
  const previousRows=gridButton('Previous rows',()=>{gridOffset=Math.max(0,gridOffset-50);loadGrid();});
  const nextRows=gridButton('Next rows',()=>{gridOffset+=50;loadGrid();});
  const jumpLabel=document.createElement('label');jumpLabel.textContent=' Go to row ';const jump=document.createElement('input');jump.type='number';jump.min='1';jump.value='1';jump.style.width='110px';jump.setAttribute('aria-label','Go to spreadsheet row');jumpLabel.append(jump);gridControls.append(jumpLabel);
  gridButton('Go',()=>{const value=Number(jump.value);if(Number.isSafeInteger(value)&&value>0){gridOffset=value-1;loadGrid();}});
  const previousColumns=gridButton('Previous columns',()=>{gridColumn=Math.max(0,gridColumn-20);loadGrid();});
  const nextColumns=gridButton('Next columns',()=>{gridColumn+=20;loadGrid();});
  const gridStatus=document.createElement('p');gridStatus.setAttribute('role','status');gridControls.append(gridStatus);gridControls.hidden=true;
  function excelLetter(index){let value='';for(index++;index;index=Math.floor((index-1)/26))value=String.fromCharCode(65+(index-1)%26)+value;return value;}
  async function loadGrid(){
    const job=reviewJob||browseJob;if(!job||!overview)return;
    const generation=++gridGeneration;
    const controls=[...gridControls.querySelectorAll('button')];controls.forEach(button=>button.disabled=true);gridStatus.textContent='Loading spreadsheet rows…';
    try{
      const path='/api/large/uploads/'+job.id+'/rows?'+new URLSearchParams({sheet:sheets.value,offset:gridOffset,column:gridColumn});
      const data=await api(path,{headers:{'X-Upload-Token':job.token}});if(generation!==gridGeneration)return;
      const columns=Array.from({length:Math.max(0,Math.min(20,data.columns_total-gridColumn))},(_,i)=>excelLetter(gridColumn+i));
      renderSheet(sheetPreview,{columns,rows:data.rows},'Spreadsheet — '+(overview.kind==='CSV'?selectedFile.name:sheets.value));
      sheetPreview.querySelector('.muted').textContent='Browse every stored row and column using the controls above. Each request loads up to 50 rows and 20 columns. Cells are limited to 500 characters; Excel formulas are displayed as text.';
      if(reviewJob&&overview.cleaning){const cleaned=await api(path+'&cleaned=true',{headers:{'X-Upload-Token':job.token}});if(generation!==gridGeneration)return;renderSheet(cleanedSheetPreview,{columns,rows:cleaned.rows},'Cleaned copy — same worksheet and position');cleanedSheetPreview.querySelector('.muted').textContent='A read-only view of the cleaned output at this position. Up to 50 rows and 20 columns per request; cells are limited to 500 characters. Your original stays unchanged.';}
      gridStatus.textContent=data.rows.length?'Showing rows '+(gridOffset+1).toLocaleString()+'–'+(gridOffset+data.rows.length).toLocaleString()+' of '+data.total.toLocaleString()+' · columns '+(gridColumn+1)+'–'+Math.min(gridColumn+20,data.columns_total):'No rows at this position. Choose a lower row number.';
      jump.max=String(data.total);controls.forEach(button=>button.disabled=false);previousRows.disabled=gridOffset===0;nextRows.disabled=gridOffset+data.rows.length>=data.total;previousColumns.disabled=gridColumn===0;nextColumns.disabled=gridColumn+20>=data.columns_total;
    }catch(error){if(generation===gridGeneration){gridStatus.textContent=error.message;controls.forEach(button=>button.disabled=false);}}
  }
  sheets.addEventListener('change',()=>{renderOverview();gridOffset=gridColumn=0;loadGrid();});
  async function api(path,options={}){const response=await fetch(path,{...options,cache:'no-store'});const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Large-file request failed.');return data;}
  cancel.addEventListener('click',async()=>{cancelled=true;cancel.disabled=true;status.textContent='Cancelling and deleting temporary data…';const job=activeJob||reviewJob||browseJob;if(job)try{await api('/api/large/uploads/'+job.id,{method:'DELETE',headers:{'X-Upload-Token':job.token}});if(!activeJob){reviewJob=browseJob=null;gridControls.hidden=true;sheetPreview.replaceChildren();cleanedSheetPreview.replaceChildren();confirm.checked=false;exportButton.disabled=true;previewText.textContent='Preview discarded. Temporary copy deleted.';status.textContent='Temporary copy deleted.';}}catch(error){status.textContent=error.message;cancel.disabled=false;}});
  save.addEventListener('click',()=>{if(!overview)return;const url=URL.createObjectURL(new Blob([JSON.stringify(overview,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='large-file-overview.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  async function inspectLarge(file, clean=null){
    if(start.disabled)return;
    large.open=true;
    if(!file){status.textContent='Choose a CSV, XLSX or XLSM first.';return;}
    if(file.size>1024**3){status.textContent='This file exceeds the local limit of 1,073,741,824 bytes (about 1 GB).';return;}
    if(!/\.(csv|xlsx|xlsm)$/i.test(file.name)){status.textContent='Choose a CSV, XLSX or XLSM file.';return;}
    large.open=true;large.scrollIntoView({behavior:'smooth',block:'start'});
    selectedFile=file;selectedName.textContent='Selected file: '+file.name;gridGeneration++;gridControls.hidden=true;
    start.disabled=input.disabled=previewButton.disabled=true;cancel.disabled=false;save.disabled=true;cancelled=false;overview=null;result.textContent='';sheetPreview.replaceChildren();cleanedSheetPreview.replaceChildren();sheetLabel.hidden=true;confirm.checked=false;exportButton.disabled=true;let job;
    for(const control of cleaning.querySelectorAll('input,select,button'))control.disabled=true;
    try{
      if(reviewJob||browseJob){const previous=reviewJob||browseJob;await api('/api/large/uploads/'+previous.id,{method:'DELETE',headers:{'X-Upload-Token':previous.token}});reviewJob=browseJob=null;}
      job=await api('/api/large/uploads',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:file.name,size:file.size,clean})});
      activeJob=job;
      const path='/api/large/uploads/'+job.id;
      for(let offset=0;offset<file.size;offset+=job.chunk_bytes){
        if(cancelled)throw Error('Cancelled. Temporary file deleted.');
        const chunk=file.slice(offset,offset+job.chunk_bytes);
        await api(path,{method:'PUT',headers:{'X-Upload-Token':job.token,'X-Upload-Offset':String(offset)},body:chunk});
        status.textContent='Uploaded '+Math.round(Math.min(offset+chunk.size,file.size)/file.size*100)+'%';
      }
      if(cancelled)throw Error('Cancelled. Temporary file deleted.');
      status.textContent='Processing on local temporary storage…';
      await api(path+'/complete',{method:'POST',headers:{'X-Upload-Token':job.token}});
      let state;
      do{await new Promise(resolve=>setTimeout(resolve,1000));state=await api(path,{headers:{'X-Upload-Token':job.token}});}while(['queued','processing'].includes(state.status));
      if(!['complete','review'].includes(state.status))throw Error(state.result?.error||'Large-file analysis failed.');
      overview=state.result;save.disabled=false;
      if(overview.kind==='Excel'){
        sheets.replaceChildren();
        for(const sheet of overview.sheets){const option=document.createElement('option');option.value=sheet.name;option.textContent=sheet.name+(sheet.state==='visible'?'':' ('+sheet.state+')');sheets.append(option);}
        if(clean)sheets.value=clean.sheet;
        sheetLabel.hidden=false;
      }
      renderOverview();
      cleaning.hidden=false;
      const excel=overview.kind==='Excel';excelColumns.hidden=!excel;fields.hidden=excel;duplicates.disabled=excel;if(excel)duplicates.checked=false;
      cleanHelp.textContent=excel?'Enter column letters separated by commas, such as A, C. Row 1 is treated as headings. Formula cells are skipped. Only reviewed literal text changes; original workbook parts and VBA are preserved. Excel row removal is blocked.':'Choose columns for text/date changes. Duplicate detection compares complete rows after changes using temporary disk storage. Download is CSV; spreadsheet programs can interpret formula-like CSV text.';
      if(!clean){fields.replaceChildren(legend);for(const name of Object.keys(overview.missing||{})){const label=document.createElement('label'),box=document.createElement('input');box.type='checkbox';box.value=name;label.append(box,document.createTextNode(' '+name+' '));fields.append(label);}previewText.textContent='';}
      if(overview.cleaning){reviewJob=job;const p=overview.cleaning;renderSheet(cleanedSheetPreview,p.copy_preview,'Cleaned copy preview');previewText.textContent=p.cells_changed+' changed cells · '+p.duplicates_removed+' duplicate rows removed\n'+p.invalid_dates_unchanged+' invalid dates left unchanged\n\n'+p.changes.map(change=>'Row '+change.row+' / '+change.column+': '+JSON.stringify(change.before)+' → '+JSON.stringify(change.after)).join('\n')+'\n\nFirst 100 changes shown; counts cover the entire file.\n'+p.notice;cleaning.open=true;status.textContent='Review the cleaning preview. The temporary output waits for your confirmation; original source is unchanged.';}
      else{browseJob=job;status.textContent='Spreadsheet ready to browse. Original unchanged. Temporary browsing data stays on this computer until you delete it, quit the app, or leave it unused for an hour.';}
      gridOffset=gridColumn=0;gridControls.hidden=false;await loadGrid();
    }catch(error){status.textContent=cancelled?'Cancelled. Temporary data is being cleared.':error.message;if(job)try{await api('/api/large/uploads/'+job.id,{method:'DELETE',headers:{'X-Upload-Token':job.token}});}catch(_){} }
    finally{start.disabled=input.disabled=previewButton.disabled=false;for(const control of cleaning.querySelectorAll('input,select,button'))control.disabled=false;duplicates.disabled=overview?.kind==='Excel';exportButton.disabled=!confirm.checked||!reviewJob||!overview?.cleaning;cancel.disabled=!(reviewJob||browseJob);activeJob=null;}
  }
  start.addEventListener('click',()=>inspectLarge(input.files[0]||selectedFile));
  window.DQDLargeFiles={inspect:inspectLarge};
  fetch('/api/config').then(response=>response.json()).then(config=>{if(!config.large_upload_bytes)large.hidden=true;}).catch(()=>{large.hidden=true;});
})();
