import { useEffect, useState } from "react";
import { FileDown, Loader2, FileText } from "lucide-react";
import { useMission } from "../store/MissionContext";
import StatusPill from "../components/StatusPill";
import api from "../api/client";

function Section({ title, children, accent }) {
  return (
    <div className="border-t border-[var(--color-border)] pt-5 mt-5 first:border-0 first:pt-0 first:mt-0">
      <div
        className="mono text-[10px] tracking-widest mb-3"
        style={{ color: accent || "var(--color-dim)" }}
      >
        {title}
      </div>
      {children}
    </div>
  );
}

export default function Reports() {
  const { missionId } = useMission();
  const [report, setReport] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getReports(missionId)
      .then((h) => {
        setHistory(h);
        if (h.length) setReport(h[h.length - 1]);
      })
      .catch(() => {});
  }, [missionId]);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.generateReport(missionId);
      setReport(r);
      setHistory((h) => [...h, r]);
    } catch {
      setError(
        "No telemetry for this mission yet — generate a scenario on the Dashboard first.",
      );
    } finally {
      setLoading(false);
    }
  };

  const healthColor =
    report?.mission_health >= 80
      ? "var(--color-green)"
      : report?.mission_health >= 55
        ? "var(--color-amber)"
        : "var(--color-red)";

  return (
    <div className="space-y-5 max-w-[1000px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="mono text-sm tracking-widest text-[var(--color-dim)]">
            MISSION REPORT
          </h1>
          {history.length > 0 && (
            <div className="mono text-[10px] text-[var(--color-muted)] mt-0.5">
              {history.length} report{history.length !== 1 ? "s" : ""} generated
              for {missionId}
            </div>
          )}
        </div>
        <div className="flex gap-2">
          {report && (
            <button
              onClick={() => window.print()}
              className="flex items-center gap-2 border border-[var(--color-border-bright)] text-[var(--color-muted)] mono text-xs px-3 py-2 rounded hover:text-[var(--color-text)] transition-colors"
            >
              <FileDown size={14} /> EXPORT / PRINT
            </button>
          )}
          <button
            onClick={generate}
            disabled={loading}
            className="flex items-center gap-2 font-semibold mono text-xs px-4 py-2 rounded hover:brightness-110 disabled:opacity-50 transition-all"
            style={{ background: "var(--color-cyan)", color: "#051018" }}
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : null}
            {loading ? "GENERATING…" : "GENERATE REPORT"}
          </button>
        </div>
      </div>

      {error && (
        <div className="text-xs text-[var(--color-red)] bg-[var(--color-red)]/10 border border-[var(--color-red)]/30 rounded px-4 py-2.5">
          {error}
        </div>
      )}

      {!report ? (
        <div className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg flex flex-col items-center justify-center py-24 gap-3">
          <FileText size={28} className="text-[var(--color-dim)]" />
          <div className="text-sm text-[var(--color-dim)] mono text-center">
            No report generated yet for this mission.
            <br />
            Generate a scenario on the Dashboard first, then generate a report.
          </div>
        </div>
      ) : (
        <div className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg p-6">
          {/* Report header */}
          <div className="flex items-start justify-between mb-1">
            <div>
              <div className="text-lg font-semibold text-[var(--color-text)]">
                MissionGuard AI — Mission Health Report
              </div>
              <div className="mono text-[10px] text-[var(--color-dim)] mt-0.5">
                {report.mission_id} · generated{" "}
                {new Date(report.generated_at).toLocaleString()}
              </div>
            </div>
            <StatusPill status={report.risk_assessment.risk_level} size="lg" />
          </div>

          <Section title="EXECUTIVE SUMMARY">
            <p className="text-sm text-[var(--color-text)] leading-relaxed">
              {report.executive_summary}
            </p>
          </Section>

          <Section title="MISSION HEALTH">
            <div className="flex items-baseline gap-2">
              <span
                className="mono text-4xl font-semibold tabular-nums"
                style={{ color: healthColor }}
              >
                {report.mission_health}
              </span>
              <span className="text-sm text-[var(--color-dim)]">/ 100</span>
            </div>
            <div className="mt-2 score-bar-track w-48">
              <div
                style={{
                  width: `${report.mission_health}%`,
                  background: healthColor,
                  height: "100%",
                  transition: "width 0.6s ease",
                }}
              />
            </div>
          </Section>

          <Section title="ACTIVE ANOMALIES">
            {report.active_anomalies.length === 0 ? (
              <div className="text-sm text-[var(--color-green)]">
                No active anomalies — mission nominal.
              </div>
            ) : (
              <div className="space-y-2">
                {report.active_anomalies.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-center justify-between bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md px-3 py-2.5 text-sm"
                  >
                    <div>
                      <span className="font-medium">{a.subsystem}</span>
                      <span className="text-[var(--color-muted)]">
                        {" "}
                        — {a.parameter.replace(/_/g, " ")}
                      </span>
                    </div>
                    <StatusPill status={a.severity_band} />
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="SUBSYSTEM STATUS">
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(report.subsystem_status).map(([sub, band]) => (
                <div
                  key={sub}
                  className="flex items-center justify-between bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded px-3 py-2"
                >
                  <span className="mono text-xs uppercase">{sub}</span>
                  <StatusPill status={band} />
                </div>
              ))}
            </div>
          </Section>

          <Section title="RISK ASSESSMENT">
            <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="mono text-sm font-semibold">
                  {report.risk_assessment.risk_level}
                </div>
                <div className="mono text-xs text-[var(--color-muted)]">
                  score {report.risk_assessment.risk_score}/100
                </div>
              </div>
              <ul className="space-y-1">
                {report.risk_assessment.factors.map((f, i) => (
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
            </div>
          </Section>

          {report.forecasts.length > 0 && (
            <Section title="FORECASTS">
              <div className="grid grid-cols-2 gap-2">
                {report.forecasts.map((f, i) => (
                  <div
                    key={i}
                    className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md px-3 py-2.5 mono text-xs"
                  >
                    <div className="text-[var(--color-muted)] mb-1">
                      {f.parameter.replace(/_/g, " ")}
                    </div>
                    <div className="text-[var(--color-text)]">
                      {f.trend_per_hour > 0 ? "+" : ""}
                      {f.trend_per_hour}/hour
                    </div>
                    {f.estimated_crossing_hours && (
                      <div className="text-[var(--color-amber)] mt-0.5">
                        ~{f.estimated_crossing_hours}h to threshold
                      </div>
                    )}
                    {!f.estimated_crossing_hours && f.note && (
                      <div className="text-[var(--color-dim)] mt-0.5">
                        {f.note}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Section>
          )}

          <Section title="AI EXPLANATIONS" accent="var(--color-purple)">
            {report.ai_explanations.length === 0 ? (
              <div className="text-sm text-[var(--color-dim)]">None.</div>
            ) : (
              <div className="space-y-2 text-sm text-[var(--color-text)] leading-relaxed">
                {report.ai_explanations.map((e, i) => (
                  <p key={i} className="ai-section-card">
                    {e}
                  </p>
                ))}
              </div>
            )}
          </Section>

          <Section title="RECOMMENDED ACTIONS" accent="var(--color-green)">
            <ul className="space-y-2">
              {report.recommended_actions.map((a, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-[var(--color-text)]"
                >
                  <span
                    className="mono text-[10px] shrink-0 mt-0.5 px-1.5 py-0.5 rounded"
                    style={{
                      color: "var(--color-green)",
                      border: "1px solid rgba(70,211,138,0.3)",
                      background: "rgba(70,211,138,0.06)",
                    }}
                  >
                    {i + 1}
                  </span>
                  {a}
                </li>
              ))}
            </ul>
          </Section>

          <Section title="LIMITATIONS">
            <p className="text-xs text-[var(--color-muted)] leading-relaxed">
              {report.limitations}
            </p>
          </Section>
        </div>
      )}
    </div>
  );
}
