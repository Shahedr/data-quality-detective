"""Private-beta SaaS API: authenticated, metered, and fail-closed.

This is separate from the public sample demo and local, full-featured app.
No uploaded workbook bytes, cell values or filenames are intentionally stored
in the SaaS database. Multipart parsers may spool content to ephemeral disk.

Requires Supabase asymmetric JWT, Postgres and Stripe credentials; do NOT
activate customer uploads until a production security/privacy review.
"""
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import jwt
import psycopg
import stripe
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from jwt import PyJWKClient
from psycopg.rows import dict_row

from dqdetect.profiler import profile_dataframe
from webapp.export import full_html_chunks, full_workbook_html_chunks
from webapp.xlsx_export import build_review_workbook, stream_file_chunks
from webapp.workbook import parse_sheets, validate_upload


# Lazy delegation avoids importing the local web app during private-router startup.
# These core functions are identical to those used in the offline browser.
def analyze_bytes(*args, **kwargs):
    from webapp.app import analyze_bytes as handler
    return handler(*args, **kwargs)


def inspect_bytes(*args, **kwargs):
    from webapp.app import inspect_bytes as handler
    return handler(*args, **kwargs)


def _read_dataset(*args, **kwargs):
    from webapp.app import _read_dataset as handler
    return handler(*args, **kwargs)


def _workbook_macro_audit(*args, **kwargs):
    from webapp.app import _workbook_macro_audit as handler
    return handler(*args, **kwargs)


router = APIRouter(prefix="/api/saas", tags=["Private SaaS beta"])
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_WEBHOOK_BYTES = 256 * 1024
FREE_MONTHLY_ANALYSES = 10
PRO_MONTHLY_ANALYSES = 500
DAILY_REQUEST_CAP = 600
ACTIVE_STATUSES = {"active", "trialing"}


def enabled():
    return (os.getenv("DQD_SAAS_ENABLED", "").strip() == "1"
            and os.getenv("DQD_SAAS_LAUNCH_APPROVED", "").strip() == "1")


def _required_env():
    names = (
        "SUPABASE_URL", "SUPABASE_ANON_KEY", "DQD_SAAS_DATABASE_URL",
        "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRO_PRICE_ID",
        "DQD_SITE_URL", "DQD_LEGAL_ENTITY", "DQD_PRIVACY_EMAIL",
    )
    return all(os.getenv(key) for key in names)


def ready():
    """No customer signup or uploads without full operator approval."""
    return enabled() and _required_env()


def _admin_owner_configured():
    """Validate the private immutable owner UUID; never expose it in public config."""
    import uuid
    try:
        allowed = str(uuid.UUID(os.environ["DQD_ADMIN_USER_ID"]))
    except (KeyError, ValueError, AttributeError):
        return False
    return allowed != str(uuid.UUID(int=0))


def admin_auth_ready():
    """Owner login/MFA setup only, independent of customer SaaS and DB access.

    The optional setup flag allows an invited owner to enroll MFA *before*
    database credentials or the read-only admin overview are configured.
    """
    return (_admin_owner_configured()
            and (os.getenv("DQD_ADMIN_SETUP_ENABLED") == "1"
                 or os.getenv("DQD_ADMIN_ENABLED") == "1")
            and bool(os.getenv("SUPABASE_URL"))
            and bool(os.getenv("SUPABASE_ANON_KEY")))


def admin_ready():
    """Read-only owner metrics require a separate explicit database gate."""
    return (admin_auth_ready()
            and os.getenv("DQD_ADMIN_ENABLED", "") == "1"
            and bool(os.getenv("DQD_SAAS_DATABASE_URL")))


def _site_url():
    value = os.environ["DQD_SITE_URL"].rstrip("/")
    if not value.startswith("https://") and not value.startswith("http://127.0.0.1:"):
        raise HTTPException(503, "SaaS site origin must use HTTPS.")
    return value


def _supabase_origin():
    value = os.environ["SUPABASE_URL"].rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".supabase.co"):
        raise HTTPException(503, "Unsupported Supabase project URL.")
    return value


