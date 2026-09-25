# Nova migration audit

The complete uploaded project was inspected on 2026-09-14, including actions.py, manifests, tests, and documentation. An unchanged copy is preserved in `desktop/`. The earlier web conversion has been reconciled against these files.

## Original architecture

CLI or PyQt6 GUI → Runtime → NovaAssistant command router → calculator, LocalStorage, OllamaLLM, DesktopActions. SpeechService uses SpeechRecognition with Google recognition and a local microphone, plus macOS `say` for output. LocalStorage appends notes, memories, commands, and conversation to JSONL files under ~/.nova-assistant. Ollama runs llama3.2:3b for chat and deepseek-r1:8b for reasoning/code. Runtime defaults to localhost:11434.

Confirmed desktop dependencies: Python >=3.11; ollama >=0.6,<1 and python-dotenv >=1.0,<2; optional PyQt6 >=6.7,<7, SpeechRecognition >=3.10,<4, PyAudio >=0.2.14,<1; macOS `say`; a running Ollama service with downloaded models. The web API uses FastAPI, Uvicorn, HTTPX and itsdangerous, without desktop GUI/audio packages.

## Web architecture

HTTPS browser (React/Vite) → HTTPS JSON API (FastAPI) → original command router → Supabase Postgres, safe calculator, structured browser actions, and model adapter.

React Three Fiber renders a procedurally generated point-cloud orb; animation reflects listening, thinking, and speech state. It loads separately from the main bundle, respects reduced-motion preference, and falls back to a CSS orb on render failure.

The original assistant.py, calculator.py and models.py are adapted directly. Storage, model transport, actions, UI and speech are replaced. Calculator input constants now have magnitude/finite checks as well as operation checks.

| Capability | Web behavior |
|---|---|
| Chat and reasoning | Ollama for local development; HTTPS OpenAI-compatible chat endpoint for hosting |
| Arithmetic | Original restricted AST calculator; no eval |
| Notes and memories | Supabase Postgres, scoped to verified email account UUID with row-level security; last 100 records per collection |
| Conversation context | Last 10 model messages and saved memories sent to model |
| Google/YouTube search | Clickable encoded search URLs; not scraped results |
| Approved sites | Seven explicit HTTPS destinations; no arbitrary server navigation |
| Python generation | Syntax-checked and downloaded as text; never executed on server |
| Time/date | Browser IANA timezone passed to server |
| Mac app launch | Explicit unavailable response |
| Microphone | Browser SpeechRecognition; user reviews transcript and sends |
| Spoken output | Browser speechSynthesis, opt-in, capped at 700 characters |
| Exit | Goodbye response; browser window stays open |

## Security and operating limits

Access code is entered by the visitor, never built into the frontend. The server issues a signed random visitor token with a 30-day expiry. Tokens are stored in browser localStorage; treat this as a small private workspace behind a public landing page, not full account authentication. A new browser/login gets a new identity. There is no cross-device account recovery, revocation list, or automatic deletion of expired identities. Delete saved data before disconnecting. For a large multi-user service add OIDC authentication, lifecycle cleanup, Redis rate limiting, and PostgreSQL before scaling.

Keys and signing secrets live only on the backend. Exact CORS origins control browser access; CORS is not authentication. Every chat/data route authenticates. Login and chat have in-process rate limits, chat has a global rate cap and four-request concurrency cap, and request bodies are bounded. Deploy one Uvicorn worker on one instance. Limits reset on restart and login IP limits may aggregate visitors behind the hosting proxy; global limits still apply. Configure provider-side spending limits as well.

Supabase provides storage independent of the API filesystem. Up to 100 entries per account and collection are retained. Verified accounts and row-level security separate users; monitor total storage and configure email abuse controls before broad exposure. Service owner has database access. User text, recent chat, and memories are transmitted to the configured model provider for AI answers. Speech processing may use the browser vendor's speech service. No raw microphone audio is uploaded to this API.

Do not expose a local Ollama port publicly. A public Render container cannot use Ollama on your laptop through localhost. Use a hosted compatible provider, or deploy private secured model infrastructure separately.
