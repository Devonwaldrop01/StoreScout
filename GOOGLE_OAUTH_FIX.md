# Google integration — production OAuth fix

The Google (GA4 + Search Console) integration is **hidden by default** for
launch (`GOOGLE_INTEGRATION_ENABLED=false`). Production OAuth currently fails
with `redirect_uri_mismatch` because the production callback URL isn't
registered on the OAuth client. Do this, then flip the flag on.

## Fix

1. **Google Cloud Console** → APIs & Services → Credentials → your OAuth 2.0
   Client ID (the one whose ID matches `GOOGLE_CLIENT_ID` in Render).
2. Under **Authorized redirect URIs**, add EXACTLY (no trailing slash):

   ```
   https://getstorescout.com/api/v1/integrations/google/callback
   ```

   Add the API subdomain variant too if the backend serves under it, e.g.
   `https://api.getstorescout.com/api/v1/integrations/google/callback`.
3. Under **Authorized JavaScript origins**, add `https://getstorescout.com`.
4. Save. Google can take a few minutes to propagate.
5. In Render, confirm the backend env:
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` are the **production** client's.
   - `PUBLIC_BASE_URL=https://getstorescout.com` (the callback is derived from it).
6. Verify the callback the app sends matches: `app/api/v1/integrations.py`
   builds it from `PUBLIC_BASE_URL` + `/api/v1/integrations/google/callback`.
   It must be byte-identical to what you registered in step 2.

## Turn it back on

Once a real connect → callback round-trip succeeds:

```
GOOGLE_INTEGRATION_ENABLED=true
```

The Settings → Intelligence Sources card and the connect endpoint re-enable
automatically. Until then, users never see a broken flow — the card is
hidden and `/google/connect-url` returns a clean 503.
