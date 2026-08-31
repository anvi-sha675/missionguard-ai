import axios from "axios";

const client = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}/api`,
});

export const api = {
  health: () => client.get("/health").then((r) => r.data),

  simulate: (payload, detector = "isolation_forest") =>
    client
      .post("/telemetry/simulate", payload, { params: { detector } })
      .then((r) => r.data),

  getTelemetry: (missionId, limit = 500) =>
    client
      .get(`/telemetry/${missionId}`, { params: { limit } })
      .then((r) => r.data),

  getAnomalies: (missionId) =>
    client.get("/anomalies", { params: { mission_id: missionId } }).then((r) => r.data),

  getAnomalyDetail: (missionId, anomalyId) =>
    client.get(`/anomalies/${missionId}/${anomalyId}`).then((r) => r.data),

  setAnomalyStatus: (missionId, anomalyId, status) =>
    client
      .post(`/anomalies/${missionId}/${anomalyId}/status`, null, { params: { status } })
      .then((r) => r.data),

  getPredictions: (missionId, parameter) =>
    client
      .get(`/predictions/${missionId}`, { params: { parameter } })
      .then((r) => r.data),

  getMissionStatus: (missionId) =>
    client.get(`/missions/${missionId}/status`).then((r) => r.data),

  // spacecraft registry / command center
  listSpacecraft: () => client.get("/spacecraft").then((r) => r.data),

  // mission planner
  evaluateMissionPlan: (payload) =>
    client.post("/mission-planner/evaluate", payload).then((r) => r.data),
  getMissionPlanHistory: (missionId) =>
    client.get(`/mission-planner/${missionId}`).then((r) => r.data),

  // space situational awareness
  // space situational awareness
getSpaceObjectSummary: () =>
  client.get("/space-objects/summary").then((r) => r.data),

screenConjunctions: (missionId, spacecraftId, seed) =>
  client
    .post("/conjunctions/screen", null, {
      params: {
        mission_id: missionId,
        spacecraft_id: spacecraftId,
        seed,
      },
    })
    .then((r) => r.data),

getConjunctions: (missionId) =>
  client
    .get("/conjunctions", { params: { mission_id: missionId } })
    .then((r) => r.data),

explainConjunction: (missionId, conjunctionId) =>
  client
    .get(`/conjunctions/${missionId}/${conjunctionId}/explain`)
    .then((r) => r.data),

  // model evaluation
  evaluateModels: (scenario, severity, durationMinutes) =>
    client
      .get("/models/evaluate", { params: { scenario, severity, duration_minutes: durationMinutes } })
      .then((r) => r.data),

  getRecommendations: (missionId) =>
    client
      .get("/recommendations", { params: { mission_id: missionId } })
      .then((r) => r.data),

  copilotChat: (payload) =>
    client.post("/copilot/chat", payload).then((r) => r.data),

  copilotHistory: (missionId) =>
    client.get("/copilot/history", { params: { mission_id: missionId } }).then((r) => r.data),

  generateReport: (missionId) =>
    client
      .post("/reports/generate", null, { params: { mission_id: missionId } })
      .then((r) => r.data),

  getReports: (missionId) =>
    client.get(`/reports/${missionId}`).then((r) => r.data),
};

export default api;
