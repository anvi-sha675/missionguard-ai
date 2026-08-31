import { useState } from "react";
import {
  Rocket,
  Loader2,
  CheckCircle,
  XCircle,
  AlertCircle,
} from "lucide-react";
import { useMission } from "../store/MissionContext";
import StatusPill from "../components/StatusPill";
import api from "../api/client";

const DEFAULTS = {
  objective: "Earth Observation Pass",
  start_in_minutes: 10,
  duration_minutes: 18,
  required_power_w: 145,
  requires_communication: true,
  requires_attitude_maneuver: true,
  min_fuel_pct: 5,
  max_temperature_c: 50,
};

const STATUS_ICONS = {
  SAFE: <CheckCircle size={14} style={{ color: "var(--color-green)" }} />,
  UNSAFE: <XCircle size={14} style={{ color: "var(--color-red)" }} />,
  MODERATE: <AlertCircle size={14} style={{ color: "var(--color-amber)" }} />,
  CONDITIONAL: (
    <AlertCircle size={14} style={{ color: "var(--color-amber)" }} />
  ),
};

function CheckRow({ check }) {
  const statusColor =
    check.status === "SAFE"
      ? "var(--color-green)"
      : check.status === "UNSAFE"
        ? "var(--color-red)"
        : "var(--color-amber)";

  return (
    <div className="flex items-center justify-between py-2.5 border-b border-[var(--color-border)] last:border-0">
      <div className="min-w-0 pr-4 flex items-start gap-2.5">
        <div className="shrink-0 mt-0.5">
          {STATUS_ICONS[check.status] || null}
        </div>
        <div>
          <div className="text-sm text-[var(--color-text)]">
            {check.constraint}
          </div>
          <div className="text-xs mt-0.5" style={{ color: statusColor + "bb" }}>
            {check.detail}
          </div>
        </div>
      </div>
      <StatusPill status={check.status} />
    </div>
  );
}

