"use strict";
(function(){
  const $=id=>document.getElementById(id);
  let cfg=null,client=null,activeFile=null,currentData=null;
  const show=(id,on)=>$(id).classList.toggle("hidden",!on);
  const status=message=>$("status").textContent=message;
  async function authToken(){
    if(!client)throw Error("Private workspace is unavailable.");
    const {data,error}=await client.auth.getSession();
    if(error||!data.session?.access_token)throw Error("Sign in again.");
    return data.session.access_token;
  }
  async function api(path,opts={}){
    const token=await authToken();
    const response=await fetch("/api/saas"+path,{
      ...opts,cache:"no-store",
      headers:{"Authorization":"Bearer "+token,...opts.headers}
    });
    if(!response.ok){
      const type=response.headers.get("content-type")||"";
      const data=type.includes("application/json")?await response.json():{};
      throw Error(data.detail||"Request failed. "+response.status);
    }
    return response;
  }
  async function refresh(){
    const {data}=await client.auth.getSession();
    const logged=!!data?.session;
    show("login",!logged);show("workspace",logged);
    if(!logged){status("Sign in to start.");return;}
    try{
      const detail=await (await api("/account")).json();
      $("accountInfo").textContent=detail.plan.toUpperCase()+" · "+detail.analyses_this_month+" of "+detail.monthly_limit+" monthly analyses used · "+(data.session.user.email||"");
      status("Private workspace ready.");
    }catch(e){status("Account status error: "+e.message);}
  }
  async function auth(action){
    $("signin").disabled=true;$("signup").disabled=true;
    try{
      const email=$("email").value.trim();
      const password=$("password").value;
      if(!email||password.length<12)throw Error("Enter an email and a password of at least 12 characters.");
      const {data,error}=action==="signup"
        ?await client.auth.signUp({email,password})
        :await client.auth.signInWithPassword({email,password});
      if(error)throw error;
      status(action==="signup"&&!data.session?"Check your inbox to confirm your email address.":"Signed in.");
      await refresh();
    }catch(e){status(e.message);}
    finally{$("signin").disabled=false;$("signup").disabled=false;}
  }
  async function analyze(){
    if(!activeFile)return;
    $("analyze").disabled=true;
    status("Analyzing workbook on private server…");
    try{
      const body=new FormData();body.append("file",activeFile);
      const data=await(await api("/analyze",{method:"POST",body})).json();
      currentData=data;
      const s=data.summary;
      $("summary").textContent="Rows: "+s.rows+" · Columns: "+s.columns+" · Duplicate copies: "+s.duplicate_rows+" · Columns with missing values: "+s.columns_with_missing;
      show("summary",true);
      const sheet=data.spreadsheet;
      const headers=document.createDocumentFragment();
      for(const name of ["Data row",...(sheet.columns||[])]){
        const th=document.createElement("th");th.textContent=name;headers.append(th);
      }
      $("preview").querySelector("thead").replaceChildren(headers);
      const rows=document.createDocumentFragment();
      for(const r of (sheet.rows||[])){
        const tr=document.createElement("tr");
        for(const value of [r.row_number,...(r.values||[])]){
          const td=document.createElement("td");td.textContent=value===null?"(blank)":String(value);tr.append(td);
        }
        rows.append(tr);
      }
      $("preview").querySelector("tbody").replaceChildren(rows);
      show("reports",true);
      status("Analysis complete. Displaying the initial preview; downloadable reports include all accepted rows.");
      await refresh();
    }catch(e){status("Analysis failed: "+e.message);}
    finally{$("analyze").disabled=!activeFile;}
  }
  async function exportFile(which){
    if(!activeFile||!currentData)return;
    status("Preparing review export…");
    try{
      const body=new FormData();body.append("file",activeFile);
      const response=await api("/export/"+which,{method:"POST",body});
      const url=URL.createObjectURL(await response.blob());
      const link=document.createElement("a");link.href=url;
      link.download=which==="xlsx"?"audit_review.xlsx":"audit_report.html";
      document.body.append(link);link.click();link.remove();
      setTimeout(()=>URL.revokeObjectURL(url),30000);
      status("Report downloaded.");
    }catch(e){status(e.message);}
  }
  async function billing(kind){
    try{
      const json=await(await api("/billing/"+kind,{method:"POST"})).json();
      if(!json.url?.startsWith("https://"))throw Error("Unexpected billing URL.");
      window.location.assign(json.url);
    }catch(e){status("Billing: "+e.message);}
  }
  async function removeAccount(){
    if(!confirm("Delete your DQD usage and account records? This cannot be undone. Your separate login still requires a support request."))return;
    try{
      const response=await api("/account",{method:"DELETE"});
      const detail=await response.json();
      status(detail.note);
      await client.auth.signOut();
      await refresh();
    }catch(e){status(e.message);}
  }
  async function start(){
    try{
      const response=await fetch("/api/saas/config",{cache:"no-store"});
      cfg=await response.json();
      if(!response.ok||!cfg.enabled){show("unavailable",true);status("Private beta remains disabled.");return;}
      if(!window.supabase?.createClient)throw Error("Authentication library unavailable.");
      client=window.supabase.createClient(cfg.supabase_url,cfg.supabase_anon_key,{
        auth:{detectSessionInUrl:true,autoRefreshToken:true,persistSession:true}
      });
      $("signin").onclick=()=>auth("signin");
      $("signup").onclick=()=>auth("signup");
      $("signout").onclick=async()=>{await client.auth.signOut();activeFile=null;currentData=null;show("reports",false);await refresh();};
      $("file").onchange=()=>{activeFile=$("file").files[0]||null;currentData=null;show("reports",false);$("analyze").disabled=!activeFile;};
      $("analyze").onclick=analyze;
      $("htmlExport").onclick=()=>exportFile("html");
      $("xlsxExport").onclick=()=>exportFile("xlsx");
      $("upgrade").onclick=()=>billing("checkout");
      $("billing").onclick=()=>billing("portal");
      $("delete").onclick=removeAccount;
      client.auth.onAuthStateChange(()=>{setTimeout(refresh,0);});
      await refresh();
    }catch(e){show("unavailable",true);status("Private workspace initialization failed: "+e.message);}
  }
  window.addEventListener("DOMContentLoaded",start);
})();