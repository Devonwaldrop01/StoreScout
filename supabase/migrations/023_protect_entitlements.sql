-- Review against the deployed schema before applying. No production change
-- has been made. All current application writes use the trusted FastAPI API.
BEGIN;

-- Row ownership alone does not protect billing/plan columns.
DROP POLICY IF EXISTS "Users can update own profile" ON public.user_profiles;
REVOKE INSERT, UPDATE, DELETE ON public.user_profiles FROM anon, authenticated;

-- Prevent direct browser writes from bypassing API quotas or changing scan state.
DROP POLICY IF EXISTS "Users manage own competitors" ON public.competitors;
DROP POLICY IF EXISTS "Users read own competitors" ON public.competitors;
CREATE POLICY "Users read own competitors" ON public.competitors
  FOR SELECT TO authenticated USING (auth.uid() = user_id);
REVOKE INSERT, UPDATE, DELETE ON public.competitors FROM anon, authenticated;

-- This internal delivery log did not enable RLS in the initial migration.
ALTER TABLE public.alert_email_log ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.alert_email_log FROM anon, authenticated;

COMMIT;
