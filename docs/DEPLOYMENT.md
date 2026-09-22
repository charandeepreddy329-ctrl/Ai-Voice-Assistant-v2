# Enable email login and AI

Existing production: https://ai-voice-assistant-v2.vercel.app/ and https://nova-voice-api.onrender.com.

Do not switch production to the email-login branch before the Supabase project, SQL migration, email delivery and AI provider are configured. The code intentionally refuses unauthenticated access when setup is missing; it does not fall back to the old shared code.

## 1. Supabase (owner setup)

Create a Supabase account and a project. Choose and store the database password yourself. Obtain the project HTTPS URL and **publishable** API key from the project settings. Neither the database password nor the service-role key is needed by this application.

In SQL Editor run `supabase/migrations/202609220001_accounts.sql` once. It creates a new table, strict per-user row policies and a 100-record retention trigger. It does not import or delete old SQLite data.

In Authentication URL Configuration set:

- Site URL: `https://ai-voice-assistant-v2.vercel.app/`
- Allowed redirect URL: `https://ai-voice-assistant-v2.vercel.app/`
- During development only: `http://localhost:5173/`

Keep Email enabled and anonymous sign-in disabled. Use the default magic-link template. Configure a custom SMTP provider and verified sender before public signup: Supabase's default mail service restricts recipients to project-team addresses and is not production email delivery. Enter SMTP credentials directly in Supabase, not in chat or GitHub. The application never needs them.

## 2. AI provider (owner setup)

Create an account with a provider offering an HTTPS chat-completions API. Select a chat model compatible with `messages` and `max_tokens`; not every reasoning model accepts this payload. Choose a spending limit and enter the API key directly in Render. A consumer chatbot subscription is not automatically an API account.

The adapter supports either hosted `compatible` inference or an explicitly configured Ollama host. Localhost Ollama on your computer is not reachable from a Render container.

## 3. Render environment

| Variable | Required value |
|---|---|
| `SUPABASE_URL` | Project HTTPS URL |
| `SUPABASE_PUBLISHABLE_KEY` | Publishable key, or legacy anon key; not service-role |
| `ALLOWED_ORIGINS` | `https://ai-voice-assistant-v2.vercel.app` |
| `LLM_PROVIDER` | `compatible` |
| `LLM_BASE_URL` | Provider API prefix, often ending `/v1`; the app appends `/chat/completions` |
| `LLM_API_KEY` | Secret provider key; backend only |
| `CHAT_MODEL` | Provider's exact compatible model ID |
| `REASONING_MODEL` | Optional separate code/reasoning model; leave unset to use CHAT_MODEL |
| `GLOBAL_REQUESTS_PER_MINUTE` | Start at `60`, lower if needed |

The blueprint uses a free Render instance and external Supabase storage; no disk or paid-plan upgrade is needed by this change. Existing hosting plans are not altered by editing the file. Free-service sleep can delay the first request. Keep one worker/instance because API request limits are in memory.

## 4. Vercel environment

Root Directory `frontend`, build `npm run build`, output `dist`, install `npm ci`.

| Variable | Required value |
|---|---|
| `VITE_API_URL` | `https://nova-voice-api.onrender.com` |
| `VITE_SUPABASE_URL` | Same project URL as Render |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Same publishable key as Render |

These values are embedded at build time. Redeploy after adding them. Never put the AI key, service-role key or database password in a `VITE_` variable.

## 5. Rollout and acceptance

1. Preserve existing SQLite data if any; old visitor identities have no verified email ownership and are not automatically migrated.
2. Test the feature branch locally with real project settings and two email accounts. If using a Vercel preview, explicitly allow its exact URL in Supabase and CORS.
3. Deploy the same reviewed commit to backend and frontend in a coordinated cutover. The old frontend cannot authenticate against the new backend.
4. Send and open an email link, sign out and sign back in. Confirm notes and conversation history return.
5. Use another account: the first account's notes, conversations and generated files must be absent.
6. Send a calculation, a real AI question and a Python-file request. Download and inspect code without executing it.
7. Restart the API and verify retained history. Check microphone transcript review and spoken replies in a supported browser over HTTPS.
8. Test deletion only with disposable data created for this check.

`/healthz` is liveness only. Authenticated `/api/model-status` reports whether settings are present, not a successful model connection. Only a real AI response verifies the provider.

Rollback: redeploy the previous frontend/backend commit pair and retain the old environment settings until rollout is accepted. The new Supabase table can remain intact. Do not delete user data during rollback.

## References

- https://supabase.com/docs/guides/auth/auth-email-passwordless
- https://supabase.com/docs/guides/auth/auth-smtp
- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://vercel.com/docs/frameworks/frontend/vite
- https://render.com/docs/configure-environment-variables
