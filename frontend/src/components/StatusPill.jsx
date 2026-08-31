const STYLES = {
  // Green — all-clear
  NORMAL:
    "text-[var(--color-green)] border-[var(--color-green)]/40 bg-[var(--color-green)]/10",
  NOMINAL:
    "text-[var(--color-green)] border-[var(--color-green)]/40 bg-[var(--color-green)]/10",
  SAFE: "text-[var(--color-green)] border-[var(--color-green)]/40 bg-[var(--color-green)]/10",
  HEALTHY:
    "text-[var(--color-green)] border-[var(--color-green)]/40 bg-[var(--color-green)]/10",
  RESOLVED:
    "text-[var(--color-green)] border-[var(--color-green)]/40 bg-[var(--color-green)]/10",

  // Cyan — low alert
  LOW: "text-[var(--color-cyan)] border-[var(--color-cyan)]/40 bg-[var(--color-cyan)]/10",
  MODERATE:
    "text-[var(--color-cyan)] border-[var(--color-cyan)]/40 bg-[var(--color-cyan)]/10",
  NEW: "text-[var(--color-cyan)] border-[var(--color-cyan)]/40 bg-[var(--color-cyan)]/10",

  // Amber — medium alert / in-progress states
  CONDITIONAL:
    "text-[var(--color-amber)] border-[var(--color-amber)]/40 bg-[var(--color-amber)]/10",
  MEDIUM:
    "text-[var(--color-amber)] border-[var(--color-amber)]/40 bg-[var(--color-amber)]/10",
  WARNING:
    "text-[var(--color-amber)] border-[var(--color-amber)]/40 bg-[var(--color-amber)]/10",
  HIGH: "text-[var(--color-amber)] border-[var(--color-amber)]/40 bg-[var(--color-amber)]/10",
  INVESTIGATING:
    "text-[var(--color-amber)] border-[var(--color-amber)]/40 bg-[var(--color-amber)]/10",
  ACKNOWLEDGED:
    "text-[var(--color-amber)] border-[var(--color-amber)]/40 bg-[var(--color-amber)]/10",
  MONITORING:
    "text-[var(--color-amber)] border-[var(--color-amber)]/40 bg-[var(--color-amber)]/10",

  // Red — critical
  CRITICAL:
    "text-[var(--color-red)] border-[var(--color-red)]/40 bg-[var(--color-red)]/10",
  UNSAFE:
    "text-[var(--color-red)] border-[var(--color-red)]/40 bg-[var(--color-red)]/10",

  // Muted — standby / unknown
  STANDBY:
    "text-[var(--color-muted)] border-[var(--color-border-bright)] bg-white/5",
  UNKNOWN:
    "text-[var(--color-muted)] border-[var(--color-border-bright)] bg-white/5",
};

export default function StatusPill({ status, size = "sm" }) {
  const key = status?.toUpperCase() || "UNKNOWN";
  const cls = STYLES[key] || STYLES.UNKNOWN;
  const sizeCls =
    size === "lg" ? "text-xs px-3 py-1.5" : "text-[10px] px-2 py-1";
  return (
    <span
      className={`mono inline-flex items-center gap-1.5 rounded border ${cls} ${sizeCls} font-semibold tracking-wider uppercase whitespace-nowrap`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current pulse-dot" />
      {status}
    </span>
  );
}
