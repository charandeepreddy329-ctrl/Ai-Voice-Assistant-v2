# Email accounts and data ownership

The web app uses Supabase email magic links. The original desktop assistant is unchanged.

1. The browser calls `signInWithOtp` with an email address and the application's own origin as the return URL. Supabase sends a one-use sign-in link. The address must be verified; typing an email alone does not grant access.
2. The Supabase browser SDK receives and refreshes the session. API requests use its current access token. Old `nova-token` browser sessions and `/api/session` access codes are no longer accepted.
3. FastAPI asks the configured Supabase Auth server to validate each token. Only its returned UUID determines the account. Anonymous and unverified accounts are rejected. The client cannot choose another user's identity.
4. Records live in Supabase Postgres. Reads and deletes include the verified user ID; all requests also carry that user's JWT. Row-level policies independently enforce `auth.uid() = user_id` for reads, inserts and deletes. No service-role key is used.
5. Notes, memories, model context and visible conversation history survive new login sessions and API restarts. Each collection retains its newest 100 records. Model context uses the last 10 chat entries and last 5 memories. Generated code downloads in history remain private to the account.
6. Signing out clears visible content and the local SDK session. It leaves stored data intact. “Delete my saved data” deletes the signed-in account's records, not its Supabase account. A previously issued access JWT can remain valid until expiry; sign-out is not a promise of immediate token revocation.

## Secrets

- Supabase URL and **publishable** key (legacy `anon` key also supported) are public configuration. Both frontend and backend need them. NEVER use a `service_role` or Supabase secret key in the frontend or this adapter.
- `LLM_API_KEY` belongs only in the backend environment. Requests go only to the operator-configured HTTPS URL, without following redirects.
- `ACCESS_CODE`, `SESSION_SECRET`, and `DATABASE_PATH` are obsolete for the web backend.
- SDK tokens reside in browser storage; scripts on the same origin can read them. React renders responses as escaped text; no generated HTML is executed. Use only trusted frontend scripts and HTTPS.
- `ALLOWED_ORIGINS` contains exact frontend origins. CORS is not authentication.
- The service owner can access the database. AI questions, recent model context and saved memories go to the configured model provider. Browser speech services may process microphone audio; the API only receives the reviewed transcript.

## Operational limits

Keep one API worker/instance while request limits are in memory. Limits reset on restart and do not replace provider spending caps. Supabase enforces email rate limits; configure production SMTP before opening signups to external users. Enable provider abuse controls and monitor usage before wider promotion.

Old anonymous browser records cannot safely be assigned to an email automatically. Back up any existing SQLite database before rollout, preserve it outside this migration, and export needed notes before switching. Never bulk-assign old records to newly created accounts.

## Tests

Backend tests mock external Auth and model endpoints while checking verification, failures, user isolation, new sessions, history, deletion, limits and timezone behavior. Frontend tests cover sign-in states and account changes. Database tests execute the migration in a local PostgreSQL-compatible PGlite instance and check RLS, denied impersonation, deletion and retention. Real email delivery and real model replies remain deployment acceptance checks.
