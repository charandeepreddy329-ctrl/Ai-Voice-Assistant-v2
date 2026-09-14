# Nova — Your ideas, amplified

A React + React Three Fiber voice workspace with a FastAPI backend, adapted from the supplied Nova desktop assistant.

## Repository

- `desktop/`: complete original macOS project and tests
- `frontend/`: Vite app, 3D orb, microphone transcript review, spoken replies, chat and downloads
- `backend/app/`: API, original assistant routing, calculator, scoped SQLite storage, model adapter
- `backend/tests/`: authentication, isolation, deletion, actions, request limits and calculator tests
- `render.yaml`: persistent Python API service
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
# Edit .env: generate unique SESSION_SECRET and ACCESS_CODE.
# Do not use the sample placeholder strings.
set -a
. ./.env
set +a
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Generate a signing secret with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`. Start your own Ollama service and pull the configured models, or configure a hosted provider as described in deployment docs. Built-in commands work without a model.

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Connect using your access code. Say “calculate 12 times 7”, “remember that I like green”, “show memory”, or “search YouTube for creative coding”.

The Vite development proxy forwards API requests to port 8000. Microphone recognition requires HTTPS or localhost and a compatible browser; unsupported browsers keep text chat available. Recording never auto-sends: stop, review, and press Send. Microphone permissions and audio playback depend on the browser/device.

```sh
cd backend && .venv/bin/pytest -q
cd ../frontend && npm run build
```

No model keys are included. Real model responses, microphone capture, and hosted deployment require your provider/browser configuration.
