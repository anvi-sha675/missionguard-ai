import StatusPill from "./StatusPill";

export function SubsystemGrid({ breakdown }) {
  const entries = Object.entries(breakdown || {});
  if (entries.length === 0) {
    return (
      <div className="text-sm text-[var(--color-dim)] mono py-6 text-center">
        No subsystem data yet — generate a telemetry scenario.
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-3">
      {entries.map(([subsystem, vals]) => {
        const risk = vals.subsystem_risk;
        const band =
          risk >= 80
            ? "CRITICAL"
            : risk >= 60
              ? "HIGH"
              : risk >= 30
                ? "MEDIUM"
                : "LOW";
        return (
          <div
            key={subsystem}
            className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md px-3 py-2.5 flex items-center justify-between"
          >
            <span className="mono text-xs uppercase tracking-wide text-[var(--color-text)]">
              {subsystem}
            </span>
            <StatusPill status={band} />
          </div>
        );
      })}
    </div>
  );
}

export function AlertsFeed({ anomalies }) {
  if (!anomalies || anomalies.length === 0) {
    return (
      <div className="text-sm text-[var(--color-dim)] mono py-6 text-center">
        No active alerts.
      </div>
    );
  }
  return (
    <div className="flex flex-col divide-y divide-[var(--color-border)]">
      {anomalies.map((a) => (
        <div
          key={a.id}
          className="py-2.5 flex items-center justify-between gap-3"
        >
          <div className="min-w-0">
            <div className="text-sm text-[var(--color-text)] truncate">
              {a.subsystem} — {a.parameter?.replace(/_/g, " ")}
            </div>
            <div className="mono text-[10px] text-[var(--color-dim)]">
              score {a.anomaly_score}/100 ·{" "}
              {new Date(a.timestamp).toLocaleTimeString()}
            </div>
          </div>
          <StatusPill status={a.severity_band} />
        </div>
      ))}
    </div>
  );
}
