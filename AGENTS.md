# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Commands

```bash
# Backend (run from backend/)
uvicorn app.main:app --reload --port 8000
python3 -m pytest tests/ -v                        # all 40 tests
python3 -m pytest tests/test_pipeline.py -v        # unit tests only
python3 -m pytest tests/test_api.py -v             # API tests only
python3 -m pytest tests/test_granite_fallback.py -v # Granite fallback tests
python3 -m pytest tests/test_api.py::test_health_endpoint -v  # single test

# Frontend (run from frontend/)
npm run dev          # Vite dev server on :5173, proxies /api -> :8000
npm run build
npm run lint         # oxlint (not eslint)
```

## Critical Architecture Rules

- **AI layer sees ONLY the `EvidencePackage`** — never raw telemetry. `build_evidence()` in `app/services/evidence.py` is the sole gateway.
- **All numbers come from ML/deterministic engines** — the `GraniteProvider` explains them, never calculates them.
- `app/services/explain.py` → `get_provider()` returns one of two implementations sharing the `GraniteProvider` ABC: `WatsonxGraniteProvider` (real HTTP call, requires credentials) or `TemplateExplanationProvider` (offline default). The single module-level `provider` instance in `app/api/deps.py` is shared across all routes.
- Every Granite call falls back to `TemplateExplanationProvider` on failure. Fallback is always labeled — `result.provider` contains `"fallback"`. Never silently impersonate live Granite.
- `config.py` reads env vars **once at import time** — use `monkeypatch.setattr(config, "ATTR", val)` in tests, not `os.environ`, or the patched value won't take effect when other test files already imported config.

## Anomaly Score Scale

Bands are 0–30 = NORMAL, 31–60 = LOW, 61–80 = WARNING, 81–100 = CRITICAL (defined in `ANOMALY_BANDS` in `config.py`, used by `score_band()` in `ml/anomaly.py`).

## Data Store

`app/services/store.py` is a pure in-memory dict store (no MongoDB). `save_telemetry` **replaces** prior scenario data for a given `mission_id` (not appends). All mutation methods acquire `_lock` (threading.Lock). No persistence across server restarts.

## ML Detector Interface

All three detectors (`isolation_forest`, `one_class_svm`, `autoencoder`) follow the convention: `decision_scores()` returns **higher = more normal**. `raw_to_scores()` normalizes against the baseline window only and maps to 0–100. The model feature set is the compact `MODEL_PARAMS` (6 raw params + 3 derived per param = 18 cols), NOT the full `build_features()` output.

## Copilot Routing

`app/api/copilot.py::_route_question()` is a keyword-intent router — it checks for "conjunction", "maneuver"/"mission plan"/"feasib", then falls through to evidence-grounded anomaly Q&A. The Copilot never queries `store` directly; it only calls functions from `app/services/copilot_tools.py`.

## Frontend

- No TypeScript — plain `.jsx` throughout.
- Tailwind CSS v4 via `@tailwindcss/vite` plugin. Theme defined in `src/index.css` as `@theme` CSS variables (e.g. `var(--color-cyan)`). Use CSS variables for all colors, never raw hex.
- Global state via `MissionContext` (`src/store/MissionContext.jsx`). Use `useMission()` hook on every page.
- All API calls go through `src/api/client.js` — the axios instance uses `baseURL: "/api"`, which Vite proxies to `:8000`.
- Monospace font class is `mono` (mapped to IBM Plex Mono). Page labels and data readouts use `mono`.

## Environment Variables

Copy `backend/.env.example` to `backend/.env`. Key non-obvious defaults:

- `EXPLANATION_PROVIDER=template` (offline; flip to `watsonx` + supply 4 Granite vars to go live)
- `CORS_ALLOW_ALL=false` — **do not set true in production**
- `JWT_SECRET` is currently inert — no endpoint checks auth

## Testing Notes

- Tests must be run from `backend/` directory (not project root) — `sys.path.insert` in each test file adds `..` relative to `tests/`.
- `test_granite_fallback.py` monkeypatches config attributes directly (see note above about import-time reads).
- `test_full_pipeline_end_to_end` in `test_api.py` uses `mission_id="INTEGRATION-TEST-MISSION"` to avoid colliding with other tests sharing `"API-TEST-MISSION"`.
