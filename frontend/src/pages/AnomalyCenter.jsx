import { useEffect, useState, useCallback } from "react";
import { X, Loader2, ChevronRight } from "lucide-react";
import { useMission } from "../store/MissionContext";
import StatusPill from "../components/StatusPill";
import {
  ContributorBars,
  AIExplanationPanel,
  GraniteProcessing,
} from "../components/Explainability";
import TelemetryChart from "../components/TelemetryChart";
import api from "../api/client";

const LIFECYCLE = [
  "NEW",
  "INVESTIGATING",
  "ACKNOWLEDGED",
  "MONITORING",
  "RESOLVED",
];

const SEVERITY_COLORS = {
  CRITICAL: "var(--color-red)",
  WARNING: "var(--color-amber)",
  LOW: "var(--color-cyan)",
  NORMAL: "var(--color-green)",
};

function ScoreBar({ score }) {
  const color =
    score >= 81
      ? "var(--color-red)"
      : score >= 61
        ? "var(--color-amber)"
        : score >= 31
          ? "var(--color-cyan)"
          : "var(--color-green)";
  return (
    <div className="flex items-center gap-2">
      <div className="score-bar-track w-16">
        <div
          style={{
            width: `${score}%`,
            background: color,
            height: "100%",
            transition: "width 0.4s ease",
          }}
        />
      </div>
      <span className="mono text-xs tabular-nums">{score}</span>
    </div>
  );
}

