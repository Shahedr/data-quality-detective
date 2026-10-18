-- Data Quality Detective SaaS private-beta schema.
-- Apply in Supabase SQL editor under service-owner permissions (NOT the anon role).
-- The browser uses only Supabase Auth; all tables are accessed through the
-- private server with DQD_SAAS_DATABASE_URL, never with the public anon key.
CREATE TABLE IF NOT EXISTS public.saas_accounts (
    user_id uuid PRIMARY KEY,
    stripe_customer_id text UNIQUE,
    subscription_id text UNIQUE,
    subscription_event_at bigint NOT NULL DEFAULT 0,
    subscription_status text NOT NULL DEFAULT 'free'
        CHECK (subscription_status IN (
            'free', 'incomplete', 'incomplete_expired', 'trialing', 'active',
            'past_due', 'canceled', 'unpaid', 'paused', 'unknown'
        )),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.saas_daily_usage (
    user_id uuid NOT NULL REFERENCES public.saas_accounts(user_id) ON DELETE CASCADE,
    usage_day date NOT NULL,
    requests integer NOT NULL DEFAULT 0 CHECK (requests >= 0),
    PRIMARY KEY (user_id, usage_day)
);

CREATE TABLE IF NOT EXISTS public.saas_monthly_usage (
    user_id uuid NOT NULL REFERENCES public.saas_accounts(user_id) ON DELETE CASCADE,
    month_start date NOT NULL,
    analyses integer NOT NULL DEFAULT 0 CHECK (analyses >= 0),
    PRIMARY KEY (user_id, month_start)
);

CREATE TABLE IF NOT EXISTS public.saas_stripe_events (
    event_id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Fail closed from Supabase REST/GraphQL; the server uses a direct Postgres
-- connection. No credentials or row policies are exposed to anonymous clients.
ALTER TABLE public.saas_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saas_daily_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saas_monthly_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saas_stripe_events ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.saas_accounts FROM anon, authenticated;
REVOKE ALL ON public.saas_daily_usage FROM anon, authenticated;
REVOKE ALL ON public.saas_monthly_usage FROM anon, authenticated;
REVOKE ALL ON public.saas_stripe_events FROM anon, authenticated;
