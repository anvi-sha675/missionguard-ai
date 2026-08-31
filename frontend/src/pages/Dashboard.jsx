import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useMission } from "../store/MissionContext";
import ScenarioControl from "../components/ScenarioControl";
import HealthGauge from "../components/HealthGauge";
import { SubsystemGrid, AlertsFeed } from "../components/PanelWidgets";
import TelemetryChart from "../components/TelemetryChart";
import StatusPill from "../components/StatusPill";
import api from "../api/client";

function Panel({ title, children, action, accent }) {
  return (
    <div className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div
          className="mono text-[10px] tracking-widest"
          style={{ color: accent || "var(--color-dim)" }}
        >
          {title}
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}

function KpiCard({ label, value, subvalue, accent, dim }) {
  return (
    <div className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg px-4 py-3 flex-1 min-w-0">
      <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest mb-1 truncate">
        {label}
      </div>
      <div
        className="mono text-2xl font-semibold tabular-nums leading-tight"
        style={{ color: accent || "var(--color-text)" }}
      >
        {value}
      </div>
      {subvalue != null && (
        <div
          className="mono text-[10px] mt-0.5"
          style={{ color: dim || "var(--color-muted)" }}
        >
          {subvalue}
        </div>
      )}
    </div>
  );
}

function ScoreBar({ value, max = 100 }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const color =
    pct >= 80
      ? "var(--color-red)"
      : pct >= 60
        ? "var(--color-amber)"
        : pct >= 30
          ? "var(--color-cyan)"
          : "var(--color-green)";
  return (
    <div className="score-bar-track mt-1">
      <div
        style={{
          width: `${pct}%`,
          background: color,
          height: "100%",
          transition: "width 0.5s ease",
        }}
      />
    </div>
  );
}

export default function Dashboard() {
  const {
    missionId,
    setMissionId,
    spacecraftId,
    setSpacecraftId,
    snapshot,
    setSnapshot,
  } = useMission();
  const [telemetry, setTelemetry] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [fleet, setFleet] = useState([]);
  const [conjunctions, setConjunctions] = useState([]);
  const [_refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const [t, a, status, roster] = await Promise.all([
        api.getTelemetry(missionId, 300),
        api.getAnomalies(missionId),
        api.getMissionStatus(missionId),
        api.listSpacecraft(),
      ]);
      setTelemetry(t);
      setAnomalies(a);
      setSnapshot(status);
      setFleet(roster);
      try {
        setConjunctions(await api.getConjunctions(missionId));
      } catch {
        setConjunctions([]);
      }
    } catch {
      // no data yet for this mission — stay silent
    } finally {
      setRefreshing(false);
    }
  }, [missionId, setSnapshot]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const selectSpacecraft = (sc) => {
    setMissionId(sc.mission_id);
    setSpacecraftId(sc.spacecraft_id);
  };

  const health = snapshot?.mission_health ?? 100;
  const risk = snapshot?.risk;
  const riskScore = risk?.risk_score ?? 0;

  const criticalAnomalies = anomalies.filter(
    (a) => a.severity_band === "CRITICAL",
  ).length;
  const warningAnomalies = anomalies.filter(
    (a) => a.severity_band === "WARNING",
  ).length;

  const worstAnomaly = anomalies.length
    ? anomalies.reduce((a, b) => (a.anomaly_score > b.anomaly_score ? a : b))
    : null;
  const chartParam = worstAnomaly?.parameter || "battery_voltage";
  const chartLabel = chartParam.replace(/_/g, " ").toUpperCase();
  const chartThreshold = {
    battery_voltage: 25.0,
    temperature: 45.0,
    signal_strength: -85.0,
    fuel_level: 15.0,
  }[chartParam];

  const highConjunctions = conjunctions.filter(
    (c) => c.risk_level === "HIGH",
  ).length;

  const healthColor =
    health >= 80
      ? "var(--color-green)"
      : health >= 55
        ? "var(--color-amber)"
        : "var(--color-red)";

  const riskColor =
    risk?.risk_level === "CRITICAL"
      ? "var(--color-red)"
      : risk?.risk_level === "HIGH"
        ? "var(--color-red)"
        : risk?.risk_level === "MEDIUM"
          ? "var(--color-amber)"
          : "var(--color-green)";

  return (
    <div className="space-y-5 max-w-[1440px]">
      {/* KPI strip */}
      <div className="flex gap-3">
        <KpiCard
          label="SYSTEM HEALTH"
          value={`${health.toFixed(0)}%`}
          subvalue={`${snapshot?.points_generated ?? 0} telemetry pts`}
          accent={healthColor}
          dim="var(--color-muted)"
        />
        <KpiCard
          label="MISSION RISK"
          value={risk?.risk_level ?? "—"}
          subvalue={risk ? `score ${riskScore}/100` : "no data"}
          accent={riskColor}
        />
        <KpiCard
          label="ACTIVE ANOMALIES"
          value={anomalies.length}
          subvalue={`${criticalAnomalies} critical · ${warningAnomalies} warning`}
          accent={
            criticalAnomalies > 0
              ? "var(--color-red)"
              : warningAnomalies > 0
                ? "var(--color-amber)"
                : "var(--color-text)"
          }
        />
        <KpiCard
          label="CONJUNCTION ALERTS"
          value={conjunctions.length}
          subvalue={`${highConjunctions} high-risk`}
          accent={
            highConjunctions > 0 ? "var(--color-red)" : "var(--color-text)"
          }
        />
        <KpiCard
          label="FLEET SIZE"
          value={fleet.length || "—"}
          subvalue={
            fleet.length
              ? `${fleet.filter((s) => s.status !== "STANDBY").length} active`
              : "no spacecraft"
          }
          accent="var(--color-cyan)"
        />
      </div>

      {/* Fleet roster */}
      {fleet.length > 0 && (
        <Panel title="FLEET ROSTER">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2.5">
            {fleet.map((sc) => (
              <button
                key={sc.spacecraft_id}
                onClick={() => selectSpacecraft(sc)}
                className={`text-left bg-[var(--color-panel-raised)] border rounded-md px-3 py-2.5 transition-all ${
                  sc.spacecraft_id === spacecraftId
                    ? "border-[var(--color-cyan)] bg-[var(--color-cyan)]/5"
                    : "border-[var(--color-border)] hover:border-[var(--color-border-bright)]"
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="text-xs font-medium text-[var(--color-text)] truncate">
                    {sc.name}
                  </div>
                  <StatusPill status={sc.status} />
                </div>
                <div className="mono text-[9px] text-[var(--color-dim)] truncate">
                  {sc.spacecraft_id}
                </div>
                {sc.health != null && (
                  <>
                    <ScoreBar value={100 - sc.health} />
                    <div className="mono text-[9px] text-[var(--color-muted)] mt-0.5">
                      health {sc.health.toFixed(0)}%
                    </div>
                  </>
                )}
              </button>
            ))}
          </div>
        </Panel>
      )}

      {/* Scenario control */}
      <ScenarioControl onComplete={refresh} />

      {/* Main layout */}
      <div className="grid grid-cols-12 gap-5">
        {/* Left column: health gauge + subsystems */}
        <div className="col-span-3 space-y-4">
          <Panel title="OVERALL HEALTH">
            <div className="flex justify-center py-2">
              <HealthGauge value={health ?? 0} />
            </div>
          </Panel>
          <Panel title="SUBSYSTEM STATUS">
            <SubsystemGrid breakdown={risk?.subsystem_breakdown} />
          </Panel>
        </div>

        {/* Centre: telemetry chart + AI briefing */}
        <div className="col-span-6 space-y-4">
          <Panel title={`TELEMETRY — ${chartLabel}`}>
            {telemetry.length > 0 ? (
              <TelemetryChart
                data={telemetry}
                dataKey={chartParam}
                threshold={chartThreshold}
                anomalies={anomalies}
              />
            ) : (
              <div className="text-sm text-[var(--color-dim)] mono py-16 text-center">
                Run a telemetry scenario to populate the mission dashboard.
              </div>
            )}
          </Panel>

          <Panel
            title="AI MISSION BRIEFING"
            accent="var(--color-purple)"
            action={
              <Link
                to="/copilot"
                className="mono text-[10px] text-[var(--color-cyan)] hover:underline"
              >
                OPEN COPILOT →
              </Link>
            }
          >
            {anomalies.length > 0 ? (
              <div className="space-y-2">
                <div className="text-sm text-[var(--color-text)] leading-relaxed">
                  <span className="font-medium">{spacecraftId}</span> requires
                  attention. Highest severity:{" "}
                  <span
                    style={{
                      color:
                        worstAnomaly.severity_band === "CRITICAL"
                          ? "var(--color-red)"
                          : "var(--color-amber)",
                    }}
                  >
                    {worstAnomaly.severity_band}
                  </span>{" "}
                  anomaly in the{" "}
                  <span className="font-medium">{worstAnomaly.subsystem}</span>{" "}
                  subsystem (score{" "}
                  <span className="mono">{worstAnomaly.anomaly_score}/100</span>
                  ).
                  {highConjunctions > 0 && (
                    <>
                      {" "}
                      Additionally,{" "}
                      <span className="text-[var(--color-red)]">
                        {highConjunctions} HIGH-risk conjunction
                      </span>{" "}
                      alert{highConjunctions !== 1 ? "s" : ""} require review.
                    </>
                  )}
                </div>
                <div className="text-xs text-[var(--color-muted)]">
                  Open Anomaly Center for the full evidence-grounded IBM Granite
                  explanation and recommended actions.
                </div>
              </div>
            ) : (
              <div className="text-sm text-[var(--color-muted)]">
                {telemetry.length > 0
                  ? "No anomalies detected in the current telemetry window — mission nominal."
                  : "Generate a telemetry scenario to enable AI mission briefing."}
              </div>
            )}
          </Panel>
        </div>

        {/* Right column: alerts + recent events */}
        <div className="col-span-3 space-y-4">
          <Panel
            title="ACTIVE ALERTS"
            action={
              <Link
                to="/anomalies"
                className="mono text-[10px] text-[var(--color-cyan)] hover:underline"
              >
                VIEW ALL →
              </Link>
            }
          >
            <AlertsFeed anomalies={anomalies.slice(0, 6)} />
          </Panel>

          <Panel title="RECENT EVENTS">
            {telemetry.length === 0 && anomalies.length === 0 ? (
              <div className="text-xs text-[var(--color-dim)] mono text-center py-6">
                No events yet.
              </div>
            ) : (
              <div className="text-xs text-[var(--color-muted)] mono space-y-2 max-h-40 overflow-y-auto">
                {telemetry.length > 0 && (
                  <div className="flex gap-2">
                    <span className="text-[var(--color-dim)] shrink-0">
                      {new Date(telemetry[0].timestamp).toLocaleTimeString()}
                    </span>
                    <span>telemetry stream started</span>
                  </div>
                )}
                {anomalies.slice(0, 8).map((a) => (
                  <div key={a.id} className="flex gap-2">
                    <span className="text-[var(--color-dim)] shrink-0">
                      {new Date(a.timestamp).toLocaleTimeString()}
                    </span>
                    <span>
                      anomaly —{" "}
                      <span className="text-[var(--color-text)]">
                        {a.subsystem}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          {risk?.factors?.length > 0 && (
            <Panel title="RISK FACTORS">
              <ul className="space-y-1">
                {risk.factors.map((f, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-xs text-[var(--color-muted)]"
                  >
                    <span className="text-[var(--color-amber)] shrink-0 mt-0.5">
                      ›
                    </span>
                    {f}
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
