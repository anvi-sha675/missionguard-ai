import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import api from "../api/client";

const MissionContext = createContext(null);

export function MissionProvider({ children }) {
  const [missionId, setMissionId] = useState("MISSION-001");
  const [spacecraftId, setSpacecraftId] = useState("SC-001");
  const [snapshot, setSnapshot] = useState(null); // { mission_health, risk, anomalies_detected, points_generated }
  const [lastScenario, setLastScenario] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getMissionStatus(missionId)
      .then(setSnapshot)
      .catch(() => setSnapshot(null));
  }, [missionId]);

  const runScenario = useCallback(
    async (params, detector = "isolation_forest") => {
      setLoading(true);
      setError(null);
      try {
        const payload = {
          mission_id: missionId,
          spacecraft_id: spacecraftId,
          ...params,
        };
        const result = await api.simulate(payload, detector);
        setSnapshot(result);
        setLastScenario(payload);
        return result;
      } catch (e) {
        setError(e?.response?.data?.detail || e.message || "Simulation failed");
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [missionId, spacecraftId],
  );

  const refreshSnapshot = useCallback(async () => {
    try {
      const anomalies = await api.getAnomalies(missionId);
      setSnapshot((prev) =>
        prev ? { ...prev, anomalies_detected: anomalies.length } : prev,
      );
      return anomalies;
    } catch {
      return [];
    }
  }, [missionId]);

  const value = {
    missionId,
    setMissionId,
    spacecraftId,
    setSpacecraftId,
    snapshot,
    setSnapshot,
    lastScenario,
    runScenario,
    refreshSnapshot,
    loading,
    error,
  };

  return (
    <MissionContext.Provider value={value}>{children}</MissionContext.Provider>
  );
}

export function useMission() {
  const ctx = useContext(MissionContext);
  if (!ctx) throw new Error("useMission must be used within MissionProvider");
  return ctx;
}