def guard():
    if not ready():
        raise HTTPException(503, "Private beta is not enabled on this deployment.")


@lru_cache(maxsize=4)
def _key_client(jwks_url):
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=300)


def _authenticate_bearer(token, *, require_aal2=False):
    """Verify asymmetric JWT against project-specific JWKS, issuer and audience."""
    if len(token) > 8192:
        raise HTTPException(401, "Invalid login token.")
    origin = _supabase_origin()
    issuer = origin + "/auth/v1"
    try:
        key = _key_client(issuer + "/.well-known/jwks.json").get_signing_key_from_jwt(token)
        decoded = jwt.decode(
            token,
            key.key,
            algorithms=["RS256", "ES256"],
            issuer=issuer,
            audience="authenticated",
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            leeway=10,
        )
        if decoded.get("role") != "authenticated":
            raise ValueError("Not an authenticated user")
        if require_aal2 and decoded.get("aal") != "aal2":
            raise ValueError("Admin console requires an MFA-verified session")
        subject = decoded["sub"]
        # Supabase Auth user IDs are UUIDs. Do not accept arbitrary identity strings.
        import uuid
        return str(uuid.UUID(subject))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, "Login expired or invalid. Sign in again.") from None


def account_id(request: Request):
    guard()
    authorization = request.headers.get("authorization", "")
    match = re.fullmatch(r"Bearer ([A-Za-z0-9._-]+)", authorization)
    if not match:
        raise HTTPException(401, "Sign in is required.")
    return _authenticate_bearer(match.group(1))


def admin_id(request: Request):
    """Authorize by immutable Supabase subject and MFA, never by email.

    Do not put the admin UUID in client JavaScript, markup or Git.
    """
    if not admin_ready():
        raise HTTPException(503, "Admin console is not configured.")
    header = request.headers.get("authorization", "")
    match = re.fullmatch(r"Bearer ([A-Za-z0-9._-]+)", header)
    if not match:
        raise HTTPException(401, "Admin sign-in is required.")
    subject = _authenticate_bearer(match.group(1), require_aal2=True)
    import uuid
    if subject != str(uuid.UUID(os.environ["DQD_ADMIN_USER_ID"])):
        raise HTTPException(403, "You do not have permission to access the admin console.")
    return subject


def _database():
    # A shared, durable Postgres/Supabase backend is REQUIRED for metering.
    # Never use SQLite or in-memory counters on serverless deployments.
    url = os.environ["DQD_SAAS_DATABASE_URL"]
    if os.getenv("VERCEL") and "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = url + sep + "sslmode=require"
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=6)


def _bootstrap(cur, subject):
    cur.execute(
        "INSERT INTO saas_accounts (user_id) VALUES (%s) "
        "ON CONFLICT (user_id) DO NOTHING", (subject,)
    )


def _plan(cur, subject):
    _bootstrap(cur, subject)
    cur.execute(
        "SELECT stripe_customer_id, subscription_status, subscription_id "
        "FROM saas_accounts WHERE user_id=%s FOR UPDATE", (subject,),
    )
    return cur.fetchone()


def _quota(status):
    return PRO_MONTHLY_ANALYSES if status in ACTIVE_STATUSES else FREE_MONTHLY_ANALYSES