export default function MissionPlanner() {
  const { missionId, spacecraftId } = useMission();
  const [form, setForm] = useState(DEFAULTS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const evaluate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.evaluateMissionPlan({
        mission_id: missionId,
        spacecraft_id: spacecraftId,
        ...form,
      });
      setResult(res);
    } catch (e) {
      setError(
        e?.response?.data?.detail ||
          "No telemetry for this mission yet — generate a scenario on the Dashboard first.",
      );
    } finally {
      setLoading(false);
    }
  };

  const inputCls =
    "w-full bg-[var(--color-panel-raised)] border border-[var(--color-border-bright)] rounded px-3 py-2 text-sm text-[var(--color-text)] focus:border-[var(--color-cyan)] outline-none transition-colors";

  return (
    <div className="space-y-5 max-w-[1200px]">
      <div>
        <h1 className="mono text-sm tracking-widest text-[var(--color-dim)]">
          MISSION PLANNER
        </h1>
        <div className="mono text-[9px] text-[var(--color-dim)] mt-0.5">
          Deterministic feasibility evaluation — not an autonomous go/no-go
          decision. Operator approval required.
        </div>
      </div>

      <div className="grid grid-cols-12 gap-5">
        {/* Form panel */}
        <div className="col-span-5 bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg p-5 space-y-4">
          <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest">
            PROPOSED ACTIVITY
          </div>

          <div>
            <label className="mono text-[10px] text-[var(--color-muted)] block mb-1.5">
              OBJECTIVE
            </label>
            <input
              value={form.objective}
              onChange={(e) => update("objective", e.target.value)}
              className={inputCls}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mono text-[10px] text-[var(--color-muted)] block mb-1.5">
                START IN (MIN)
              </label>
              <input
                type="number"
                value={form.start_in_minutes}
                onChange={(e) =>
                  update("start_in_minutes", Number(e.target.value))
                }
                className={inputCls}
              />
            </div>
            <div>
              <label className="mono text-[10px] text-[var(--color-muted)] block mb-1.5">
                DURATION (MIN)
              </label>
              <input
                type="number"
                value={form.duration_minutes}
                onChange={(e) =>
                  update("duration_minutes", Number(e.target.value))
                }
                className={inputCls}
              />
            </div>
            <div>
              <label className="mono text-[10px] text-[var(--color-muted)] block mb-1.5">
                REQUIRED POWER (W)
              </label>
              <input
                type="number"
                value={form.required_power_w}
                onChange={(e) =>
                  update("required_power_w", Number(e.target.value))
                }
                className={inputCls}
              />
            </div>
            <div>
              <label className="mono text-[10px] text-[var(--color-muted)] block mb-1.5">
                MIN FUEL (%)
              </label>
              <input
                type="number"
                value={form.min_fuel_pct}
                onChange={(e) => update("min_fuel_pct", Number(e.target.value))}
                className={inputCls}
              />
            </div>
          </div>

          <div className="flex items-center gap-6 pt-1">
            <label className="flex items-center gap-2 text-xs text-[var(--color-muted)] cursor-pointer">
              <input
                type="checkbox"
                checked={form.requires_communication}
                onChange={(e) =>
                  update("requires_communication", e.target.checked)
                }
                className="accent-[var(--color-cyan)]"
              />
              Requires communication
            </label>
            <label className="flex items-center gap-2 text-xs text-[var(--color-muted)] cursor-pointer">
              <input
                type="checkbox"
                checked={form.requires_attitude_maneuver}
                onChange={(e) =>
                  update("requires_attitude_maneuver", e.target.checked)
                }
                className="accent-[var(--color-cyan)]"
              />
              Requires attitude maneuver
            </label>
          </div>

          <button
            onClick={evaluate}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 font-semibold mono text-xs tracking-wide px-4 py-2.5 rounded hover:brightness-110 disabled:opacity-50 transition-all"
            style={{ background: "var(--color-cyan)", color: "#051018" }}
          >
            {loading ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Rocket size={14} />
            )}
            {loading ? "EVALUATING…" : "EVALUATE FEASIBILITY"}
          </button>

          {error && (
            <div className="text-xs text-[var(--color-red)] bg-[var(--color-red)]/10 border border-[var(--color-red)]/30 rounded px-3 py-2">
              {error}
            </div>
          )}
        </div>

        {/* Results panel */}
        <div className="col-span-7 bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg p-5">
          {!result ? (
            <div className="flex flex-col items-center justify-center h-full py-20 gap-3">
              <Rocket size={28} className="text-[var(--color-dim)]" />
              <div className="text-sm text-[var(--color-dim)] mono text-center">
                Evaluate a proposed activity to see its feasibility against
                current telemetry.
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Header */}
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-base font-semibold text-[var(--color-text)]">
                    {result.evaluation.objective}
                  </div>
                  <div className="mono text-[10px] text-[var(--color-dim)] mt-0.5">
                    MISSION FEASIBILITY ASSESSMENT
                  </div>
                </div>
                <div className="shrink-0">
                  <StatusPill status={result.evaluation.overall} size="lg" />
                </div>
              </div>

              <div className="mono text-[10px] text-[var(--color-muted)]">
                confidence {(result.evaluation.confidence * 100).toFixed(0)}%
              </div>

              {/* Constraint checks */}
              <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md px-4">
                <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest py-3 border-b border-[var(--color-border)]">
                  CONSTRAINT CHECKS
                </div>
                {result.evaluation.checks.map((c) => (
                  <CheckRow key={c.constraint} check={c} />
                ))}
              </div>

              {/* AI Narrative */}
              <div>
                <div
                  className="mono text-[10px] tracking-widest mb-2"
                  style={{ color: "var(--color-purple)" }}
                >
                  AI NARRATIVE
                </div>
                <div className="text-sm text-[var(--color-text)] leading-relaxed whitespace-pre-line ai-section-card">
                  {result.narrative}
                </div>
              </div>

              <div className="mono text-[9px] text-[var(--color-dim)]">
                This is a deterministic constraint evaluation, not an autonomous
                go/no-go decision. Operator approval required before any planned
                activity.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
