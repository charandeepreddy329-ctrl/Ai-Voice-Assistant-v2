# Authentication and credential handling

## Original desktop application

The original project has no user login, passwords, OAuth, JWTs, or session tokens. `desktop/nova_assistant/config.py:Settings.load` reads model names, Ollama host, data directory and speech options from environment variables (optionally loaded by python-dotenv without overriding existing environment values). `desktop/nova_assistant/llm.py:OllamaLLM._get_client` constructs an Ollama client with a host and no explicit API credential. Its default is the local loopback service at port 11434. Local OS access is the effective trust boundary.

`runtime.py:build_runtime` wires Settings → JSONL LocalStorage → OllamaLLM → DesktopActions → NovaAssistant and SpeechService. CLI/GUI commands enter `NovaAssistant.handle`, then route to arithmetic, storage, desktop actions or model inference. `speech.py:listen` uses Google recognition without an application-supplied key; this does not make voice transcription local. No original JSONL data is included in this repository.

## Web components

| Component | Responsibility |
|---|---|
| `frontend/src/main.jsx:connect` | Sends the visitor-entered access code to POST /api/session over HTTPS |
| `backend/app/main.py:login` | Rate-limits attempts, compares SHA-256 digests with constant-time compare, creates a new random identity |
| `URLSafeTimedSerializer` | Signs that identity with SESSION_SECRET and salt nova-session-v1; includes issue time |
| `frontend/src/main.jsx:request` | Reads the token from app state and sends Authorization: Bearer on requests |
| `backend/app/main.py:identity` | Verifies signature and maximum age of 30 days before chat or deletion |
| `backend/app/storage.py:LocalStorage` | Scopes every query, insert, and deletion to the verified identity |
| `backend/app/llm.py:OllamaLLM._chat` | Sends the provider API key only to the server-configured HTTPS model endpoint |

## Request flow

1. The public frontend loads without authentication. GET /healthz is public and checks API health only.
2. Connect submits `{ "access_code": "visitor-entered value" }` to POST /api/session. ACCESS_CODE must be at least 12 characters, SESSION_SECRET at least 32; missing values fail startup.
3. An incorrect code returns 403. Successful login creates a fresh random 24-byte URL-safe identity and signs it. The access code is removed from React state after success and is not deliberately persisted by the application.
4. The browser saves the returned bearer token in localStorage under `nova-token`. This is a signed token, not a JWT or an encrypted payload. The payload holds a random identity, not model keys or user notes.
5. POST /api/chat verifies the token; limits message length, rate and concurrent work; constructs storage scoped to the identity; routes the command. Local commands need no model key. AI requests include recent chat and saved memories in the provider request.
6. The backend returns text and, where appropriate, an allowlisted HTTPS link or a syntax-checked Python download. Generated programs are never executed. The browser renders text with React escaping and uses optional browser speech synthesis.
7. DELETE /api/data deletes only the verified session's records. Disconnect removes the browser token and visible chat, but does not revoke that token or delete stored data. Expired/invalid tokens return 401 and the frontend prompts for reconnection.

## Secrets and boundaries

- `ACCESS_CODE`: shared workspace gate, backend environment only. Anyone who knows it can create an isolated session; this is not named-user account authentication.
- `SESSION_SECRET`: backend signing secret. Rotation invalidates all existing tokens and makes their old records inaccessible through newly created sessions. Keep it stable during routine deployments.
- `LLM_API_KEY`: backend environment only, used as a Bearer credential for LLM_PROVIDER=compatible. LLM_BASE_URL is controlled by the operator, never by visitor input. Redirects are not followed by the HTTPX client by default.
- `VITE_API_URL`: public backend origin, not a secret. Never put secrets in VITE_* variables; Vite embeds them in downloadable JavaScript.
- `ALLOWED_ORIGINS`: explicit frontend origins; CORS governs browsers and does not authenticate non-browser clients. Credentials are explicit Authorization headers, not automatically attached cookies.
- Browser microphone access requires HTTPS/localhost and user permission. Speech recognition may send audio to the browser vendor. The Nova API receives the reviewed text, not raw microphone recordings.
- LocalStorage tokens are readable by JavaScript on the frontend origin, so XSS could steal them. Avoid third-party scripts; for stronger account security migrate to OIDC and secure HttpOnly cookies with appropriate CSRF protection.
- Tokens cannot currently be individually revoked; changing ACCESS_CODE blocks new logins with the old code but does not invalidate already-issued sessions. There is no password reset, MFA, account recovery, or cross-device identity.
- In-process limits require one worker/instance, reset on restart, and are not a substitute for provider spending limits. SQLite needs a persistent disk for durable notes. The owner can access server data; it is not end-to-end encrypted.

## Verification

`backend/tests/test_api.py` covers missing and forged tokens, wrong access codes, token expiry, session isolation, deletion, CORS, message/body limits, throttling, and code-generation validation. Provider requests are mocked in tests; live model credentials must be configured and checked separately.