def meter(subject, event_type):
    """Atomic database-backed per-user daily limit and monthly analysis quota."""
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)
    with _database() as conn:
        with conn.cursor() as cur:
            account = _plan(cur, subject)  # row lock prevents quota races
            cur.execute(
                "INSERT INTO saas_daily_usage(user_id, usage_day, requests) "
                "VALUES (%s,%s,0) ON CONFLICT DO NOTHING", (subject, today),
            )
            cur.execute(
                "SELECT requests FROM saas_daily_usage "
                "WHERE user_id=%s AND usage_day=%s FOR UPDATE", (subject, today),
            )
            daily = cur.fetchone()["requests"]
            if daily >= DAILY_REQUEST_CAP:
                raise HTTPException(429, "Daily usage limit reached.")
            if event_type == "analysis":
                cur.execute(
                    "INSERT INTO saas_monthly_usage(user_id, month_start, analyses) "
                    "VALUES (%s,%s,0) ON CONFLICT DO NOTHING", (subject, month_start),
                )
                cur.execute(
                    "SELECT analyses FROM saas_monthly_usage "
                    "WHERE user_id=%s AND month_start=%s FOR UPDATE",
                    (subject, month_start),
                )
                uses = cur.fetchone()["analyses"]
                if uses >= _quota(account["subscription_status"]):
                    raise HTTPException(429, "Monthly analysis quota reached. Manage your plan to continue.")
                cur.execute(
                    "UPDATE saas_monthly_usage SET analyses=analyses+1 "
                    "WHERE user_id=%s AND month_start=%s", (subject, month_start),
                )
            cur.execute(
                "UPDATE saas_daily_usage SET requests=requests+1 "
                "WHERE user_id=%s AND usage_day=%s", (subject, today),
            )
    return True


async def read_upload(file):
    name = Path(file.filename or "").name
    if not name:
        raise HTTPException(400, "Select a file.")
    try:
        data = await file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Private beta uploads cannot exceed 2 MiB.")
    # Defense in depth; reject highly compressed workbook bombs more tightly
    # than the local/offline analyzer and disallow unnecessarily large sheets.
    if Path(name).suffix.lower() in {".xlsx", ".xlsm"}:
        from zipfile import ZipFile, BadZipFile
        import io
        try:
            with ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > 250 or sum(x.file_size for x in entries) > 20 * 1024 * 1024:
                    raise HTTPException(413, "Workbook expansion exceeds private-beta limits.")
        except BadZipFile:
            raise HTTPException(422, "Invalid workbook archive.") from None
    validate_upload(name, data)
    return name, data


@router.get("/config")
def public_configuration():
    """Only publish public Supabase identifiers, never database or Stripe secrets."""
    return {
        "enabled": ready(),
        "supabase_url": os.getenv("SUPABASE_URL") if ready() else None,
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY") if ready() else None,
        "plans": {"free": FREE_MONTHLY_ANALYSES, "pro": PRO_MONTHLY_ANALYSES},
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "no_macro_execution": True,
        "legal_entity": os.getenv("DQD_LEGAL_ENTITY") if ready() else None,
        "privacy_contact": os.getenv("DQD_PRIVACY_EMAIL") if ready() else None,
    }


@router.get("/admin/config")
def admin_configuration():
    """Only public Auth configuration. No user IDs, database credentials or keys."""
    auth_enabled = admin_auth_ready()
    return {
        "enabled": auth_enabled,
        "overview_enabled": admin_ready(),
        "supabase_url": os.getenv("SUPABASE_URL") if auth_enabled else None,
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY") if auth_enabled else None,
        "mfa_required": True,
        "read_only": True,
    }


@router.get("/admin/overview")
def admin_overview(subject: str = Depends(admin_id)):
    """Aggregate-only read access; no customer emails, rows, files or tokens."""
    with _database() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS accounts, "
                "COUNT(*) FILTER (WHERE subscription_status IN ('active','trialing')) AS active_pro "
                "FROM saas_accounts"
            )
            subscribers = cur.fetchone()
            cur.execute("SELECT COALESCE(SUM(analyses),0) AS total FROM saas_monthly_usage")
            analyzed = cur.fetchone()
            cur.execute("SELECT COUNT(*) AS total FROM saas_stripe_events")
            events = cur.fetchone()
    return {
        "accounts": subscribers["accounts"],
        "active_pro_accounts": subscribers["active_pro"],
        "all_time_analyses": analyzed["total"],
        "processed_webhook_events": events["total"],
        "uploaded_files_stored_in_app_database": False,
        "read_only": True,
    }


