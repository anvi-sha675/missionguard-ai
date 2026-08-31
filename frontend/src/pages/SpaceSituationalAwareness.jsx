import { useEffect, useState, useCallback } from "react";
import { Satellite, Loader2, RefreshCw, AlertTriangle } from "lucide-react";
import { useMission } from "../store/MissionContext";
import StatusPill from "../components/StatusPill";
import api from "../api/client";

function Stat({ label, value, accent }) {
  return (
    <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md px-4 py-3">
      <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest mb-1">
        {label}
      </div>
      <div
        className="mono text-2xl font-semibold"
        style={{ color: accent || "var(--color-text)" }}
      >
        {value}
      </div>
    </div>
  );
}

function ConjunctionDetail({ event, explanation, loadingExplain }) {
  if (!event) return null;

  const riskColor =
    event.risk_level === "HIGH"
      ? "var(--color-red)"
      : event.risk_level === "MEDIUM"
        ? "var(--color-amber)"
        : "var(--color-green)";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-[var(--color-text)]">
            {event.object_name}
          </div>
          <div className="mono text-[10px] text-[var(--color-dim)] mt-0.5">
            {event.id}
          </div>
        </div>
        <StatusPill status={event.risk_level} size="lg" />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md p-2.5">
          <div className="mono text-[9px] text-[var(--color-dim)] tracking-widest mb-1">
            CLOSEST APPROACH
          </div>
          <div
            className="mono text-sm font-semibold"
            style={{ color: riskColor }}
          >
            {event.closest_approach_km} km
          </div>
        </div>
        <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md p-2.5">
          <div className="mono text-[9px] text-[var(--color-dim)] tracking-widest mb-1">
            TIME TO CA
          </div>
          <div className="mono text-sm font-semibold text-[var(--color-text)]">
            {event.time_to_closest_approach_hours}h
          </div>
        </div>
        <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md p-2.5">
          <div className="mono text-[9px] text-[var(--color-dim)] tracking-widest mb-1">
            REL. VELOCITY
          </div>
          <div className="mono text-sm font-semibold text-[var(--color-text)]">
            {event.relative_velocity_km_s} km/s
          </div>
        </div>
      </div>

      {event.risk_level === "HIGH" && (
        <div className="flex items-start gap-2 bg-[var(--color-red)]/8 border border-[var(--color-red)]/30 rounded-md px-3 py-2">
          <AlertTriangle
            size={14}
            className="shrink-0 mt-0.5"
            style={{ color: "var(--color-red)" }}
          />
          <div className="text-xs" style={{ color: "var(--color-red)" }}>
            HIGH-RISK conjunction. Operator review recommended before closest
            approach.
          </div>
        </div>
      )}

      <div className="border-t border-[var(--color-border)] pt-4">
        <div className="mono text-[10px] text-[var(--color-cyan)] tracking-widest mb-2">
          AI ASSESSMENT
        </div>
        {loadingExplain ? (
          <div className="flex items-center gap-2 text-[var(--color-dim)] text-sm py-2">
            <Loader2
              size={13}
              className="animate-spin text-[var(--color-cyan)]"
            />
            <span className="mono text-xs">Generating explanation…</span>
          </div>
        ) : explanation ? (
          <div className="text-sm text-[var(--color-text)] leading-relaxed">
            {explanation}
          </div>
        ) : null}
      </div>

      <div className="mono text-[9px] text-[var(--color-dim)] leading-relaxed">
        SIMULATED DATA — simplified geometric model, not a real orbital
        propagator or tracked-object catalog. Data source:{" "}
        {event.data_source || "SIMULATED"}
      </div>
    </div>
  );
}

