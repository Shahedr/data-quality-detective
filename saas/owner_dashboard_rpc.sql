-- Owner-only aggregate dashboard using Supabase Auth JWT, no database password
-- in a Vercel environment or browser. Full customer SaaS remains independently off.
-- The owner identity is provisioned privately AFTER migration, never committed here.
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS private.dqd_admin_owners (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    enrolled_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE private.dqd_admin_owners ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON private.dqd_admin_owners FROM PUBLIC, anon, authenticated;

CREATE OR REPLACE FUNCTION public.dqd_owner_overview()
RETURNS jsonb
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $function$
DECLARE
    requesting_user uuid;
BEGIN
    -- When called through Supabase PostgREST, auth.uid() and auth.jwt() are
    -- populated ONLY after verification of the bearer token by Supabase Auth.
    requesting_user := auth.uid();
    IF requesting_user IS NULL
       OR auth.jwt() ->> 'aal' IS DISTINCT FROM 'aal2'
       OR NOT EXISTS (
           SELECT 1 FROM private.dqd_admin_owners
           WHERE user_id = requesting_user
       )
    THEN
       RAISE EXCEPTION 'Owner MFA authorization required'
           USING ERRCODE = '42501';
    END IF;

    -- Results intentionally contain aggregates only; no email addresses,
    -- source spreadsheet contents, Stripe identifiers, IPs or user IDs.
    RETURN jsonb_build_object(
        'accounts', (SELECT count(*) FROM public.saas_accounts),
        'registered_identities', (SELECT count(*) FROM auth.users),
        'active_pro_accounts',
            (SELECT count(*) FROM public.saas_accounts
             WHERE subscription_status IN ('active', 'trialing')),
        'analyses_this_month',
            (SELECT coalesce(sum(analyses), 0) FROM public.saas_monthly_usage
             WHERE month_start = date_trunc('month', now() AT TIME ZONE 'UTC')::date),
        'all_time_analyses',
            (SELECT coalesce(sum(analyses), 0) FROM public.saas_monthly_usage),
        'requests_today',
            (SELECT coalesce(sum(requests), 0) FROM public.saas_daily_usage
             WHERE usage_day = (now() AT TIME ZONE 'UTC')::date),
        'processed_webhook_events',
            (SELECT count(*) FROM public.saas_stripe_events),
        'daily_activity',
            (SELECT coalesce(jsonb_agg(jsonb_build_object(
                  'date', day::text, 'requests', coalesce(u.requests, 0))
                  ORDER BY day), '[]'::jsonb)
             FROM generate_series((now() AT TIME ZONE 'UTC')::date - 6,
                                   (now() AT TIME ZONE 'UTC')::date,
                                   interval '1 day') AS d(day)
             LEFT JOIN (
                SELECT usage_day, sum(requests) AS requests
                FROM public.saas_daily_usage
                GROUP BY usage_day
             ) u ON u.usage_day = d.day::date),
        'monthly_activity',
            (SELECT coalesce(jsonb_agg(jsonb_build_object(
                 'month', months.month::date::text,
                 'analyses', coalesce(u.analyses, 0))
                 ORDER BY months.month), '[]'::jsonb)
             FROM generate_series(
               date_trunc('month', now() AT TIME ZONE 'UTC') - interval '5 months',
               date_trunc('month', now() AT TIME ZONE 'UTC'),
               interval '1 month') AS months(month)
             LEFT JOIN (
                 SELECT month_start, sum(analyses) AS analyses
                 FROM public.saas_monthly_usage
                 GROUP BY month_start
             ) u ON u.month_start = months.month::date),
        'read_only', true,
        'uploads_stored_in_application_database', false,
        'generated_at_utc', (now() AT TIME ZONE 'UTC')::text
    );
END;
$function$;

-- Default PostgreSQL functions allow PUBLIC EXECUTE: explicitly revoke
-- before granting to the signed-in browser role. Anonymous cannot invoke.
REVOKE ALL ON FUNCTION public.dqd_owner_overview() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.dqd_owner_overview() TO authenticated;

COMMENT ON FUNCTION public.dqd_owner_overview() IS
'Read-only aggregate metrics, guarded by verified Supabase Auth user allowlist and aal2 MFA';
