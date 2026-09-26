# Google sign-in rollout for Nova

Google sign-in replaces email magic links in the current frontend. No SMTP sender or purchased domain is needed for this flow. The earlier email-delivery instructions in AUTHENTICATION.md apply only if email magic links are restored later.

## Account setup

The owner must complete Google Cloud first-use terms and any required two-step verification before the OAuth console is accessible. Keep billing disabled.

Use project `gen-lang-client-0600179988`. Configure an external Google OAuth application named Nova using only openid, email, and profile scopes. Create a Web application OAuth client with origin `https://ai-voice-assistant-v2.vercel.app` and redirect URI `https://uirfduauyywgidxetqbj.supabase.co/auth/v1/callback`. Store the client ID and client secret in Supabase Authentication > Sign In / Providers > Google, never in frontend code or GitHub. Keep nonce checking enabled. Testing mode requires explicitly added test users; public launch requires the appropriate production audience configuration.

## Completed Supabase preparation

On September 25, 2026, the existing account migration was applied successfully in the Supabase SQL editor. The production site URL and allowed redirect are both `https://ai-voice-assistant-v2.vercel.app/`. Do not re-run the create-table migration on that project.

## Hosting and validation

Before deploying the account branch, configure SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in Render, and VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY in Vercel. Keep provider secrets on their respective servers. The existing Gemini connection is verified on production with CHAT_MODEL and REASONING_MODEL set to gemini-3.5-flash-lite.

Verify Google sign-in, returned session, authenticated API requests, restored history, sign-out, and isolation between two accounts before replacing the live access-code application. Frontend tests mock OAuth; they do not establish a working provider connection. Keep the current live deployment until Google and hosting configuration are ready.