export default function SpaceSituationalAwareness() {
  const { missionId, spacecraftId } = useMission();
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingExplain, setLoadingExplain] = useState(false);
  const [selected, setSelected] = useState(null);
  const [explanation, setExplanation] = useState(null);

  const load = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([
        api.getSpaceObjectSummary(),
        api.getConjunctions(missionId),
      ]);
      setSummary(s);
      setEvents(c);
    } catch {
      // ignore — no data yet
    }
  }, [missionId]);

  useEffect(() => {
    load();
  }, [load]);

  const screen = async () => {
    setLoading(true);
    setSelected(null);
    setExplanation(null);
    try {
      const c = await api.screenConjunctions(
        missionId,
        spacecraftId,
        Math.floor(Math.random() * 10000),
      );
      setEvents(c);
    } finally {
      setLoading(false);
    }
  };

  const openEvent = async (event) => {
    if (selected?.id === event.id) return; // already open
    setSelected(event);
    setExplanation(null);
    setLoadingExplain(true);
    try {
      // Use the axios client via the api object's base URL instead of raw fetch
      const res = await fetch(
        `/api/conjunctions/${missionId}/${event.id}/explain`,
      );
      const data = await res.json();
      setExplanation(data.explanation);
    } catch {
      setExplanation("Explanation unavailable.");
    } finally {
      setLoadingExplain(false);
    }
  };

  const high = events.filter((e) => e.risk_level === "HIGH").length;
  const medium = events.filter((e) => e.risk_level === "MEDIUM").length;
  const low = events.filter((e) => e.risk_level === "LOW").length;

  return (
    <div className="space-y-5 max-w-[1300px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="mono text-sm tracking-widest text-[var(--color-dim)]">
            SPACE SITUATIONAL AWARENESS
          </h1>
          <div className="mono text-[9px] text-[var(--color-amber)]/80 mt-0.5">
            SIMULATED DATA — simplified geometric model, not a real orbital
            propagator or tracked-object catalog
          </div>
        </div>
        <button
          onClick={screen}
          disabled={loading}
          className="flex items-center gap-2 font-semibold mono text-xs px-4 py-2.5 rounded hover:brightness-110 disabled:opacity-50 transition-all"
          style={{ background: "var(--color-cyan)", color: "#051018" }}
        >
          {loading ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <RefreshCw size={14} />
          )}
          {loading ? "SCREENING…" : "RUN CONJUNCTION SCREENING"}
        </button>
      </div>

      <div className="grid grid-cols-5 gap-4">
        <Stat
          label="TRACKED OBJECTS"
          value={summary?.tracked_objects?.toLocaleString() ?? "—"}
        />
        <Stat label="ACTIVE ALERTS" value={events.length} />
        <Stat
          label="HIGH RISK"
          value={high}
          accent={high > 0 ? "var(--color-red)" : undefined}
        />
        <Stat
          label="MEDIUM RISK"
          value={medium}
          accent={medium > 0 ? "var(--color-amber)" : undefined}
        />
        <Stat label="LOW RISK" value={low} accent="var(--color-green)" />
      </div>

      <div className="grid grid-cols-12 gap-5">
        {/* Event table */}
        <div className="col-span-7 bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg overflow-hidden">
          {events.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Satellite size={28} className="text-[var(--color-dim)]" />
              <div className="text-sm text-[var(--color-dim)] mono text-center">
                No conjunction screening run yet for this mission.
                <br />
                Run screening to detect nearby objects.
              </div>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="mono text-[10px] text-[var(--color-dim)] tracking-widest border-b border-[var(--color-border)]">
                  <th className="text-left font-normal py-3 px-4">OBJECT</th>
                  <th className="text-left font-normal py-3 px-4">
                    CLOSEST APPROACH
                  </th>
                  <th className="text-left font-normal py-3 px-4">
                    TIME TO CA
                  </th>
                  <th className="text-left font-normal py-3 px-4">
                    REL. VELOCITY
                  </th>
                  <th className="text-left font-normal py-3 px-4">RISK</th>
                </tr>
              </thead>
              <tbody>
                {events
                  .slice()
                  .sort((a, b) => {
                    const order = { HIGH: 0, MEDIUM: 1, LOW: 2 };
                    return (
                      (order[a.risk_level] ?? 3) - (order[b.risk_level] ?? 3)
                    );
                  })
                  .map((e) => (
                    <tr
                      key={e.id}
                      onClick={() => openEvent(e)}
                      className={`border-b border-[var(--color-border)] last:border-0 cursor-pointer transition-colors ${
                        selected?.id === e.id
                          ? "bg-[var(--color-cyan)]/5"
                          : "hover:bg-white/5"
                      }`}
                    >
                      <td className="px-4 py-3 text-xs font-medium text-[var(--color-text)]">
                        {e.object_name}
                      </td>
                      <td className="mono px-4 py-3 text-xs">
                        {e.closest_approach_km} km
                      </td>
                      <td className="mono px-4 py-3 text-xs">
                        {e.time_to_closest_approach_hours}h
                      </td>
                      <td className="mono px-4 py-3 text-xs">
                        {e.relative_velocity_km_s} km/s
                      </td>
                      <td className="px-4 py-3">
                        <StatusPill status={e.risk_level} />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Detail panel */}
        <div className="col-span-5 bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg p-5">
          {!selected ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-16 gap-3">
              <Satellite size={28} className="text-[var(--color-dim)]" />
              <div className="text-sm text-[var(--color-dim)]">
                Select a tracked object to see its AI assessment and orbital
                data.
              </div>
            </div>
          ) : (
            <ConjunctionDetail
              event={selected}
              explanation={explanation}
              loadingExplain={loadingExplain}
            />
          )}
        </div>
      </div>
    </div>
  );
}
