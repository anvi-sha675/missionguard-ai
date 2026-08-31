# MissionGuard AI — IBM Granite Integration

## 1. Provider Architecture

`app/services/explain.py` defines an abstract `GraniteProvider` interface with two implementations:

- **`WatsonxGraniteProvider`** — makes real HTTP calls to IBM watsonx.ai.
- **`TemplateExplanationProvider`** — a deterministic, fully offline provider that implements the identical interface and follows the identical grounding structure, used when Granite is not configured or a live call fails.

`get_provider()` selects `WatsonxGraniteProvider` when `EXPLANATION_PROVIDER=watsonx` and both `GRANITE_API_KEY`/`GRANITE_PROJECT_ID` are set; otherwise it returns the template provider. A single instance is created once at startup (`app/api/deps.py`) and shared by every API route — there is no route in the codebase that instantiates a provider directly or duplicates an AI call.

Every AI-powered feature in the application goes through this one interface:

```
explain_anomaly()          -- anomaly explanation (Anomaly Center)
answer_copilot()            -- Mission Copilot answers
generate_recommendations()  -- recommendation cards
summarize_report()          -- report executive summary
explain_mission_plan()      -- Mission Planner narrative
explain_conjunction()       -- SSA conjunction narrative
```

## 2. What Granite Receives

The Granite layer never receives raw telemetry. It receives one of a small number of structured Pydantic objects, serialized to JSON:

- **`EvidencePackage`** (for `explain_anomaly`/`answer_copilot`) — contains the anomaly record, its top contributors, a forecast (if available), the current risk assessment, and pre-computed baseline-deviation statistics (`app/services/evidence.py`). It does not contain the full telemetry time series.
- **`MissionPlanEvaluation`** (for `explain_mission_plan`) — the already-computed per-constraint checks and overall verdict.
- **`ConjunctionEvent`** (for `explain_conjunction`) — the already-computed simulated closest-approach data.
- Free-text `mission_summary`/`context` strings (for `answer_copilot`/`summarize_report`), built from counts and labels already present in the store, not raw records.

Every prompt is prefixed with a fixed `GROUNDING_RULES` system message (defined once, at the top of `explain.py`) instructing the model to:

- never invent telemetry, sensor readings, or mission events,
- never fabricate certainty,
- distinguish observed facts from inferred causes,
- state when evidence is insufficient,
- never issue autonomous spacecraft commands,
- note that all recommendations require operator validation,
- and structure its answer as `OBSERVATION` / `LIKELY EXPLANATION` / `EVIDENCE` / `RISK` / `POSSIBLE IMPACT` / `RECOMMENDED ACTIONS` / `CONFIDENCE / LIMITATIONS`.

The `TemplateExplanationProvider` follows the same section structure using pre-written, evidence-interpolated text, so the contract the rest of the application relies on (an `ExplanationResponse` with these fields) is identical regardless of which provider is active.

## 3. Authentication Flow (implemented for real IBM Cloud IAM)

`WatsonxGraniteProvider._get_iam_token()` implements the correct IBM Cloud authentication flow for watsonx.ai: `GRANITE_API_KEY` is treated as an IBM Cloud IAM API key, which is exchanged for a short-lived Bearer access token via `POST https://iam.cloud.ibm.com/identity/token` before every Granite call. The token is cached in-process and automatically refreshed 60 seconds before its reported `expires_in` window closes, so repeated calls within an hour reuse one token rather than re-authenticating every time. This two-step exchange (API key → IAM token → Bearer header) reflects real IBM Cloud IAM behavior, not a guess.

## 4. The Actual Granite Request

`_call_granite()` calls IBM watsonx.ai's chat completions endpoint:

```
POST {GRANITE_URL}/ml/v1/text/chat?version=2024-05-01
Authorization: Bearer <IAM access token>
Content-Type: application/json

{
  "model_id": "<GRANITE_MODEL_ID>",
  "messages": [
    { "role": "system", "content": "<GROUNDING_RULES>" },
    { "role": "user", "content": "<evidence/context payload>" }
  ],
  "project_id": "<GRANITE_PROJECT_ID>",
  "parameters": { "max_new_tokens": 600, "temperature": 0.2 }
}
```

The combined prompt string is split on the first blank line into a `system` message (the grounding rules) and a `user` message (the evidence payload), so the model receives them in the correct chat roles rather than as one undifferentiated block of text.

## 5. Response Parsing

A real Granite chat response is `{"choices": [{"message": {"content": "..."}}]}`. `_call_granite()` extracts `choices[0].message.content` and raises a specific error (rather than a silent empty string) if `choices` is missing/empty or the content is blank.

The extracted text is then parsed by `_parse_structured_sections()`, which is deliberately tolerant of real-world LLM output variance:

