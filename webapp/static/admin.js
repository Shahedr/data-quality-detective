"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const show = (id,visible) => $(id).classList.toggle("hidden",!visible);
  const status = message => $("status").textContent = message;
  let client = null, factorId = null, cfg = null;
  async function getToken(){
    const {data,error} = await client.auth.getSession();
    if (error || !data.session?.access_token) throw Error("Sign in again.");
    return data.session.access_token;
  }
  function fillTrend(tableId, entries, labelField, countField){
    const body=$(tableId);
    body.replaceChildren();
    for(const entry of entries){
      const row=document.createElement("tr");
      const label=document.createElement("td");
      const count=document.createElement("td");
      label.textContent=String(entry[labelField]??"");
      count.textContent=String(entry[countField]??0);
      count.className="numeric";
      row.append(label,count);
      body.append(row);
    }
  }
  async function overview(){
    let info;
    if(cfg.overview_source==="supabase_rpc"){
      // JWT verification and MFA owner allowlist are enforced by Supabase
      // PostgREST and the private SQL SECURITY DEFINER function, NOT the UI.
      const {data,error}=await client.rpc("dqd_owner_overview");
      if(error)throw Error("Owner metrics permission denied or temporarily unavailable.");
      info=data;
    }else if(cfg.overview_source==="server"){
      const token=await getToken();
      const response=await fetch("/api/saas/admin/overview",{
        headers:{"Authorization":"Bearer "+token},cache:"no-store"
      });
      if(!response.ok)throw Error("Owner metrics permission denied or unavailable.");
      info=await response.json();
    }else{
      throw Error("Owner overview has not been enabled.");
    }
    if(!info || info.read_only!==true)throw Error("Invalid owner metrics response.");
    $("accounts").textContent=String(info.accounts??0);
    $("identities").textContent=String(info.registered_identities??"—");
    $("active").textContent=String(info.active_pro_accounts??0);
    $("analyses").textContent=String(info.all_time_analyses??0);
    $("monthAnalyses").textContent=String(info.analyses_this_month??"—");
    $("requestsToday").textContent=String(info.requests_today??"—");
    $("webhooks").textContent=String(info.processed_webhook_events??0);
    fillTrend("dailyActivity",info.daily_activity||[],"date","requests");
    fillTrend("monthlyActivity",info.monthly_activity||[],"month","analyses");
    $("reportTimestamp").textContent=info.generated_at_utc
      ? "Database snapshot: "+String(info.generated_at_utc)+" UTC" : "Read-only database aggregates.";
    show("overview",true);
    status("Owner access verified · MFA-protected read-only dashboard.");
  }
  async function refresh(){
    for (const id of ["login","mfa","overview","setupComplete"]) show(id,false);
    const {data}=await client.auth.getSession();
    if (!data.session){show("login",true);status("Owner sign-in required.");return;}
    const {data:assurance,error}=await client.auth.mfa.getAuthenticatorAssuranceLevel();
    if (error) throw error;
    if (assurance.currentLevel==="aal2"){
      if (cfg.overview_enabled) await overview();
      else {show("setupComplete",true);status("Authenticator verified. Owner setup complete; dashboard access is still gated.");}
      return;
    }
    const {data:factors,error:fError}=await client.auth.mfa.listFactors();
    if (fError) throw fError;
    const verified=(factors.totp||[]).find(f=>f.status==="verified");
    factorId=verified?.id||null;
    $("enroll").classList.toggle("hidden",!!verified);
    $("mfaMessage").textContent=verified
      ?"Enter the six-digit code from your registered authenticator app."
      :"Enroll an authenticator app, then enter its six-digit code.";
    show("mfa",true);status("Authenticator verification required.");
  }
  async function signIn(){
    $("signin").disabled=true;
    try{
      const {error}=await client.auth.signInWithPassword({
        email:$("email").value.trim(),password:$("password").value
      });
      if(error)throw error;
      $("password").value="";
      await refresh();
    }catch(e){
      const badPassword=/invalid login credentials/i.test(e.message||"");
      status(badPassword
        ?"Email/password sign-in failed. The password for this application's Supabase Auth user may differ from your Supabase dashboard password. Try the one-time email link below."
        :"Sign-in failed: "+e.message);
    }
    finally{$("signin").disabled=false;}
  }
  async function sendEmailLink(){
    const button=$("emailLink");
    button.disabled=true;
    try{
      const email=$("email").value.trim();
      if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)){
        throw Error("Enter your account email address first.");
      }
      // Email authentication uses the existing Supabase user only:
      // never create a new public account while this app is in private beta.
      const {error}=await client.auth.signInWithOtp({
        email,
        options:{
          shouldCreateUser:false,
          emailRedirectTo:window.location.origin+"/admin"
        }
      });
      if(error)throw error;
      status("Check your inbox for the one-time sign-in link. Open it in this browser. Do not share the link.");
    }catch(e){
      status("Email sign-in could not start: "+e.message);
    }finally{button.disabled=false;}
  }
  async function enroll(){
    try{
      const {data,error}=await client.auth.mfa.enroll({
        factorType:"totp",friendlyName:"DQD owner console"
      });
      if(error)throw error;
      factorId=data.id;
      const qr=data.totp?.qr_code;
      if(typeof qr!=="string"||!qr.startsWith("data:image/svg+xml;")){
        throw Error("Supabase did not supply an expected authenticator QR code.");
      }
      $("qr").src=qr;show("qr",true);
      $("mfaSecret").textContent="Scan the code in your authenticator. Keep this code private.";
      status("Enter a fresh six-digit code to finish enrollment.");
    }catch(e){status("MFA setup failed: "+e.message)}
  }
  async function verify(){
    try{
      if(!factorId)throw Error("Enroll or select an authenticator first.");
      const code=$("code").value.trim();
      if(!/^\d{6}$/.test(code))throw Error("Enter a six-digit code.");
      const {error}=await client.auth.mfa.challengeAndVerify({factorId,code});
      if(error)throw error;
      $("code").value="";$("qr").removeAttribute("src");show("qr",false);
      await refresh();
    }catch(e){status("Verification failed: "+e.message)}
  }
  async function signOut(){
    await client.auth.signOut();
    $("code").value="";$("qr").removeAttribute("src");show("qr",false);
    factorId=null;await refresh();
  }
  async function start(){
    try{
      const response=await fetch("/api/saas/admin/config",{cache:"no-store"});
      if(!response.ok)throw Error("Owner configuration is unavailable.");
      cfg=await response.json();
      if(!cfg.enabled){show("unavailable",true);status("Admin access is not yet configured.");return;}
      await new Promise((resolve,reject)=>{
        const script=document.createElement("script");
        script.src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.79.0/dist/umd/supabase.min.js";
        script.referrerPolicy="no-referrer";script.crossOrigin="anonymous";
        script.onload=resolve;script.onerror=()=>reject(Error("Auth SDK not available."));
        document.head.appendChild(script);
      });
      if(!window.supabase?.createClient)throw Error("Auth SDK did not initialize.");
      client=window.supabase.createClient(cfg.supabase_url,cfg.supabase_anon_key,{
        auth:{detectSessionInUrl:true,autoRefreshToken:true,persistSession:true}
      });
      $("signin").onclick=signIn;
      $("emailLink").onclick=sendEmailLink;
      $("enroll").onclick=enroll;
      $("verify").onclick=verify;
      $("signout").onclick=signOut;
      $("signoutMfa").onclick=signOut;
      $("signoutSetup").onclick=signOut;
      await refresh();
    }catch(e){show("unavailable",true);status("Owner console error: "+e.message);}
  }
  document.addEventListener("DOMContentLoaded",start);
})();