function AnomalyDetail({ missionId, anomalyId, onClose, onStatusChange }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [telemetry, setTelemetry] = useState([]);

  useEffect(() => {
    setLoading(true);
    setDetail(null);
    Promise.all([
      api.getAnomalyDetail(missionId, anomalyId),
      api.getTelemetry(missionId, 500),
    ])
      .then(([d, t]) => {
        setDetail(d);
        setTelemetry(t);
      })
      .finally(() => setLoading(false));
  }, [missionId, anomalyId]);

  const setStatus = async (status) => {
    await api.setAnomalyStatus(missionId, anomalyId, status);
    onStatusChange?.();
    setDetail((d) => (d ? { ...d, anomaly: { ...d.anomaly, status } } : d));
  };

  const anomalyParam = detail?.anomaly?.parameter;
  const chartThreshold = {
    battery_voltage: 25.0,
    temperature: 45.0,
    signal_strength: -85.0,
    fuel_level: 15.0,
  }[anomalyParam];

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60"
      onClick={onClose}
    >
      <div
        className="w-[600px] max-w-full h-full bg-[var(--color-panel)] border-l border-[var(--color-border)] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 bg-[var(--color-panel)] border-b border-[var(--color-border)] px-5 py-4 flex items-center justify-between">
          <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest">
            ANOMALY DETAIL · {anomalyId}
          </div>
          <button
            onClick={onClose}
            className="text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 px-8">
            <GraniteProcessing />
          </div>
        ) : !detail ? (
          <div className="p-6 text-sm text-[var(--color-red)]">
            Failed to load anomaly detail.
          </div>
        ) : (
          <div className="p-5 space-y-5">
            {/* Severity + score */}
            <div className="flex items-center gap-3">
              <StatusPill status={detail.anomaly.severity_band} size="lg" />
              <div className="mono text-xs text-[var(--color-muted)]">
                score{" "}
                <span
                  className="font-semibold"
                  style={{
                    color:
                      SEVERITY_COLORS[detail.anomaly.severity_band] ||
                      "var(--color-text)",
                  }}
                >
                  {detail.anomaly.anomaly_score}
                </span>
                /100 · confidence {(detail.anomaly.confidence * 100).toFixed(0)}
                %
              </div>
            </div>

            {/* Subsystem + parameter */}
            <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md px-4 py-3">
              <div className="text-sm font-semibold text-[var(--color-text)] uppercase tracking-wide">
                {detail.anomaly.subsystem}
              </div>
              <div className="text-xs text-[var(--color-muted)] mt-0.5">
                {detail.anomaly.parameter.replace(/_/g, " ")}
              </div>
              <div className="mono text-[10px] text-[var(--color-dim)] mt-1">
                {new Date(detail.anomaly.timestamp).toLocaleString()}
              </div>
            </div>

            {/* Telemetry mini-chart */}
            {telemetry.length > 0 && (
              <div>
                <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest mb-2">
                  TELEMETRY —{" "}
                  {(anomalyParam || "").replace(/_/g, " ").toUpperCase()}
                </div>
                <TelemetryChart
                  data={telemetry}
                  dataKey={anomalyParam}
                  threshold={chartThreshold}
                  anomalies={[detail.anomaly]}
                  height={180}
                />
              </div>
            )}

            {/* Anomaly contributors */}
            <div>
              <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest mb-2">
                ANOMALY CONTRIBUTORS
              </div>
              <ContributorBars contributors={detail.anomaly.contributors} />
            </div>

            {/* Lifecycle status */}
            <div>
              <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest mb-2">
                LIFECYCLE STATUS
              </div>
              <div className="flex items-center gap-1 flex-wrap">
                {LIFECYCLE.map((s, i) => {
                  const isActive = detail.anomaly.status === s;
                  const isPast = LIFECYCLE.indexOf(detail.anomaly.status) > i;
                  return (
                    <div key={s} className="flex items-center gap-1">
                      <button
                        onClick={() => setStatus(s)}
                        className={`mono text-[10px] px-2.5 py-1.5 rounded border tracking-wide transition-all ${
                          isActive
                            ? "border-[var(--color-cyan)] text-[var(--color-cyan)] bg-[var(--color-cyan)]/10"
                            : isPast
                              ? "border-[var(--color-green)]/40 text-[var(--color-green)] bg-[var(--color-green)]/5"
                              : "border-[var(--color-border-bright)] text-[var(--color-muted)] hover:text-[var(--color-text)] hover:border-[var(--color-border-bright)]"
                        }`}
                      >
                        {s}
                      </button>
                      {i < LIFECYCLE.length - 1 && (
                        <ChevronRight
                          size={10}
                          className="text-[var(--color-border-bright)]"
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Forecast */}
            {detail.forecast?.sufficient_data && (
              <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md p-3">
                <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest mb-2">
                  TREND FORECAST
                </div>
                <div className="grid grid-cols-3 gap-3 mono text-xs">
                  <div>
                    <div className="text-[var(--color-dim)]">TREND/HOUR</div>
                    <div className="text-[var(--color-text)] mt-1">
                      {detail.forecast.trend_per_hour > 0 ? "+" : ""}
                      {detail.forecast.trend_per_hour}
                    </div>
                  </div>
                  {detail.forecast.threshold != null && (
                    <div>
                      <div className="text-[var(--color-dim)]">THRESHOLD</div>
                      <div className="text-[var(--color-amber)] mt-1">
                        {detail.forecast.threshold}
                      </div>
                    </div>
                  )}
                  <div>
                    <div className="text-[var(--color-dim)]">EST. CROSSING</div>
                    <div className="text-[var(--color-text)] mt-1">
                      {detail.forecast.estimated_crossing_hours != null
                        ? `~${detail.forecast.estimated_crossing_hours}h`
                        : detail.forecast.note || "n/a"}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* AI Explanation Panel */}
            <div className="border-t border-[var(--color-border)] pt-4">
              <AIExplanationPanel explanation={detail.explanation} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AnomalyCenter() {
  const { missionId } = useMission();
  const [anomalies, setAnomalies] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [filter, setFilter] = useState("ALL");

  const load = useCallback(() => {
    setLoadingList(true);
    api
      .getAnomalies(missionId)
      .then(setAnomalies)
      .catch(() => setAnomalies([]))
      .finally(() => setLoadingList(false));
  }, [missionId]);

  useEffect(() => {
    load();
  }, [load]);

  const FILTERS = ["ALL", "CRITICAL", "WARNING", "LOW", "NORMAL"];
  const filtered =
    filter === "ALL"
      ? anomalies
      : anomalies.filter((a) => a.severity_band === filter);

  const criticalCount = anomalies.filter(
    (a) => a.severity_band === "CRITICAL",
  ).length;
  const warningCount = anomalies.filter(
    (a) => a.severity_band === "WARNING",
  ).length;

  return (
    <div className="space-y-4 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="mono text-sm tracking-widest text-[var(--color-dim)]">
            ANOMALY CENTER
          </h1>
          {anomalies.length > 0 && (
            <div className="mono text-[10px] text-[var(--color-muted)] mt-0.5">
              {anomalies.length} anomalies · {criticalCount} critical ·{" "}
              {warningCount} warning
            </div>
          )}
        </div>
        <div className="flex items-center gap-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`mono text-[10px] px-2.5 py-1.5 rounded border tracking-wide transition-colors ${
                filter === f
                  ? "border-[var(--color-cyan)] text-[var(--color-cyan)] bg-[var(--color-cyan)]/10"
                  : "border-[var(--color-border-bright)] text-[var(--color-muted)] hover:text-[var(--color-text)]"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg overflow-hidden">
        {loadingList ? (
          <div className="flex items-center justify-center py-20 gap-3">
            <Loader2
              size={18}
              className="animate-spin text-[var(--color-cyan)]"
            />
            <span className="mono text-xs text-[var(--color-dim)]">
              Loading anomalies…
            </span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-sm text-[var(--color-dim)] mono py-16 text-center">
            {filter === "ALL"
              ? "No anomalies recorded for this mission. Run a scenario from the Dashboard."
              : `No ${filter} anomalies.`}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="mono text-[10px] text-[var(--color-dim)] tracking-widest border-b border-[var(--color-border)]">
                <th className="text-left font-normal py-3 px-4">INCIDENT</th>
                <th className="text-left font-normal py-3 px-4">SUBSYSTEM</th>
                <th className="text-left font-normal py-3 px-4">PARAMETER</th>
                <th className="text-left font-normal py-3 px-4">TIMESTAMP</th>
                <th className="text-left font-normal py-3 px-4">SCORE</th>
                <th className="text-left font-normal py-3 px-4">SEVERITY</th>
                <th className="text-left font-normal py-3 px-4">STATUS</th>
                <th className="text-left font-normal py-3 px-4" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((a) => (
                <tr
                  key={a.id}
                  onClick={() => setSelected(a.id)}
                  className="border-b border-[var(--color-border)] last:border-0 hover:bg-white/5 cursor-pointer transition-colors"
                >
                  <td className="mono text-xs px-4 py-3 text-[var(--color-cyan)]">
                    {a.id}
                  </td>
                  <td className="px-4 py-3 uppercase text-xs font-medium">
                    {a.subsystem}
                  </td>
                  <td className="px-4 py-3 text-xs text-[var(--color-muted)]">
                    {a.parameter.replace(/_/g, " ")}
                  </td>
                  <td className="mono px-4 py-3 text-xs text-[var(--color-dim)]">
                    {new Date(a.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-4 py-3">
                    <ScoreBar score={a.anomaly_score} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusPill status={a.severity_band} />
                  </td>
                  <td className="mono px-4 py-3 text-[10px] text-[var(--color-muted)]">
                    {a.status}
                  </td>
                  <td className="px-4 py-3 text-[var(--color-dim)]">
                    <ChevronRight size={14} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <AnomalyDetail
          missionId={missionId}
          anomalyId={selected}
          onClose={() => setSelected(null)}
          onStatusChange={load}
        />
      )}
    </div>
  );
}