@router.get("/account")
def account(subject: str = Depends(account_id)):
    today = datetime.now(timezone.utc).date().replace(day=1)
    with _database() as conn:
        with conn.cursor() as cur:
            row = _plan(cur, subject)
            cur.execute(
                "SELECT analyses FROM saas_monthly_usage WHERE user_id=%s AND month_start=%s",
                (subject, today),
            )
            usage = cur.fetchone()
    return {
        "plan": "pro" if row["subscription_status"] in ACTIVE_STATUSES else "free",
        "subscription_status": row["subscription_status"],
        "analyses_this_month": usage["analyses"] if usage else 0,
        "monthly_limit": _quota(row["subscription_status"]),
        "uploads_stored": False,
    }


@router.post("/analyze")
async def analyze(file: UploadFile = File(...), sheet: str = "",
                  subject: str = Depends(account_id)):
    name, data = await read_upload(file)
    meter(subject, "analysis")
    return JSONResponse(analyze_bytes(name, data, sheet=sheet))


@router.post("/rows")
async def rows(file: UploadFile = File(...), page: int = 1, issue: str = "all",
               sheet: str = "", subject: str = Depends(account_id)):
    name, data = await read_upload(file)
    meter(subject, "read")
    return JSONResponse(inspect_bytes(name, data, page=page, issue=issue, sheet=sheet))


@router.post("/export/html")
async def export_html(file: UploadFile = File(...),
                      subject: str = Depends(account_id)):
    name, data = await read_upload(file)
    meter(subject, "export")
    df, review, frames, _, suffix, reviews = _read_dataset(
        name, data, all_reviews=True
    )
    profiles = {tab: profile_dataframe(frame, source_name=name)
                for tab, frame in frames.items()}
    if suffix == ".csv":
        output = full_html_chunks(profiles[next(iter(frames))], df)
    else:
        output = full_workbook_html_chunks(
            profiles, frames, reviews,
            _workbook_macro_audit(name, data, review, suffix)
        )
    return StreamingResponse(
        output, media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="audit_report.html"'},
    )


@router.post("/export/xlsx")
async def export_excel(file: UploadFile = File(...),
                       subject: str = Depends(account_id)):
    name, data = await read_upload(file)
    meter(subject, "export")
    _, review, frames, _, suffix, reviews = _read_dataset(
        name, data, all_reviews=True
    )
    profiles = {tab: profile_dataframe(frame, source_name=name)
                for tab, frame in frames.items()}
    output = build_review_workbook(
        frames, reviews, profiles, name,
        _workbook_macro_audit(name, data, review, suffix)
    )
    return StreamingResponse(
        stream_file_chunks(output),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="audit_review.xlsx"'},
    )


def _is_pro_subscription(subscription, expected_price):
    """Grant Pro only for this application's configured recurring Stripe price.

    Webhook signatures authenticate Stripe as sender, not that an arbitrary
    subscription/product matches the plan the service is selling.
    """
    if not isinstance(subscription, dict) or not expected_price:
        return False
    items = subscription.get("items")
    if not isinstance(items, dict) or not isinstance(items.get("data"), list):
        return False
    for entry in items["data"]:
        if not isinstance(entry, dict):
            continue
        price = entry.get("price")
        if isinstance(price, dict) and price.get("id") == expected_price:
            return True
    return False


@router.post("/billing/checkout")
def create_checkout(subject: str = Depends(account_id)):
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    _site_url()
    with _database() as conn:
        with conn.cursor() as cur:
            account = _plan(cur, subject)
            if account["subscription_status"] in ACTIVE_STATUSES:
                raise HTTPException(409, "Your subscription is already active.")
            if account["subscription_status"] in {"past_due", "unpaid", "paused", "incomplete"}:
                raise HTTPException(409, "Manage your current subscription in Billing before starting another.")
    params = {
        "mode": "subscription",
        "line_items": [{"price": os.environ["STRIPE_PRO_PRICE_ID"], "quantity": 1}],
        "success_url": _site_url() + "/app?billing=success",
        "cancel_url": _site_url() + "/app?billing=cancelled",
        "client_reference_id": subject,
        "subscription_data": {"metadata": {"dqd_user_id": subject}},
        "allow_promotion_codes": False,
    }
    # Reuse an existing verified customer instead of creating duplicates.
    if account["stripe_customer_id"]:
        params["customer"] = account["stripe_customer_id"]
    try:
        session = stripe.checkout.Session.create(**params)
    except stripe.error.StripeError:
        raise HTTPException(503, "Billing provider is temporarily unavailable.") from None
    return {"url": session.url}


