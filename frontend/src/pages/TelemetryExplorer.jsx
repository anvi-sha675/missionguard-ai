import { useEffect, useState, useCallback } from "react";
import { Loader2, AlertTriangle } from "lucide-react";
import { useMission } from "../store/MissionContext";
import TelemetryChart from "../components/TelemetryChart";
import StatusPill from "../components/StatusPill";
import api from "../api/client";

const PARAMETERS = [
  {
    value: "battery_voltage",
    label: "Battery Voltage",
    unit: "V",
    threshold: 25.0,
    subsystem: "power",
  },
  {
    value: "battery_current",
    label: "Battery Current",
    unit: "A",
    subsystem: "power",
  },
  {
    value: "power_consumption",
    label: "Power Consumption",
    unit: "W",
    subsystem: "power",
  },
  {
    value: "solar_output",
    label: "Solar Output",
    unit: "W",
    subsystem: "power",
  },
  {
    value: "temperature",
    label: "Temperature",
    unit: "°C",
    threshold: 45.0,
    subsystem: "thermal",
  },
  {
    value: "signal_strength",
    label: "Signal Strength",
    unit: "dBm",
    threshold: -85.0,
    subsystem: "communication",
  },
  {
    value: "fuel_level",
    label: "Fuel Level",
    unit: "%",
    threshold: 15.0,
    subsystem: "navigation",
  },
  { value: "gyro_x", label: "Gyro X", unit: "rad/s", subsystem: "navigation" },
  { value: "gyro_y", label: "Gyro Y", unit: "rad/s", subsystem: "navigation" },
  { value: "gyro_z", label: "Gyro Z", unit: "rad/s", subsystem: "navigation" },
  { value: "cpu_usage", label: "CPU Usage", unit: "%", subsystem: "onboard" },
  {
    value: "memory_usage",
    label: "Memory Usage",
    unit: "%",
    subsystem: "onboard",
  },
  {
    value: "radiation_level",
    label: "Radiation Level",
    unit: "rad/h",
    subsystem: "onboard",
  },
];

const SUBSYSTEMS = [
  "power",
  "thermal",
  "communication",
  "navigation",
  "onboard",
];

