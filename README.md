# MissionGuard AI 🚀

### AI-Powered Mission Operations & Decision Support Platform

MissionGuard AI is an AI-powered mission operations platform built for the **Space Exploration Challenge**. It transforms complex spacecraft telemetry into actionable mission insights using machine learning, predictive analytics, deterministic risk assessment, mission planning, simulated space-situational awareness, and an evidence-grounded AI Mission Copilot.

> **Hackathon Prototype:** MissionGuard AI uses simulated telemetry and space-object data. It is a decision-support system and does not autonomously control spacecraft.

---

## 🎯 Problem

Mission operators deal with large volumes of spacecraft telemetry and must quickly identify anomalies, understand their causes, assess mission risk, and determine appropriate actions.

MissionGuard AI turns this complex workflow into:

**Detect → Explain → Predict → Assess → Recommend**

---

## 💡 Solution

MissionGuard AI combines:

- 🛰️ **ML-powered anomaly detection**
- 📈 **Predictive telemetry forecasting**
- ⚠️ **Deterministic mission risk assessment**
- 🧭 **Mission activity feasibility analysis**
- 🌌 **Simulated space situational awareness**
- 🧠 **Evidence-grounded AI Mission Copilot**
- 📊 **Mission reporting and analytics**
- 🚀 **Multi-spacecraft Mission Control Dashboard**

The AI reasoning layer explains and contextualizes results calculated by the underlying ML and deterministic systems rather than independently generating mission-critical decisions.

---

## ✨ Key Features

### 🛰️ Predictive Spacecraft Monitoring

- Deterministic telemetry simulation
- Multiple spacecraft and mission scenarios
- Spacecraft health monitoring
- Battery, thermal, power, fuel, attitude, and communication analysis

### 🤖 ML Anomaly Detection

Supports multiple anomaly-detection approaches:

- Isolation Forest
- One-Class SVM
- Autoencoder using `MLPRegressor`

The system includes an evaluation pipeline for measuring detector performance on simulated ground truth.

### 📈 Predictive Analytics

Forecasts important telemetry parameters and identifies potential threshold crossings to support proactive mission monitoring.

### ⚠️ Mission Risk Assessment

A deterministic risk engine combines anomaly severity, telemetry trends, and subsystem criticality to produce mission risk assessments.

### 🧭 Mission Planner

Evaluates proposed mission activities against:

- Power
- Thermal conditions
- Fuel
- Communications
- Attitude constraints

The resulting feasibility assessment is deterministic, while the AI layer provides supporting explanation.

### 🌌 Space Situational Awareness

Provides simulated conjunction screening and collision-risk awareness.

> All space-object data in this prototype is explicitly labeled **SIMULATED**.

### 🧠 AI Mission Copilot

A tool-routed assistant that provides operational assistance using structured mission evidence.

It can work with:

- Spacecraft status
- Recent anomalies
- Forecasts
- Risk assessments
- Mission plans
- Conjunction information
- Recommendations

The Copilot does not directly access raw telemetry or storage.

### 📊 Mission Reports

Generates consolidated mission reports containing spacecraft health, anomalies, predictions, risk assessments, and recommendations.

---

## 🏗️ Architecture

```text
                    Telemetry Simulator
                           │
                           ▼
                  Feature Engineering
                           │
                           ▼
                ML Anomaly Detection
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
        Isolation      One-Class     Autoencoder
         Forest           SVM
             └─────────────┼─────────────┘
                           ▼
                  Predictive Analytics
                           │
                           ▼
                Deterministic Risk Engine
                           │
                           ▼
                    Evidence Builder
                           │
                           ▼
                   AI Reasoning Layer
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         Mission Planner  Copilot     Reports
                           │
                           ▼
                    FastAPI REST API
                           │
                           ▼
              React Mission Control UI
```

### Core Design Principle

**Critical calculations remain deterministic.**

Machine learning and deterministic services calculate anomaly scores, forecasts, risk assessments, and feasibility results.

The AI reasoning layer explains these results using structured evidence and does not independently generate mission-critical scores or execute spacecraft commands.

---

## 🛠️ Tech Stack

### Frontend

- React
- Vite
- Tailwind CSS
- Recharts
- React Router
- Axios
- Lucide Icons

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

### AI / ML

- scikit-learn
- NumPy
- Pandas
- IBM Granite / watsonx integration
- Deterministic fallback reasoning layer

### Testing

- Pytest
- FastAPI TestClient

---

## 📁 Project Structure

```text
missionguard-ai/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── ml/
│   │   └── services/
│   │
│   └── tests/
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       └── store/
│
└── docs/
    └── detailed documentation
```

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd missionguard-ai
```

### 2. Start the Backend

```bash
cd backend

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

### 3. Start the Frontend

Open another terminal:

```bash
cd frontend

npm install

npm run dev
```

The application will be available through the Vite development server.

---

## 🧪 Testing

Run the backend test suite:

```bash
cd backend

python -m pytest tests/ -v
```

Tests cover:

- ML anomaly detection
- Forecasting
- Risk assessment
- Mission planning
- Conjunction screening
- API endpoints
- End-to-end mission workflow
- AI provider fallback behavior

---

## 🎬 Demo Flow

A typical MissionGuard AI demonstration:

```text
1. Open Mission Control Dashboard
          ↓
2. Select spacecraft and telemetry scenario
          ↓
3. Generate simulated telemetry
          ↓
4. Observe spacecraft health changes
          ↓
5. Open Anomaly Center
          ↓
6. Inspect anomaly evidence and AI explanation
          ↓
7. Review predictions and mission risk
          ↓
8. Evaluate an activity using Mission Planner
          ↓
9. Run Space Situational Awareness screening
          ↓
10. Ask Mission Copilot operational questions
          ↓
11. Generate Mission Report
```

---

## 🔐 Human-in-the-Loop

MissionGuard AI is designed as a **decision-support system**, not an autonomous spacecraft control system.

- AI recommendations require operator validation.
- Critical calculations are performed by deterministic or ML components.
- No endpoint in this prototype executes spacecraft commands.

> **Operator validation required.**

---

## 📚 Documentation

Detailed technical documentation is available in the [`docs/`](docs/) directory, including:

- System architecture
- AI/ML pipeline
- IBM Granite integration
- Evaluation methodology
- API design
- Testing
- Limitations
- Future improvements

---

## ⚠️ Prototype Disclaimer

MissionGuard AI is a **hackathon prototype**.

Telemetry, mission scenarios, and space-object data are simulated and should not be interpreted as real spacecraft or orbital data. The system is not flight-certified and is not intended for autonomous spacecraft control.

---

## 👥 Team

**MissionGuard AI**

Built for the **Space Exploration Challenge**.
