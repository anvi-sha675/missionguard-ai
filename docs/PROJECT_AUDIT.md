# MissionGuard AI — Project Audit

_Concise engineering status as of this documentation pass. Based on direct inspection of the repository and re-running its test suite/build, not on assumption._

## Implemented Functionality

| Area                                       | Status                             | Notes                                                                                 |
| ------------------------------------------ | ---------------------------------- | ------------------------------------------------------------------------------------- |
| Telemetry simulation                       | Complete                           | 6 deterministic, seeded scenarios                                                     |
| Feature engineering                        | Complete                           | Full + compact feature sets for display vs. model fitting                             |
| Anomaly detection                          | Complete                           | 3 selectable detectors behind one interface                                           |
| Anomaly lifecycle (dedup, status workflow) | Complete                           | Hysteresis-based incident merging; operator-controlled status field                   |
| Forecasting                                | Complete                           | Linear trend, honest insufficient-data path                                           |
| Risk engine                                | Complete                           | Deterministic, weighted, explainable                                                  |
| Evidence grounding                         | Complete                           | Structured `EvidencePackage`, no raw telemetry passed to the AI layer                 |
| AI reasoning layer                         | Complete (code); not live-verified | See below                                                                             |
| Mission Copilot                            | Complete                           | Intent-routed to conjunctions / mission plan / general evidence Q&A                   |
| Mission Planner                            | Complete                           | 5 deterministic constraints, AI narrates only                                         |
| Space Situational Awareness                | Complete, explicitly simulated     | Labeled `SIMULATED` at the data model, API response, and AI-explanation level         |
| Reports                                    | Complete                           | AI-narrated executive summary + deterministic figures                                 |
| Frontend (7 pages)                         | Complete                           | Dashboard, Telemetry Explorer, Anomaly Center, Mission Planner, SSA, Copilot, Reports |
| Model evaluation                           | Complete                           | Real precision/recall/F1/FPR/latency + MAE/RMSE on fresh seeded runs                  |

## AI/ML Functionality

- Three real anomaly detectors (Isolation Forest, One-Class SVM, sklearn-MLP autoencoder) behind a shared, tested interface.
- Evaluation metrics are computed live from actual model predictions against simulator-known ground truth — never hardcoded.
- ML/deterministic code owns every number (anomaly score, risk score, forecast trend, feasibility verdict); the AI layer only explains already-computed results.

## Granite Integration

- Code-complete real IBM watsonx.ai integration: correct IBM Cloud IAM API-key-to-Bearer-token exchange, the current (non-deprecated) `/ml/v1/text/chat` endpoint, retry/timeout handling, and a response parser that tolerates JSON, markdown-fenced JSON, and prose with several real-world section-name variants.
- Every provider method has a tested, consistently-labeled fallback to a deterministic template provider on any failure (network, malformed response, empty response, unparseable content).
- **Not verified against a live successful IBM watsonx response** — the development environment this was built in has no network path to IBM's cloud. The failure/fallback path _has_ been verified against this exact code, including the IAM token-exchange step. Full detail and exact activation steps: `GRANITE_INTEGRATION.md` §8.

## Frontend Quality

- Consistent dark mission-control visual language across all 7 pages (shared `StatusPill`, `HealthGauge`, `TelemetryChart` components).
- Loading, empty, and error states present on every data-driven page (verified by inspection of each page component).
- No TypeScript; plain JS/JSX per the project's stated technology choice.
- No automated frontend test suite exists; frontend validation is limited to a successful production build (`npm run build`) and manual verification.

## Backend Quality

- Clean modular structure: one route file per feature area, one shared AI-provider singleton, clear separation between `ml/` (statistical/ML) and `services/` (deterministic business logic + AI orchestration).
- `python3 -m pyflakes app/ tests/` reports zero issues.
- Structured request logging middleware (request ID, method, path, status, duration) on every request.

## Testing Status

- **72 tests, 72 passing, 0 failing** at the time of this audit (`pytest tests/ -q`).
- Covers ML pipeline, risk engine, Mission Planner, SSA, every major API endpoint (including documented 404 cases), one full end-to-end integration test, the Granite fallback path, and the Granite response parser in isolation.
- No live-Granite-response test exists, for the reason stated above — this cannot be created without real credentials and network access.
- No frontend automated tests exist.

## Known Limitations

- **Data store is in-memory**, not a database. All state is lost on backend restart. `MONGODB_URI`/`MONGODB_DB` are defined in config but unused by any code path.
- **No authentication** is wired to any endpoint. `JWT_SECRET` exists as an inert placeholder for future work.
- **Space Situational Awareness is fully simulated**: a simplified geometric model, not a real orbital propagator (no SGP4) and not a real tracked-object catalog.
- **Mission Planner uses fixed prototype constants** (a 250W bus budget, fixed margin thresholds) — illustrative, not derived from real spacecraft engineering specifications.
- **Anomaly score bands and risk weights are prototype values**, explicitly documented as such, not certified operational standards.
- **No WebSocket/live streaming** — all telemetry access is request/response.
- **A minor known inconsistency**: the conjunction-explanation endpoint returns `{"error": "not found"}` with an HTTP 200 status rather than a proper HTTP 404, unlike the rest of the API's error convention. Documented in `API.md`; not corrected in this documentation-only pass since fixing it would touch application code.

## Security Considerations

- No secrets committed to the repository; `.gitignore` excludes `.env`; `.env.example` documents required variables with no real values.
- CORS restricted to explicitly configured origins by default; wildcard CORS requires an explicit opt-in (`CORS_ALLOW_ALL=true`) and is off by default.
- No API keys are ever sent to the frontend.
- All request bodies are validated via Pydantic models.
- The AI layer's grounding rules explicitly instruct against fabricated telemetry, fabricated confidence, and autonomous spacecraft commands; no endpoint in the codebase executes a spacecraft command of any kind.
- No authentication currently protects any endpoint — acceptable for a local/demo deployment, not for a publicly reachable production deployment without further work.

## Deployment Readiness

- Backend and frontend both start cleanly from a fresh checkout with the documented commands (`DEPLOYMENT.md`).
- No hardcoded `localhost` assumptions in production code paths — only environment-variable defaults and the Vite dev-server proxy (which is dev-only and absent from the production build).
- Both `/health` and `/api/health` respond correctly for use as a deployment liveness probe.
- **Not actually deployed to any hosting environment** as part of this work — "deployment readiness" here means the configuration is production-shaped (env-var driven, no hardcoded hosts), not that a live deployment has been performed or tested.

## Remaining Optional Improvements

- Persist state to a real database (MongoDB, per the collection names already implied by `store.py`'s structure, or any other store) instead of the in-memory dictionary.
- Wire authentication to the endpoints (the `JWT_SECRET` placeholder and dependency exist for this but nothing currently checks it).
- Verify a real, successful IBM watsonx/Granite response with live credentials and network access, and confirm the parser handles it correctly end-to-end.
- Replace the simulated SSA data with a real orbital propagator and/or public tracked-object catalog if genuine collision-avoidance functionality is desired beyond the current workflow demonstration.
- Fix the conjunction-explain endpoint's error-response inconsistency noted above.
