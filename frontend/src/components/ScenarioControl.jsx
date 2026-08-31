import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { useMission } from "../store/MissionContext";

const SCENARIOS = [
  { value: "normal", label: "Normal" },
  { value: "battery_degradation", label: "Battery Degradation" },
  { value: "thermal_anomaly", label: "Thermal Anomaly" },
  { value: "communication_anomaly", label: "Communication Anomaly" },
  { value: "sensor_anomaly", label: "Sensor Anomaly" },
  { value: "compound_anomaly", label: "Compound Anomaly" },
];

const DETECTORS = [
  { value: "isolation_forest", label: "Isolation Forest" },
  { value: "one_class_svm", label: "One-Class SVM" },
  { value: "autoencoder", label: "Autoencoder" },
];

export default function ScenarioControl({ onComplete }) {
  const { runScenario, loading } = useMission();
  const [scenario, setScenario] = useState("battery_degradation");
  const [severity, setSeverity] = useState(70);
  const [duration, setDuration] = useState(90);
  const [detector, setDetector] = useState("isolation_forest");

  const handleRun = async () => {
    const result = await runScenario(
      {
        scenario,
        severity,
        duration_minutes: duration,
        interval_seconds: 30,
        seed: 42,
      },
      detector,
    );
    onComplete?.(result);
  };

  return (
    <div className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg p-4">
      <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest mb-3">
        SIMULATED TELEMETRY SCENARIO
      </div>
      <div className="flex flex-wrap items-end gap-4">
        <div className="flex-1 min-w-[200px]">
          <label className="mono text-[10px] text-[var(--color-muted)] block mb-1.5">
            SCENARIO
          </label>
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="w-full bg-[var(--color-panel-raised)] border border-[var(--color-border-bright)] rounded px-3 py-2 text-sm text-[var(--color-text)] focus:border-[var(--color-cyan)] outline-none"
          >
            {SCENARIOS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        <div className="w-40">
          <label className="mono text-[10px] text-[var(--color-muted)] block mb-1.5">
            SEVERITY — {severity}
          </label>
          <input
            type="range"
            min="1"
            max="100"
            value={severity}
            onChange={(e) => setSeverity(Number(e.target.value))}
            className="w-full accent-[var(--color-cyan)]"
          />
        </div>

        <div className="w-32">
          <label className="mono text-[10px] text-[var(--color-muted)] block mb-1.5">
            DURATION (MIN)
          </label>
          <input
            type="number"
            min="5"
            max="1440"
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            className="w-full bg-[var(--color-panel-raised)] border border-[var(--color-border-bright)] rounded px-3 py-2 text-sm text-[var(--color-text)] focus:border-[var(--color-cyan)] outline-none"
          />
        </div>

        <div className="w-44">
          <label className="mono text-[10px] text-[var(--color-muted)] block mb-1.5">
            DETECTOR
          </label>
          <select
            value={detector}
            onChange={(e) => setDetector(e.target.value)}
            className="w-full bg-[var(--color-panel-raised)] border border-[var(--color-border-bright)] rounded px-3 py-2 text-sm text-[var(--color-text)] focus:border-[var(--color-cyan)] outline-none"
          >
            {DETECTORS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleRun}
          disabled={loading}
          className="flex items-center gap-2 bg-[var(--color-cyan)] text-[#051018] font-semibold mono text-xs tracking-wide px-4 py-2.5 rounded hover:brightness-110 disabled:opacity-50 transition"
        >
          {loading ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Play size={14} />
          )}
          {loading ? "GENERATING…" : "GENERATE TELEMETRY"}
        </button>
      </div>
    </div>
  );
}