@router.post("/billing/portal")
def billing_portal(subject: str = Depends(account_id)):
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    with _database() as conn:
        with conn.cursor() as cur:
            account = _plan(cur, subject)
            customer = account["stripe_customer_id"]
    if not customer:
        raise HTTPException(404, "No billing customer exists for this account.")
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer, return_url=_site_url() + "/app"
        )
    except stripe.error.StripeError:
        raise HTTPException(503, "Billing provider is temporarily unavailable.") from None
    return {"url": session.url}


@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    guard()
    body = await request.body()
    if len(body) > MAX_WEBHOOK_BYTES:
        raise HTTPException(413, "Webhook is too large.")
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            body, signature, os.environ["STRIPE_WEBHOOK_SECRET"]
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(400, "Invalid webhook signature.") from None
    event_id = event["id"]
    kind = event["type"]
    item = event["data"]["object"]
    with _database() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO saas_stripe_events(event_id) VALUES (%s) "
                "ON CONFLICT DO NOTHING RETURNING event_id", (event_id,),
            )
            if not cur.fetchone():
                return {"received": True, "duplicate": True}
            if kind == "checkout.session.completed" and item.get("mode") == "subscription":
                user = item.get("client_reference_id")
                if user:
                    # Do not implicitly create an account from arbitrary webhook metadata.
                    cur.execute(
                        "UPDATE saas_accounts SET stripe_customer_id=%s, subscription_id=%s "
                        "WHERE user_id=%s AND (stripe_customer_id IS NULL OR stripe_customer_id=%s)",
                        (item.get("customer"), item.get("subscription"), user, item.get("customer")),
                    )
            elif kind in {
                "customer.subscription.created",
                "customer.subscription.updated",
                "customer.subscription.deleted",
            }:
                metadata = item.get("metadata") or {}
                user = metadata.get("dqd_user_id")
                if (user and item.get("id") and item.get("customer")
                        and _is_pro_subscription(item, os.environ["STRIPE_PRO_PRICE_ID"])):
                    # Only subscriptions for our exact configured Pro price
                    # are allowed to change the user's quota/entitlement.
                    # A renewal event can arrive before the Checkout event.
                    # Customer identity remains tied to the Supabase account.
                    cur.execute(
                        "UPDATE saas_accounts SET stripe_customer_id=%s, "
                        "subscription_id=%s, subscription_status=%s, subscription_event_at=%s "
                        "WHERE user_id=%s AND (stripe_customer_id IS NULL OR stripe_customer_id=%s) "
                        "AND subscription_event_at <= %s",
                        (item["customer"], item["id"], item.get("status", "unknown"),
                         int(event.get("created", 0)), user, item["customer"],
                         int(event.get("created", 0))),
                    )
    return {"received": True}


@router.delete("/account")
def delete_account(subject: str = Depends(account_id)):
    """Delete DQD-only usage/account metadata; provider identity is separate."""
    with _database() as conn:
        with conn.cursor() as cur:
            current = _plan(cur, subject)
            if current["subscription_status"] in ACTIVE_STATUSES:
                raise HTTPException(
                    409, "Cancel the subscription in Billing first, and wait until it is inactive."
                )
            cur.execute("DELETE FROM saas_accounts WHERE user_id=%s", (subject,))
    return {
        "deleted": True,
        "note": "DQD usage records deleted. Delete your separate Supabase sign-in "
                "account via support; Stripe records have separate legal retention.",
    }
