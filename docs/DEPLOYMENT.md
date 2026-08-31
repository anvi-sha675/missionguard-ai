# MissionGuard AI — Running Locally / Deployment

## Prerequisites

- Python 3.12+ (backend)
- Node.js 18+ and npm (frontend)
- No database server required — the backend uses an in-memory store (see `ARCHITECTURE.md` §3)

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in values as needed (see Environment Variables below). `app/core/config.py` loads `backend/.env` automatically via `python-dotenv` if present; real shell/CI environment variables always take priority over `.env` file values.

Run the development server:

```bash
uvicorn app.main:app --reload --port 8000
```

Verify it's up:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/health
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on port 5173 by default and proxies any `/api/*` request to `http://localhost:8000` (configured in `vite.config.js`) — no manual CORS setup is needed for local development.

## Environment Variables

All variables are read by `backend/app/core/config.py`.

| Variable                     | Default                                      | Purpose                                                                          |
| ---------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------- |
| `EXPLANATION_PROVIDER`       | `template`                                   | `template` (offline, default) or `watsonx` (real Granite)                        |
| `GRANITE_API_KEY`            | _(empty)_                                    | IBM Cloud IAM API key — required only for `watsonx` mode                         |
| `GRANITE_PROJECT_ID`         | _(empty)_                                    | watsonx.ai project id — required only for `watsonx` mode                         |
| `GRANITE_URL`                | `https://us-south.ml.cloud.ibm.com`          | watsonx regional endpoint base URL                                               |
| `GRANITE_MODEL_ID`           | `ibm/granite-3-8b-instruct`                  | Model to call                                                                    |
| `GRANITE_TIMEOUT_SECONDS`    | `20`                                         | Per-request timeout for Granite calls                                            |
| `CORS_ORIGINS`               | `http://localhost:5173`                      | Comma-separated allowed frontend origin(s)                                       |
| `CORS_ALLOW_ALL`             | `false`                                      | Opt-in wildcard CORS; never set `true` in production                             |
| `JWT_SECRET`                 | placeholder                                  | **Inert** — no endpoint currently checks authentication (see `PROJECT_AUDIT.md`) |
| `MONGODB_URI` / `MONGODB_DB` | `mongodb://localhost:27017` / `missionguard` | **Defined but unused** — no code path reads these; the active store is in-memory |

**Never commit a real `.env` file.** `.gitignore` already excludes it; only `.env.example` (with no real values) should be committed.

## Development Commands

```bash
# backend
cd backend
uvicorn app.main:app --reload --port 8000    # dev server with autoreload
python3 -m pytest tests/ -v                   # run tests
python3 -m pyflakes app/ tests/                # lint

# frontend
cd frontend
npm run dev      # dev server
npm run build     # production build -> frontend/dist/
```

## Production Build

```bash
cd frontend && npm run build
```

Produces static assets in `frontend/dist/`, which can be served by any static file host or reverse proxy. The frontend calls relative `/api/...` paths (no hardcoded backend host), so in production the API must be reachable at `/api` relative to wherever the built frontend is served from — typically via a reverse proxy (e.g. nginx) routing `/api/*` to the FastAPI backend process.

The backend itself has no build step; run the same `uvicorn app.main:app` command (typically without `--reload`, and behind a process manager or an ASGI server like `uvicorn`/`gunicorn` with multiple workers) in a production environment.

## Configuration Checklist for a Non-Local Deployment

- Set `CORS_ORIGINS` to the actual deployed frontend origin (do not rely on the `http://localhost:5173` default)
- Leave `CORS_ALLOW_ALL` at `false` unless you have a specific reason to wildcard CORS
- Set `EXPLANATION_PROVIDER=watsonx` with real `GRANITE_API_KEY`/`GRANITE_PROJECT_ID` if live Granite explanations are desired (otherwise the app runs correctly on the deterministic template provider by default)
- The in-memory store means all mission/telemetry/anomaly state is lost on backend restart — this is expected behavior in the current build, not a bug (see `ARCHITECTURE.md` §3 and `PROJECT_AUDIT.md`)

## Health Checks

- `GET /health` and `GET /api/health` both return `{"status": "ok", "explanation_provider": "..."}` — either is suitable as a load-balancer/orchestrator liveness probe.

## Troubleshooting

| Symptom                                                                                                                 | Likely cause                                                                                                                               | Fix                                                                                                                          |
| ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| Frontend loads but API calls fail                                                                                       | Backend not running, or wrong port                                                                                                         | Confirm `uvicorn` is running on port 8000 and `vite.config.js`'s proxy target matches                                        |
| `GET /api/health` shows `explanation_provider: "template-offline..."` even though `EXPLANATION_PROVIDER=watsonx` is set | `GRANITE_API_KEY`/`GRANITE_PROJECT_ID` missing, or a live Granite call failed and fell back (check backend logs for `granite_call_failed`) | Verify both env vars are set; check logs for the specific failure reason                                                     |
| `pytest` import errors                                                                                                  | Run from the wrong directory                                                                                                               | Tests must be run from `backend/` — each test file inserts the parent directory onto `sys.path` relative to its own location |
| CORS errors in the browser console                                                                                      | `CORS_ORIGINS` doesn't include your frontend's actual origin                                                                               | Set `CORS_ORIGINS` to match exactly (scheme + host + port)                                                                   |
| Anomaly/report/predictions endpoints return 404                                                                         | No telemetry has been generated for that `mission_id` yet                                                                                  | Call `POST /api/telemetry/simulate` first                                                                                    |