- **JSON-first**: `_try_parse_json()` tries to parse the response as a JSON object (also stripping ` ```json ` / ` ``` ` markdown code fences if present), since models frequently return structured JSON even when asked for section-headed prose.
- **Key aliasing**: `_canonicalize_key()` maps common variant section names (`ASSESSMENT`→`RISK`, `RECOMMENDATION`/`RECOMMENDATIONS`→`RECOMMENDED ACTIONS`, `CONFIDENCE`/`LIMITATIONS`→`CONFIDENCE / LIMITATIONS`, `IMPACT`/`POTENTIAL IMPACT`→`POSSIBLE IMPACT`, etc.) onto the seven canonical section names, case-insensitively.
- **List-value joining**: if a JSON section's value is a list (e.g. a list of observation strings), it is joined into one newline-separated string.
- **Prose fallback**: if JSON parsing fails, a regex-based header scanner looks for the canonical/alias section names in plain text, tolerating `**bold**`, `*** headers ***`, trailing colons, and different casing.
- **Malformed input never raises**: unparseable text returns an empty `dict` rather than throwing, so a genuinely garbled response degrades to the "insufficient content" fallback path below instead of crashing the request.

`explain_anomaly()` additionally checks that at least one of the three primary fields (`OBSERVATION`, `LIKELY EXPLANATION`, `RISK`) was actually recovered before accepting the parsed result; if none were, it falls back to the template provider and labels the result `"... (fallback -- granite response could not be parsed)"` rather than returning a mostly-empty `ExplanationResponse`.

## 6. Fallback Behavior

Every `WatsonxGraniteProvider` method wraps its Granite call in a `try/except` and falls back to `TemplateExplanationProvider` on any failure — network error, timeout, HTTP error, malformed JSON, empty response, or an unparseable/insufficient response body. The fallback is always visibly labeled, never silently presented as a real Granite response:

- `explain_anomaly` sets `ExplanationResponse.provider` to a string containing `"fallback"` and the specific failure reason (e.g. `"... (fallback -- watsonx unavailable: HTTPError)"` or `"... (fallback -- granite response could not be parsed)"`).
- `answer_copilot`, `summarize_report`, `explain_mission_plan`, `explain_conjunction` prefix their returned text with `[AI service unavailable -- showing deterministic system analysis]`.
- `explain_conjunction` additionally always prefixes `[SIMULATED DATA]` onto whatever text is ultimately returned (Granite or fallback), because that label is a grounding requirement independent of which provider answered.
- Every fallback is logged via Python's `logging` module (`granite_call_failed method=... error=...` or `granite_parse_failed method=...`) so failures are visible in server logs without exposing secrets.

### Retry and timeout behavior

`_call_granite()` retries once with a short backoff on transient network-level errors (`URLError`/timeout), but does **not** retry on an HTTP 4xx client error (e.g. a bad API key), since retrying an unrecoverable auth failure only wastes time. The request timeout is configurable via `GRANITE_TIMEOUT_SECONDS` (default 20 seconds).

## 7. Configuration

```bash
EXPLANATION_PROVIDER=watsonx     # "template" (default) or "watsonx"
GRANITE_API_KEY=                 # IBM Cloud IAM API key
GRANITE_PROJECT_ID=              # watsonx.ai project id
GRANITE_URL=https://us-south.ml.cloud.ibm.com   # regional endpoint
GRANITE_MODEL_ID=ibm/granite-3-8b-instruct
GRANITE_TIMEOUT_SECONDS=20
```

Values are read once at import time in `app/core/config.py` (which also loads `backend/.env` if present via `python-dotenv`, without overriding real shell/CI environment variables). No credential has a real-looking default; `GRANITE_API_KEY`/`GRANITE_PROJECT_ID` default to empty strings, which causes `get_provider()` to select the template provider.

## 8. Honest Verification Status

This is the most important section of this document, and it is deliberately explicit:

- **The HTTP call, IAM authentication flow, request construction, and response parsing are real, implemented code** — not stubs. They correctly reflect IBM watsonx.ai's actual chat-completions API and IBM Cloud's actual IAM token-exchange flow.
- **The failure/fallback path has been re-verified against this exact code** (including the IAM token-exchange step) by running `WatsonxGraniteProvider.explain_anomaly()` with placeholder credentials from a network-restricted sandbox that does not allow-list `*.cloud.ibm.com`. The IAM token request to `https://iam.cloud.ibm.com/identity/token` is attempted first (before any watsonx call can happen) and is rejected by the sandbox's own egress restriction (HTTP 403 — not a response from IBM's servers). The provider correctly caught this, logged `granite_call_failed method=explain_anomaly error=HTTPError: ...`, and returned a result whose `provider` field reads `"... (fallback -- watsonx unavailable: HTTPError)"`. Unit tests in `tests/test_granite_fallback.py` further verify the fallback logic in isolation against simulated malformed JSON, empty responses, and empty message content, without needing network access.
- **A real successful Granite response has not been verified**, because that requires a real `GRANITE_API_KEY`, a real `GRANITE_PROJECT_ID`, and a network path to IBM's cloud that the development environment did not have.

**To complete verification**, run the backend with real credentials and network access, set `EXPLANATION_PROVIDER=watsonx`, and confirm via `GET /api/health` that `explanation_provider` reports `"ibm-granite (watsonx.ai)"` (not a `"fallback"`-labeled string) after a request that triggers an AI call, e.g. `GET /api/anomalies/{mission_id}/{anomaly_id}`.
