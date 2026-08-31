import { NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Radio,
  TriangleAlert,
  MessageSquareText,
  FileText,
  Satellite,
  Rocket,
  OrbitIcon,
  Cpu,
} from "lucide-react";
import { useMission } from "../store/MissionContext";
import StatusPill from "./StatusPill";
import api from "../api/client";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/telemetry", label: "Telemetry", icon: Radio },
  { to: "/anomalies", label: "Anomalies", icon: TriangleAlert },
  { to: "/planner", label: "Planner", icon: Rocket },
  { to: "/ssa", label: "SSA", icon: OrbitIcon },
  { to: "/copilot", label: "Copilot", icon: MessageSquareText },
  { to: "/reports", label: "Reports", icon: FileText },
];

function Clock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  const t = now.toISOString().slice(11, 19);
  return (
    <span className="mono text-xs text-[var(--color-muted)] tabular-nums">
      {t} UTC
    </span>
  );
}

function GraniteStatus() {
  const [info, setInfo] = useState(null);
  useEffect(() => {
    api
      .health()
      .then(setInfo)
      .catch(() => setInfo(null));
  }, []);

  if (!info) return null;

  const isLive =
    info.granite_configured &&
    !info.explanation_provider?.includes("fallback") &&
    !info.explanation_provider?.includes("template");

  return (
    <div
      className="flex items-center gap-1.5 px-2.5 py-1 rounded border"
      style={{
        borderColor: isLive
          ? "rgba(165,110,255,0.4)"
          : "var(--color-border-bright)",
        background: isLive ? "rgba(165,110,255,0.08)" : "transparent",
      }}
      title={`AI provider: ${info.explanation_provider}`}
    >
      <Cpu
        size={11}
        style={{ color: isLive ? "var(--color-purple)" : "var(--color-muted)" }}
      />
      <span
        className="mono text-[10px] tracking-wider"
        style={{ color: isLive ? "var(--color-purple)" : "var(--color-muted)" }}
      >
        {isLive ? "IBM GRANITE" : "OFFLINE AI"}
      </span>
      <span
        className="w-1.5 h-1.5 rounded-full pulse-dot"
        style={{
          background: isLive ? "var(--color-purple)" : "var(--color-dim)",
        }}
      />
    </div>
  );
}

export default function Layout({ children }) {
  const { missionId, spacecraftId, snapshot } = useMission();
  const overallStatus = snapshot
    ? snapshot.risk?.risk_level === "CRITICAL"
      ? "CRITICAL"
      : snapshot.risk?.risk_level === "HIGH"
        ? "WARNING"
        : snapshot.anomalies_detected > 0
          ? "MONITORING"
          : "NOMINAL"
    : "STANDBY";

  return (
    <div className="min-h-screen flex bg-[var(--color-bg)] console-grid">
      {/* nav rail */}
      <aside className="w-[76px] shrink-0 border-r border-[var(--color-border)] bg-[var(--color-panel)]/60 flex flex-col items-center py-5 gap-1">
        <div className="mb-6 flex flex-col items-center gap-1">
          <Satellite size={22} className="text-[var(--color-cyan)]" />
          <span className="mono text-[8px] text-[var(--color-dim)] tracking-widest">
            MG·AI
          </span>
        </div>
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `group flex flex-col items-center gap-1 w-16 py-2.5 rounded-md transition-colors ${
                isActive
                  ? "text-[var(--color-cyan)] bg-[var(--color-cyan)]/10"
                  : "text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-white/5"
              }`
            }
          >
            <Icon size={18} strokeWidth={1.75} />
            <span className="mono text-[9px] tracking-wide">{label}</span>
          </NavLink>
        ))}
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        {/* top bar */}
        <header className="h-14 shrink-0 border-b border-[var(--color-border)] bg-[var(--color-panel)]/80 backdrop-blur flex items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <div>
              <div className="mono text-sm font-bold tracking-[0.15em] text-[var(--color-text)]">
                MISSIONGUARD
                <span className="text-[var(--color-cyan)]">.AI</span>
              </div>
              <div className="mono text-[9px] text-[var(--color-dim)] tracking-wide">
                DECISION-SUPPORT PROTOTYPE — NOT FLIGHT-CERTIFIED
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <GraniteStatus />
            <div className="w-px h-6 bg-[var(--color-border)]" />
            <div className="flex items-center gap-2 mono text-xs">
              <span className="text-[var(--color-dim)]">MISSION</span>
              <span className="text-[var(--color-text)] font-semibold">
                {missionId}
              </span>
              <span className="text-[var(--color-border-bright)]">/</span>
              <span className="text-[var(--color-dim)]">SC</span>
              <span className="text-[var(--color-text)] font-semibold">
                {spacecraftId}
              </span>
            </div>
            <StatusPill status={overallStatus} size="lg" />
            <Clock />
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
