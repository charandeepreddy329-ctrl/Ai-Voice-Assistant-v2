# Nova — Your ideas, amplified

A React + React Three Fiber voice workspace with a FastAPI backend, adapted from the supplied Nova desktop assistant.

## Repository

- `desktop/`: complete original macOS project and tests
- `frontend/`: Vite app, 3D orb, microphone transcript review, spoken replies, chat and downloads
- `backend/app/`: API, original assistant routing, calculator, verified email accounts and Supabase storage, model adapter
- `backend/tests/`: authentication, isolation, deletion, actions, request limits and calculator tests
- `render.yaml`: Python API service with external persistent storage
- `.github/workflows/ci.yml`: API tests and production frontend build
- `docs/ARCHITECTURE.md`: source audit, capability mapping, limitations
- `docs/AUTHENTICATION.md`: credential handling and authenticated request flow
- `docs/DEPLOYMENT.md`: hosting and secrets walkthrough

## Run locally

Use Python 3.12 and Node 22.12+.

```sh
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env: configure Supabase and your AI provider.
# Do not use the sample placeholder strings.
set -a
. ./.env
set +a
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

First apply the Supabase migration and configure email redirects as described in `docs/DEPLOYMENT.md`. Configure hosted AI or explicitly use your local Ollama service. Built-in commands require email login and database access but do not require a model.

In another terminal:

```sh
cd frontend
npm ci
cp .env.example .env
# Add your Supabase URL and publishable key.
npm run dev
```

Open http://localhost:5173. Sign in using the link emailed to you. Say “calculate 12 times 7”, “remember that I like green”, “show memory”, or “search YouTube for creative coding”.

The Vite development proxy forwards API requests to port 8000. Microphone recognition requires HTTPS or localhost and a compatible browser; unsupported browsers keep text chat available. Recording never auto-sends: stop, review, and press Send. Microphone permissions and audio playback depend on the browser/device.

```sh
cd backend && .venv/bin/pytest -q
cd ../frontend && npm test && npm run build
```

No model keys are included. Real model responses, microphone capture, and hosted deployment require your provider/browser configuration.
