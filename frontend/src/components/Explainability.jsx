import { Cpu, CheckCircle2 } from "lucide-react";

export function GraniteBadge({ provider }) {
  if (!provider) return null;
  const isLive =
    provider.includes("ibm-granite") || provider.includes("watsonx");
  const isFallback =
    provider.includes("fallback") || provider.includes("template");

  if (isFallback) {
    return (
      <span className="mono text-[10px] text-[var(--color-dim)] border border-[var(--color-border-bright)] rounded px-2 py-0.5">
        OFFLINE AI · template provider
      </span>
    );
  }
  if (isLive) {
    return (
      <span className="granite-badge">
        <Cpu size={10} />
        IBM GRANITE · watsonx.ai
      </span>
    );
  }
  return (
    <span className="mono text-[10px] text-[var(--color-muted)]">
      {provider}
    </span>
  );
}

function AISection({ label, children, accent }) {
  return (
    <div className="ai-section-card">
      <div
        className="section-label mb-1.5"
        style={{ color: accent || "var(--color-dim)" }}
      >
        {label}
      </div>
      {children}
    </div>
  );
}

export function GraniteProcessing({ done = false }) {
  const STEPS = [
    "Reading anomaly evidence",
    "Correlating telemetry",
    "Generating assessment",
  ];
  const activeIdx = done ? STEPS.length : STEPS.length - 1;

  return (
    <div
      className="rounded-lg px-5 py-6 flex flex-col items-center gap-4"
      style={{
        background: "rgba(165,110,255,0.05)",
        border: "1px solid rgba(165,110,255,0.18)",
      }}
      role="status"
      aria-label={
        done ? "AI analysis complete" : "IBM Granite AI analysis in progress"
      }
    >
      {/* Spinning ring + IBM Granite label */}
      <div className="flex flex-col items-center gap-2">
        <div className="relative w-10 h-10 flex items-center justify-center">
          {/* background circle */}
          <svg className="absolute inset-0" viewBox="0 0 40 40" fill="none">
            <circle
              cx="20"
              cy="20"
              r="17"
              stroke="rgba(165,110,255,0.15)"
              strokeWidth="2"
            />
          </svg>
          {/* spinning arc — hidden when done */}
          {!done && (
            <svg
              className="absolute inset-0 granite-spin"
              viewBox="0 0 40 40"
              fill="none"
            >
              <circle
                cx="20"
                cy="20"
                r="17"
                stroke="var(--color-purple)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeDasharray="30 76"
              />
            </svg>
          )}
          {/* centre icon */}
          <Cpu
            size={16}
            style={{
              color: done ? "var(--color-green)" : "var(--color-purple)",
              flexShrink: 0,
            }}
          />
        </div>

        <div className="text-center">
          <div
            className="mono text-[11px] tracking-[0.15em] font-semibold"
            style={{
              color: done ? "var(--color-green)" : "var(--color-purple)",
            }}
          >
            IBM GRANITE
          </div>
          <div
            className="mono text-[10px] mt-0.5"
            style={{ color: "var(--color-muted)" }}
          >
            {done ? "Analysis complete" : "AI ANALYSIS IN PROGRESS"}
          </div>
        </div>
      </div>

      {/* Step list */}
      <div className="space-y-2 w-full max-w-[220px]">
        {STEPS.map((step, i) => {
          const isActive = !done && i === activeIdx;
          const isDone = done || i < activeIdx;
          return (
            <div key={step} className="flex items-center gap-2.5">
              {/* indicator */}
              {isDone ? (
                <CheckCircle2
                  size={13}
                  style={{ color: "var(--color-green)", flexShrink: 0 }}
                />
              ) : isActive ? (
                <span
                  className="step-active-dot shrink-0 w-[13px] h-[13px] rounded-full"
                  style={{
                    background: "var(--color-purple)",
                    display: "inline-block",
                  }}
                />
              ) : (
                <span
                  className="shrink-0 w-[13px] h-[13px] rounded-full"
                  style={{
                    background: "var(--color-border-bright)",
                    display: "inline-block",
                  }}
                />
              )}
              <span
                className="text-xs"
                style={{
                  color: isDone
                    ? "var(--color-green)"
                    : isActive
                      ? "var(--color-text)"
                      : "var(--color-dim)",
                }}
              >
                {isActive ? `${step}…` : step}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function AIExplanationPanel({ explanation }) {
  if (!explanation) return null;

  const {
    observation,
    likely_explanation,
    evidence,
    risk,
    possible_impact,
    recommended_actions,
    confidence_limitations,
    provider,
  } = explanation;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="section-label text-[var(--color-purple)]">
          AI INVESTIGATION
        </div>
        <GraniteBadge provider={provider} />
      </div>

      {observation && (
        <AISection label="OBSERVATION">
          <p className="text-sm text-[var(--color-text)] leading-relaxed">
            {observation}
          </p>
        </AISection>
      )}

      {likely_explanation && (
        <AISection label="LIKELY EXPLANATION" accent="var(--color-cyan)">
          <p className="text-sm text-[var(--color-text)] leading-relaxed">
            {likely_explanation}
          </p>
        </AISection>
      )}

      {evidence?.length > 0 && (
        <AISection label="EVIDENCE">
          <ul className="space-y-1">
            {evidence.map((e, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-[var(--color-muted)]"
              >
                <span className="text-[var(--color-cyan)] mt-0.5 shrink-0">
                  ›
                </span>
                {e}
              </li>
            ))}
          </ul>
        </AISection>
      )}

      {risk && (
        <AISection label="RISK" accent="var(--color-amber)">
          <p className="text-sm text-[var(--color-text)] leading-relaxed">
            {risk}
          </p>
        </AISection>
      )}

      {possible_impact && (
        <AISection label="POSSIBLE IMPACT" accent="var(--color-amber)">
          <p className="text-sm text-[var(--color-text)] leading-relaxed">
            {possible_impact}
          </p>
        </AISection>
      )}

      {recommended_actions?.length > 0 && (
        <AISection label="RECOMMENDED ACTIONS" accent="var(--color-green)">
          <ul className="space-y-1.5">
            {recommended_actions.map((action, i) => (
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
                {action}
              </li>
            ))}
          </ul>
        </AISection>
      )}

      {confidence_limitations && (
        <AISection label="CONFIDENCE / LIMITATIONS">
          <p className="text-xs text-[var(--color-muted)] leading-relaxed">
            {confidence_limitations}
          </p>
        </AISection>
      )}
    </div>
  );
}

export function ContributorBars({ contributors }) {
  if (!contributors || contributors.length === 0) return null;
  const max = Math.max(...contributors.map((c) => c.contribution));
  return (
    <div className="space-y-2">
      {contributors.map((c) => {
        const pct = Math.round((c.contribution / max) * 100);
        return (
          <div key={c.parameter} className="flex items-center gap-3">
            <span className="mono text-[10px] text-[var(--color-muted)] w-36 truncate uppercase">
              {c.parameter.replace(/_/g, " ")}
            </span>
            <div className="flex-1 score-bar-track">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${pct}%`,
                  background:
                    pct > 66
                      ? "var(--color-red)"
                      : pct > 33
                        ? "var(--color-amber)"
                        : "var(--color-cyan)",
                  transition: "width 0.4s ease",
                }}
              />
            </div>
            <span className="mono text-[10px] text-[var(--color-dim)] w-10 text-right">
              {(c.contribution * 100).toFixed(0)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function RecommendationCard({ card }) {
  return (
    <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md p-4">
      <div className="mono text-[10px] text-[var(--color-cyan)] tracking-widest mb-2">
        AI RECOMMENDATION
      </div>
      <div className="text-sm font-medium text-[var(--color-text)] mb-2">
        {card.title}
      </div>
      <div className="text-xs text-[var(--color-muted)] mb-1">
        <span className="text-[var(--color-dim)]">Reason: </span>
        {card.reason}
      </div>
      <div className="text-xs text-[var(--color-muted)] mb-3">
        <span className="text-[var(--color-dim)]">Expected objective: </span>
        {card.expected_objective}
      </div>
      <div className="flex items-center justify-between">
        <span className="mono text-[10px] text-[var(--color-amber)] flex items-center gap-1">
          ⚠ OPERATOR VALIDATION REQUIRED
        </span>
      </div>
    </div>
  );
}