export default function TelemetryExplorer() {
  const { missionId } = useMission();
  const [telemetry, setTelemetry] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [parameter, setParameter] = useState("battery_voltage");
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSubsystem, setActiveSubsystem] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, a] = await Promise.all([
        api.getTelemetry(missionId, 1000),
        api.getAnomalies(missionId),
      ]);
      setTelemetry(t);
      setAnomalies(a);
    } catch {
      setTelemetry([]);
      setAnomalies([]);
    } finally {
      setLoading(false);
    }
  }, [missionId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api
      .getPredictions(missionId, parameter)
      .then(setForecast)
      .catch(() => setForecast(null));
  }, [missionId, parameter]);

  const meta = PARAMETERS.find((p) => p.value === parameter);
  const current = telemetry.length
    ? telemetry[telemetry.length - 1][parameter]
    : null;
  const baseline = telemetry.length ? telemetry[0][parameter] : null;
  const delta = current != null && baseline != null ? current - baseline : null;

  // Anomalies relevant to the current parameter
  const paramAnomalies = anomalies.filter((a) => a.parameter === parameter);

  const filteredParams =
    activeSubsystem === "all"
      ? PARAMETERS
      : PARAMETERS.filter((p) => p.subsystem === activeSubsystem);

  // Determine if current parameter has active anomaly
  const hasAnomaly = paramAnomalies.length > 0;
  const worstAnomaly = hasAnomaly
    ? paramAnomalies.reduce((a, b) =>
        a.anomaly_score > b.anomaly_score ? a : b,
      )
    : null;

  return (
    <div className="space-y-4 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <h1 className="mono text-sm tracking-widest text-[var(--color-dim)]">
          TELEMETRY EXPLORER
        </h1>
        {loading && (
          <div className="flex items-center gap-2 text-[var(--color-dim)] mono text-xs">
            <Loader2 size={13} className="animate-spin" /> Loading…
          </div>
        )}
      </div>

      <div className="grid grid-cols-12 gap-5">
        {/* Parameter sidebar */}
        <div className="col-span-3 bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg p-4">
          <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest mb-3">
            PARAMETERS
          </div>

          {/* Subsystem filter */}
          <div className="flex flex-wrap gap-1 mb-3">
            <button
              onClick={() => setActiveSubsystem("all")}
              className={`mono text-[9px] px-2 py-1 rounded border transition-colors ${
                activeSubsystem === "all"
                  ? "border-[var(--color-cyan)] text-[var(--color-cyan)] bg-[var(--color-cyan)]/10"
                  : "border-[var(--color-border-bright)] text-[var(--color-muted)] hover:text-[var(--color-text)]"
              }`}
            >
              ALL
            </button>
            {SUBSYSTEMS.map((s) => (
              <button
                key={s}
                onClick={() => setActiveSubsystem(s)}
                className={`mono text-[9px] px-2 py-1 rounded border transition-colors ${
                  activeSubsystem === s
                    ? "border-[var(--color-cyan)] text-[var(--color-cyan)] bg-[var(--color-cyan)]/10"
                    : "border-[var(--color-border-bright)] text-[var(--color-muted)] hover:text-[var(--color-text)]"
                }`}
              >
                {s.toUpperCase()}
              </button>
            ))}
          </div>

          <div className="space-y-0.5">
            {filteredParams.map((p) => {
              const paramAnoms = anomalies.filter(
                (a) => a.parameter === p.value,
              );
              const worstBand = paramAnoms.length
                ? paramAnoms.reduce((a, b) =>
                    a.anomaly_score > b.anomaly_score ? a : b,
                  ).severity_band
                : null;
              return (
                <button
                  key={p.value}
                  onClick={() => setParameter(p.value)}
                  className={`w-full text-left px-3 py-2 rounded text-sm transition-colors flex items-center justify-between ${
                    parameter === p.value
                      ? "bg-[var(--color-cyan)]/10 text-[var(--color-cyan)]"
                      : "text-[var(--color-muted)] hover:bg-white/5 hover:text-[var(--color-text)]"
                  }`}
                >
                  <span>{p.label}</span>
                  {worstBand && (
                    <span className="shrink-0">
                      <StatusPill status={worstBand} />
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Main chart area */}
        <div className="col-span-9 space-y-4">
          {/* Current value header */}
          <div className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg p-4">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="text-sm font-medium text-[var(--color-text)]">
                  {meta.label}
                </div>
                <div className="mono text-[10px] text-[var(--color-dim)] mt-0.5">
                  {meta.subsystem?.toUpperCase()} SUBSYSTEM · SIMULATED
                  TELEMETRY
                </div>
              </div>
              <div className="text-right flex items-start gap-4">
                {hasAnomaly && (
                  <div className="flex items-center gap-1.5">
                    <AlertTriangle
                      size={14}
                      style={{
                        color:
                          worstAnomaly.severity_band === "CRITICAL"
                            ? "var(--color-red)"
                            : "var(--color-amber)",
                      }}
                    />
                    <StatusPill status={worstAnomaly.severity_band} />
                  </div>
                )}
                {current != null && (
                  <div>
                    <div
                      className="mono text-2xl font-semibold tabular-nums"
                      style={{
                        color: hasAnomaly
                          ? worstAnomaly.severity_band === "CRITICAL"
                            ? "var(--color-red)"
                            : "var(--color-amber)"
                          : "var(--color-cyan)",
                      }}
                    >
                      {current.toFixed(2)}{" "}
                      <span
                        className="text-sm"
                        style={{ color: "var(--color-dim)" }}
                      >
                        {meta.unit}
                      </span>
                    </div>
                    {delta != null && (
                      <div className="mono text-[10px] text-[var(--color-muted)]">
                        {delta >= 0 ? "+" : ""}
                        {delta.toFixed(2)} from baseline
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-24">
                <Loader2
                  size={18}
                  className="animate-spin text-[var(--color-cyan)]"
                />
              </div>
            ) : telemetry.length > 0 ? (
              <TelemetryChart
                data={telemetry}
                dataKey={parameter}
                threshold={meta.threshold}
                anomalies={paramAnomalies}
                height={300}
              />
            ) : (
              <div className="text-sm text-[var(--color-dim)] mono py-20 text-center">
                No telemetry loaded. Run a scenario from the Dashboard first.
              </div>
            )}

            {/* Threshold legend */}
            {meta.threshold != null && telemetry.length > 0 && (
              <div className="flex items-center gap-2 mt-2">
                <div
                  className="w-6 h-0.5"
                  style={{
                    background: "var(--color-amber)",
                    borderTop: "1px dashed",
                  }}
                />
                <span className="mono text-[10px] text-[var(--color-amber)]">
                  Warning threshold: {meta.threshold} {meta.unit}
                </span>
              </div>
            )}
          </div>

          {/* Forecast panel */}
          <div className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg p-4">
            <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest mb-3">
              TREND / FORECAST
            </div>
            {forecast ? (
              forecast.sufficient_data ? (
                <div className="grid grid-cols-4 gap-4 mono text-xs">
                  <div>
                    <div className="text-[var(--color-dim)] mb-1">CURRENT</div>
                    <div className="text-[var(--color-text)] text-sm font-medium">
                      {current != null
                        ? `${current.toFixed(2)} ${meta.unit}`
                        : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--color-dim)] mb-1">
                      TREND/HOUR
                    </div>
                    <div
                      className="text-sm font-medium"
                      style={{
                        color:
                          forecast.trend_per_hour < 0
                            ? "var(--color-red)"
                            : "var(--color-green)",
                      }}
                    >
                      {forecast.trend_per_hour > 0 ? "+" : ""}
                      {forecast.trend_per_hour}
                    </div>
                  </div>
                  {forecast.threshold != null && (
                    <div>
                      <div className="text-[var(--color-dim)] mb-1">
                        THRESHOLD
                      </div>
                      <div className="text-[var(--color-amber)] text-sm font-medium">
                        {forecast.threshold}
                      </div>
                    </div>
                  )}
                  <div>
                    <div className="text-[var(--color-dim)] mb-1">
                      EST. CROSSING
                    </div>
                    <div
                      className="text-sm font-medium"
                      style={{
                        color:
                          forecast.estimated_crossing_hours != null
                            ? "var(--color-amber)"
                            : "var(--color-text)",
                      }}
                    >
                      {forecast.estimated_crossing_hours != null
                        ? `~${forecast.estimated_crossing_hours}h`
                        : forecast.note || "n/a"}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-[var(--color-dim)]">
                  {forecast.note}
                </div>
              )
            ) : (
              <div className="text-sm text-[var(--color-dim)]">
                No forecast available for this parameter yet.
              </div>
            )}
          </div>

          {/* Active anomalies for this parameter */}
          {paramAnomalies.length > 0 && (
            <div className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg p-4">
              <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest mb-3">
                ACTIVE ANOMALIES — {meta.label.toUpperCase()}
              </div>
              <div className="space-y-2">
                {paramAnomalies.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-center justify-between bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md px-3 py-2"
                  >
                    <div>
                      <div className="mono text-[10px] text-[var(--color-cyan)]">
                        {a.id}
                      </div>
                      <div className="mono text-[10px] text-[var(--color-dim)] mt-0.5">
                        {new Date(a.timestamp).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="mono text-xs text-[var(--color-muted)]">
                        score {a.anomaly_score}/100
                      </span>
                      <StatusPill status={a.severity_band} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
