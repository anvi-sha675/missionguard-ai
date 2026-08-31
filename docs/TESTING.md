# MissionGuard AI — Testing

## Summary

```
cd backend && python3 -m pytest tests/ -q
```

**72 tests, 72 passed, 0 failed** (result of actually running the suite in this repository at the time this document was written).

| File                             | Tests | Covers                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| -------------------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_pipeline.py`         | 13    | Score-band boundaries, forecasting honesty (insufficient-data path, declining/flat trends), risk engine (zero-anomaly, severity scaling, criticality weighting), Mission Planner (unsafe-power case, safe case), SSA conjunction screening (determinism, `SIMULATED` labeling, risk classification), all three registered anomaly detectors running without error                                                                                                                                           |
| `tests/test_api.py`              | 18    | Every major REST endpoint via FastAPI's `TestClient` — health, telemetry simulate/fetch, mission status, anomaly list/detail/404, predictions/404, Copilot chat (including a no-conjunctions-screened case), report generation/404, Mission Planner evaluate/404, conjunction screening + explanation, spacecraft roster, model evaluation, and one full `test_full_pipeline_end_to_end` integration test covering telemetry → ML → risk → evidence → AI provider → Copilot → report as one continuous flow |
| `tests/test_granite_fallback.py` | 12    | Real, observable proof that the Granite unavailability path works: provider selection when credentials are present, clean fallback + correct labeling on a genuine network failure, visible fallback notices in Copilot/report text, malformed-JSON / empty-results / empty-generated-text response handling (each via a mocked transport), and retry-vs-no-retry behavior (4xx fails fast, transient errors retry once)                                                                                    |
| `tests/test_parser.py`           | 29    | The Granite response parser (`_parse_structured_sections`, `_try_parse_json`, `_canonicalize_key`, `_value_to_str`) in isolation: canonical and aliased section-name resolution (`ASSESSMENT`→`RISK`, `RECOMMENDATION`→`RECOMMENDED ACTIONS`, etc.), JSON responses with string and list-valued sections, markdown code-fence stripping, prose responses with plain/colon-suffixed/bold/triple-asterisk headers, and malformed/empty input handled without raising                                          |

## What Is and Isn't Covered

**Covered by automated tests:**

- ML anomaly detection (all three detectors), scoring, severity bands, contributor ranking
- Forecasting, including the "insufficient data" honesty path
- Risk engine arithmetic and subsystem-criticality weighting
- Mission Planner constraint evaluation
- Simulated conjunction screening and its data labeling
- Every REST endpoint's happy path and its documented 404 cases
- The Granite provider's failure/fallback behavior and response-parsing logic, including realistic LLM output variance (JSON vs. prose, markdown fences, aliased section names)
- One full end-to-end pipeline integration test

**Not covered by automated tests (and cannot be, from this repository alone):**

- A real, successful IBM watsonx/Granite API response — see `GRANITE_INTEGRATION.md` §8 for why, and what's needed to close this gap
- Frontend component/unit tests — there is no frontend test suite in this repository; frontend validation is limited to the production build succeeding (see below) and manual/visual verification during development
- Load, concurrency, or performance testing

## Frontend Build Validation

```
cd frontend && npm run build
```

This is a Vite production build, which fails on any JavaScript/JSX syntax error, unresolved import, or build-time issue. A successful build (`vite build` exits 0 and emits `dist/`) is the frontend-side check available in this repository — there is no Jest/Vitest/React Testing Library suite present.

## Linting

```
cd backend && python3 -m pyflakes app/ tests/
```

Reports unused imports, unused variables, and similar static issues across the entire backend application and test code.

## Manual/Functional Verification

The following have been exercised by actually running the backend and calling the endpoints (not merely reading the code), using the standard demo fixture (`scenario=battery_degradation`, `severity=75`, `duration_minutes=90`, `seed=42`):

- Telemetry simulation produces a detectable `WARNING`-band anomaly in the power subsystem
- The resulting risk assessment reaches `MEDIUM`/`HIGH` depending on severity
- Anomaly detail returns a grounded `ExplanationResponse` with a non-empty `observation` derived from the actual telemetry delta
- Mission Planner correctly returns `UNSAFE` for an activity requesting excessive power
- Conjunction screening returns simulated events all labeled `data_source: "SIMULATED"`
- Mission Copilot answers evidence-grounded questions about the active anomaly, conjunctions, and mission-plan feasibility
- Report generation returns a populated `MissionReport` with a limitations disclaimer

## Running Tests Yourself

```bash
cd backend
pip install -r requirements.txt
python3 -m pytest tests/ -v
```

No IBM credentials are required for any test in this suite — `test_granite_fallback.py` and `test_parser.py` use placeholder credentials and mocked/simulated transport specifically so the fallback and parsing logic can be verified without live network access or real API keys.
