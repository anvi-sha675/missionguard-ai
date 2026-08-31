import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "var(--color-panel-raised)",
        border: "1px solid var(--color-border-bright)",
        borderRadius: 6,
        padding: "8px 12px",
        fontSize: 12,
        fontFamily: "var(--font-mono)",
      }}
    >
      <div style={{ color: "var(--color-muted)", marginBottom: 4 }}>
        {label}
      </div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.stroke || "var(--color-cyan)" }}>
          {p.name || p.dataKey}:{" "}
          {typeof p.value === "number" ? p.value.toFixed(3) : p.value}
        </div>
      ))}
    </div>
  );
}

export default function TelemetryChart({
  data,
  dataKey,
  anomalies = [],
  threshold,
  height = 280,
}) {
  const formatted = (data || []).map((d) => ({
    ...d,
    t: new Date(d.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
  }));

  // Build set of anomaly timestamps for fast lookup
  const anomalyTimes = new Set(
    (anomalies || []).map((a) =>
      new Date(a.timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    ),
  );

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart
        data={formatted}
        margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
      >
        <CartesianGrid
          stroke="var(--color-border)"
          strokeDasharray="3 3"
          vertical={false}
        />
        <XAxis
          dataKey="t"
          stroke="var(--color-dim)"
          tick={{ fontSize: 10, fontFamily: "var(--font-mono)" }}
          minTickGap={40}
        />
        <YAxis
          stroke="var(--color-dim)"
          tick={{ fontSize: 10, fontFamily: "var(--font-mono)" }}
          width={48}
        />
        <Tooltip content={<CustomTooltip />} />
        {threshold != null && (
          <ReferenceLine
            y={threshold}
            stroke="var(--color-amber)"
            strokeDasharray="4 4"
            label={{
              value: "threshold",
              fontSize: 10,
              fill: "var(--color-amber)",
              position: "insideTopRight",
            }}
          />
        )}
        <Line
          type="monotone"
          dataKey={dataKey}
          stroke="var(--color-cyan)"
          strokeWidth={1.8}
          dot={(props) => {
            const { cx, cy, payload } = props;
            if (anomalyTimes.has(payload.t)) {
              return (
                <circle
                  key={`dot-${cx}-${cy}`}
                  cx={cx}
                  cy={cy}
                  r={4}
                  fill="var(--color-red)"
                  stroke="var(--color-bg)"
                  strokeWidth={1.5}
                />
              );
            }
            return null;
          }}
          activeDot={{ r: 4, strokeWidth: 0 }}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
