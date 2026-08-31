export default function HealthGauge({ value = 0, label = "MISSION HEALTH" }) {
  const pct = Math.max(0, Math.min(100, value));
  const color =
    pct >= 80
      ? "var(--color-green)"
      : pct >= 55
        ? "var(--color-cyan)"
        : pct >= 30
          ? "var(--color-amber)"
          : "var(--color-red)";

  // radial dial: 270 degree sweep, segmented ticks
  const radius = 74;
  const circumference = 2 * Math.PI * radius;
  const sweepFraction = 0.75; // 270 of 360 degrees
  const arcLength = circumference * sweepFraction;
  const dashOffset = arcLength * (1 - pct / 100);

  const ticks = Array.from({ length: 28 });

  return (
    <div className="relative flex items-center justify-center w-[200px] h-[200px]">
      <svg viewBox="0 0 200 200" className="w-full h-full -rotate-[135deg]">
        {/* tick marks */}
        {ticks.map((_, i) => {
          const angle = (i / (ticks.length - 1)) * 270 * (Math.PI / 180);
          const inner = 92;
          const outer = 98;
          const x1 = 100 + inner * Math.cos(angle);
          const y1 = 100 + inner * Math.sin(angle);
          const x2 = 100 + outer * Math.cos(angle);
          const y2 = 100 + outer * Math.sin(angle);
          const lit = i / (ticks.length - 1) <= pct / 100;
          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={lit ? color : "var(--color-border-bright)"}
              strokeWidth="2"
              opacity={lit ? 0.9 : 0.5}
            />
          );
        })}
        {/* track */}
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="8"
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeLinecap="round"
        />
        {/* value arc */}
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          style={{
            transition: "stroke-dashoffset 0.6s ease, stroke 0.6s ease",
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="mono text-4xl font-semibold tabular-nums"
          style={{ color }}
        >
          {pct.toFixed(0)}
        </span>
        <span className="mono text-[10px] text-[var(--color-muted)] tracking-widest mt-1">
          {label}
        </span>
      </div>
    </div>
  );
}
