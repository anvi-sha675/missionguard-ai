# MissionGuard AI — Documentation

This folder documents MissionGuard AI as it actually exists in this repository, verified by direct inspection and by re-running its test suite and build — not as an imagined future version. See the file index at the bottom for the detailed technical documents.

---

## Problem Statement

**Challenge: Advance Space Exploration with AI**

> Space exploration operates in some of the most complex and high-stakes environments, where decisions must be precise, data-rich, and often made with limited time and resources. Space-related challenges include managing and interpreting large volumes of satellite and mission data, ensuring the reliability and performance of spacecraft systems, navigating complex mission planning and coordination, and making space data more accessible to a broader audience. Despite vast amounts of available telemetry, satellite imagery, and sensor data, extracting actionable insights remains difficult.
>
> Your challenge is to build AI-powered solutions that help advance space exploration by improving mission success, enabling smarter decisions, and making space more accessible and understandable. Whether you're developing AI-powered mission planning assistants, predictive monitoring systems, data interpretation tools, decision-support platforms, or exploration and discovery applications, your solution should demonstrate how AI can transform space exploration from data-heavy to insight-driven systems. Projects should use AI as a core component and leverage IBM Bob as the primary development tool.

**Example solution areas named by the challenge:** AI-powered mission planning assistants, predictive spacecraft monitoring and anomaly detection, space debris tracking and collision avoidance systems, tools that translate complex space data into clear insights, AI systems supporting astronomy research, satellite data analysis platforms, space operations and decision-support systems, space education and public engagement tools.

**Questions the challenge asks builders to consider:** How can AI improve mission safety and reliability? How can AI make space data more usable and accessible? How can AI help scientists, engineers, and the public engage with space exploration? How can AI support better decision-making in complex environments? How can AI help transform space exploration from data-heavy to insight-driven systems?

Distilled to the specific problem MissionGuard AI addresses: **mission operators are flooded with raw spacecraft telemetry and have to manually spot the handful of readings that matter, reason through what they mean, assess the risk they pose, and decide what to do — under time pressure, across multiple subsystems and often multiple spacecraft at once.**

---

## Solution Description

MissionGuard AI turns that raw telemetry stream into mission intelligence through one consistent pipeline: **Detect → Explain → Predict → Assess → Recommend**, with a human operator kept in the loop at every step.

Concretely, the system:

- Simulates spacecraft telemetry across six scenarios (normal operation and five distinct fault types), deterministically and reproducibly
- Detects anomalies using a choice of three real machine-learning models, with a compact explainability layer showing which telemetry parameters drove each detection
- Forecasts near-term trends and, where the data supports it, estimates when a parameter will cross a warning threshold — explicitly refusing to guess when it doesn't have enough data
- Assesses mission risk with a deterministic, auditable formula that weighs anomaly severity, forecast trend, and subsystem criticality
- Explains and recommends via an AI reasoning layer (IBM Granite, with a fully offline deterministic fallback) that receives only pre-computed, structured evidence — never raw telemetry — so it explains the system's findings but never invents or overrides them
- Extends the same evidence-grounded approach to two further decision-support tools: a **Mission Planner** that deterministically checks whether a proposed spacecraft activity is feasible given current power, thermal, fuel, communication, and attitude constraints, and a **Space Situational Awareness** module that screens for simulated conjunction (close-approach) events
- Lets an operator investigate through a **Mission Copilot** that answers grounded questions about anomalies, risk, mission-plan feasibility, and conjunctions
- Generates a **Mission Report** summarizing mission health, anomalies, risk, forecasts, and recommended actions

Every AI-generated recommendation is explicitly flagged as requiring operator validation. No part of the system issues or is capable of issuing an autonomous spacecraft command.

---

## AI Approach and Architecture

MissionGuard AI draws a hard line between **what calculates** and **what explains**:

- **Machine learning and deterministic code calculate every number**: anomaly scores (Isolation Forest / One-Class SVM / a real small neural-network autoencoder, selectable), forecast trends (linear regression), risk scores (a fixed weighted formula), and mission-plan feasibility (rule-based constraint checks). None of these can be overridden by an LLM.
- **IBM Granite (via watsonx.ai) is the reasoning layer.** It receives a structured "evidence package" — never raw telemetry — built from the ML/deterministic layer's output, and turns it into grounded natural-language explanation, recommendations, Copilot answers, and report narratives, following an explicit system prompt that forbids inventing telemetry, fabricating confidence, or issuing spacecraft commands, and requires the response to be structured as OBSERVATION / LIKELY EXPLANATION / EVIDENCE / RISK / POSSIBLE IMPACT / RECOMMENDED ACTIONS / CONFIDENCE-LIMITATIONS.
- **A deterministic template provider** implements the identical interface and grounding structure entirely offline, so the application is fully demoable without live IBM credentials, and so any live-Granite failure falls back cleanly and visibly rather than crashing or silently serving something mislabeled.

