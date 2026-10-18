"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const show = (id,visible) => $(id).classList.toggle("hidden",!visible);
  const status = message => $("status").textContent = message;
  let client = null, factorId = null;
  async function getToken(){
    const {data,error} = await client.auth.getSession();
    if (error || !data.session?.access_token) throw Error("Sign in again.");
    return data.session.access_token;
  }
  async function overview(){
    const token = await getToken();
    const response = await fetch("/api/saas/admin/overview",{
      headers:{"Authorization":"Bearer "+token},cache:"no-store"
    });
    if (!response.ok) {
      const result=await response.json().catch(()=>({}));
      throw Error(result.detail||"Owner access refused ("+response.status+").");
    }
    const info=await response.json();
    $("accounts").textContent=String(info.accounts);
    $("active").textContent=String(info.active_pro_accounts);
    $("analyses").textContent=String(info.all_time_analyses);
    $("webhooks").textContent=String(info.processed_webhook_events);
    show("overview",true);
    status("Owner access verified · Read-only.");
  }
  async function refresh(){
    for (const id of ["login","mfa","overview"]) show(id,false);
    const {data}=await client.auth.getSession();
    if (!data.session){show("login",true);status("Owner sign-in required.");return;}
    const {data:assurance,error}=await client.auth.mfa.getAuthenticatorAssuranceLevel();
    if (error) throw error;
    if (assurance.currentLevel==="aal2"){await overview();return;}
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
    }catch(e){status("Sign-in failed: "+e.message)}
    finally{$("signin").disabled=false;}
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
      const cfg=await response.json();
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
      $("enroll").onclick=enroll;
      $("verify").onclick=verify;
      $("signout").onclick=signOut;
      $("signoutMfa").onclick=signOut;
      await refresh();
    }catch(e){show("unavailable",true);status("Owner console error: "+e.message);}
  }
  document.addEventListener("DOMContentLoaded",start);
})();