Full technical detail: [`AI_ML.md`](./AI_ML.md) (the ML pipeline) and [`GRANITE_INTEGRATION.md`](./GRANITE_INTEGRATION.md) (the Granite integration, including its current, honestly-stated live-verification status).

---

## Selected Challenge Theme

**Space Exploration** — specifically the **predictive spacecraft monitoring and anomaly detection** solution area, with **space operations and decision-support** (Mission Planner, Mission Copilot) and **tools that translate complex space data into clear insights** (the evidence-grounded explanation layer, Mission Reports) as directly-supported secondary areas. A **space debris tracking** component (Space Situational Awareness) is included as a supporting feature, explicitly and consistently labeled as simulated data rather than a real collision-avoidance system.

| Challenge solution area                                     | MissionGuard AI component                                                     |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Predictive spacecraft monitoring and anomaly detection      | ML anomaly detection + forecasting                                            |
| Space operations and decision-support systems               | Deterministic risk engine, Mission Planner, human-in-the-loop recommendations |
| Tools that translate complex space data into clear insights | Evidence Builder + Granite-based explanation layer, Mission Reports           |
| Space debris tracking and collision avoidance systems       | Space Situational Awareness (explicitly simulated)                            |

---

## How IBM Bob Was Used

This section is written from what can actually be verified by inspecting this repository, since this assistant does not have access to IBM Bob and cannot itself observe a Bob development session in progress.

**Observable evidence in this repository:**

- A `.bob/` directory is present at the project root, containing `rules-agent`, `rules-ask`, and `rules-plan` configuration folders, each with an `AGENTS.md` file. These are IBM Bob project-configuration artifacts.
- The `rules-agent/AGENTS.md` file contains specific, accurate, codebase-level engineering notes (e.g. the exact reason `AutoencoderDetector.decision_scores()` returns a negated reconstruction error to satisfy a shared convention with the other detectors, the exact reason `store.save_telemetry()` replaces rather than appends prior runs, the exact test that enforces fallback labeling, and a correctly identified — and deliberately left alone — minor API inconsistency in the conjunction-explain endpoint). This reflects genuine, specific understanding of this codebase rather than generic boilerplate.
- Compared to the previous state of this project, the current repository contains meaningfully upgraded engineering in the Granite integration specifically: a correct IBM Cloud IAM API-key-to-Bearer-token exchange (`_get_iam_token()`), a switch from the legacy `/ml/v1/text/generation` endpoint to the current `/ml/v1/text/chat` endpoint with proper system/user role separation, and a substantially more robust response parser (JSON detection, markdown-fence stripping, section-name aliasing) backed by 29 new dedicated unit tests (`tests/test_parser.py`). This is exactly the kind of hardening pass a capable coding agent — or a careful engineer — would produce when asked to make the Granite integration production-ready.

**What this document does not claim:** it does not claim to have observed IBM Bob performing these specific edits, since no development log or session transcript is included in the delivered files this assistant inspected — only the resulting code and the `.bob/` configuration.

**Action needed from you before submission:** confirm directly (e.g. from your own Bob session history) which specific changes were made via IBM Bob, and state that plainly in this section with specifics (e.g. "IBM Bob was used to implement the IAM token-exchange fix and the response-parser hardening in `explain.py`, and to generate the accompanying test suite in `test_parser.py`"). Replace this paragraph with that confirmed account before submitting — a specific, accurate claim you can stand behind is stronger than this hedged one, and this hedge exists only because this assistant cannot independently verify authorship, not because the evidence is weak.

---

## Document Index

| File                                                 | Contents                                                                                           |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md)               | System architecture, data flow, backend/frontend structure, module-by-module walkthrough           |
| [`API.md`](./API.md)                                 | Every REST endpoint, with actual request/response shapes and error behavior                        |
| [`AI_ML.md`](./AI_ML.md)                             | The ML pipeline in detail — detectors, features, forecasting, risk formula, evaluation methodology |
| [`GRANITE_INTEGRATION.md`](./GRANITE_INTEGRATION.md) | The IBM Granite integration in detail, including its honest verification status                    |
| [`TESTING.md`](./TESTING.md)                         | What is tested, how, and actual current test results                                               |
| [`DEPLOYMENT.md`](./DEPLOYMENT.md)                   | Local setup, environment variables, production build, troubleshooting                              |
| [`PROJECT_AUDIT.md`](./PROJECT_AUDIT.md)             | Concise final engineering status: what's implemented, what's limited, what's left                  |
