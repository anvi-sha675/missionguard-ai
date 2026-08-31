import { useEffect, useRef, useState } from "react";
import { Send, User, Cpu, RotateCcw } from "lucide-react";
import { useMission } from "../store/MissionContext";
import api from "../api/client";

const SUGGESTED = [
  {
    text: "What is the most critical anomaly right now?",
    category: "anomalies",
  },
  { text: "Which subsystem has the highest risk?", category: "risk" },
  {
    text: "Why is the power subsystem showing abnormal behavior?",
    category: "analysis",
  },
  {
    text: "Are there any conjunction threats I should know about?",
    category: "ssa",
  },
  {
    text: "Can we safely perform the planned attitude maneuver?",
    category: "planning",
  },
  {
    text: "What will happen if the current trend continues?",
    category: "forecast",
  },
  { text: "Summarize the current mission health.", category: "status" },
  {
    text: "What are the recommended actions for the active anomaly?",
    category: "actions",
  },
];

const CATEGORY_COLORS = {
  anomalies: "var(--color-red)",
  risk: "var(--color-amber)",
  analysis: "var(--color-cyan)",
  ssa: "var(--color-amber)",
  planning: "var(--color-green)",
  forecast: "var(--color-amber)",
  status: "var(--color-cyan)",
  actions: "var(--color-green)",
};

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <div
      className={`flex gap-3 fade-in-up ${isUser ? "flex-row-reverse" : ""}`}
    >
      <div
        className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
          isUser
            ? "bg-[var(--color-border-bright)]"
            : "bg-[var(--color-purple)]/15"
        }`}
      >
        {isUser ? (
          <User size={14} className="text-[var(--color-muted)]" />
        ) : (
          <Cpu size={13} style={{ color: "var(--color-purple)" }} />
        )}
      </div>
      <div
        className={`max-w-[78%] rounded-lg px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-[var(--color-panel-raised)] text-[var(--color-text)] border border-[var(--color-border)]"
            : "text-[var(--color-text)]"
        }`}
        style={
          !isUser
            ? {
                background: "rgba(165,110,255,0.06)",
                border: "1px solid rgba(165,110,255,0.2)",
              }
            : undefined
        }
      >
        {message.content}
      </div>
    </div>
  );
}

export default function Copilot() {
  const { missionId } = useMission();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [contextAnomalyId, setContextAnomalyId] = useState(null);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    api
      .copilotHistory(missionId)
      .then((h) => setMessages(h))
      .catch(() => setMessages([]));
  }, [missionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (question) => {
    const q = question ?? input;
    if (!q.trim() || loading) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", content: q }]);
    setLoading(true);
    try {
      const res = await api.copilotChat({
        mission_id: missionId,
        question: q,
        context_anomaly_id: contextAnomalyId,
      });
      setContextAnomalyId(res.context_anomaly_id);
      setMessages((m) => [...m, { role: "assistant", content: res.answer }]);
    } catch {
      setError(
        "Copilot temporarily unavailable. Numerical analysis remains available on the Dashboard.",
      );
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setContextAnomalyId(null);
    setError(null);
  };

  return (
    <div
      className="max-w-[920px] mx-auto flex flex-col"
      style={{ height: "calc(100vh - 7rem)" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="mono text-sm tracking-widest text-[var(--color-dim)]">
            MISSION COPILOT
          </h1>
          <div
            className="mono text-[10px] mt-0.5 flex items-center gap-1.5"
            style={{ color: "var(--color-purple)" }}
          >
            <Cpu size={9} />
            Grounded analysis · Evidence-anchored reasoning
          </div>
        </div>
        <div className="flex items-center gap-3">
          {contextAnomalyId && (
            <span className="mono text-[10px] text-[var(--color-cyan)] bg-[var(--color-cyan)]/10 border border-[var(--color-cyan)]/30 rounded px-2 py-1">
              Context: anomaly #{contextAnomalyId}
            </span>
          )}
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="text-[var(--color-muted)] hover:text-[var(--color-text)] flex items-center gap-1.5 text-xs mono"
            >
              <RotateCcw size={12} />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Chat window */}
      <div className="flex-1 overflow-y-auto bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg p-5 space-y-4">
        {messages.length === 0 && (
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="shrink-0 w-7 h-7 rounded-full bg-[var(--color-purple)]/15 flex items-center justify-center">
                <Cpu size={13} style={{ color: "var(--color-purple)" }} />
              </div>
              <div
                className="rounded-lg px-4 py-3 text-sm leading-relaxed text-[var(--color-text)]"
                style={{
                  background: "rgba(165,110,255,0.06)",
                  border: "1px solid rgba(165,110,255,0.2)",
                }}
              >
                <span className="font-medium">Mission Copilot ready.</span> I
                have access to anomaly evidence, risk data, telemetry forecasts,
                conjunction alerts, and mission plan evaluations. All answers
                are grounded in current mission data — I will not invent
                telemetry values.
                <br />
                <br />
                <span className="text-[var(--color-muted)]">
                  Try one of the suggested questions below, or type your own.
                </span>
              </div>
            </div>

            <div className="pl-10">
              <div className="mono text-[10px] text-[var(--color-dim)] tracking-widest mb-2">
                SUGGESTED QUESTIONS
              </div>
              <div className="flex flex-wrap gap-2">
                {SUGGESTED.map((s) => (
                  <button
                    key={s.text}
                    onClick={() => send(s.text)}
                    className="text-xs border rounded-full px-3 py-1.5 transition-all hover:brightness-110"
                    style={{
                      color: CATEGORY_COLORS[s.category] || "var(--color-cyan)",
                      borderColor: `${CATEGORY_COLORS[s.category] || "var(--color-cyan)"}33`,
                      background: `${CATEGORY_COLORS[s.category] || "var(--color-cyan)"}08`,
                    }}
                  >
                    {s.text}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}

        {loading && (
          <div className="flex gap-3 fade-in-up">
            {/* avatar */}
            <div className="shrink-0 w-7 h-7 rounded-full bg-[var(--color-purple)]/15 flex items-center justify-center mt-0.5">
              <Cpu size={13} style={{ color: "var(--color-purple)" }} />
            </div>
            {/* processing card */}
            <div
              className="rounded-lg px-4 py-3 flex flex-col gap-2"
              style={{
                background: "rgba(165,110,255,0.06)",
                border: "1px solid rgba(165,110,255,0.2)",
                minWidth: "220px",
              }}
            >
              {/* label row */}
              <div className="flex items-center gap-2">
                <svg
                  className="granite-spin shrink-0"
                  width="13"
                  height="13"
                  viewBox="0 0 13 13"
                  fill="none"
                  aria-hidden="true"
                >
                  <circle
                    cx="6.5"
                    cy="6.5"
                    r="5.5"
                    stroke="rgba(165,110,255,0.25)"
                    strokeWidth="1.5"
                  />
                  <circle
                    cx="6.5"
                    cy="6.5"
                    r="5.5"
                    stroke="var(--color-purple)"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeDasharray="8 27"
                  />
                </svg>
                <span
                  className="mono text-[10px] tracking-[0.12em] font-semibold"
                  style={{ color: "var(--color-purple)" }}
                >
                  IBM GRANITE
                </span>
              </div>
              {/* step lines */}
              <div className="space-y-1">
                {[
                  "Analyzing mission context",
                  "Correlating telemetry and anomalies",
                  "Generating response",
                ].map((line, i) => (
                  <div
                    key={line}
                    className="flex items-center gap-1.5 text-xs"
                    style={{
                      color: i < 2 ? "var(--color-dim)" : "var(--color-muted)",
                    }}
                  >
                    {i < 2 ? (
                      <span
                        style={{
                          color: "var(--color-green)",
                          fontSize: "11px",
                          lineHeight: 1,
                        }}
                      >
                        ✓
                      </span>
                    ) : (
                      <span
                        className="step-active-dot inline-block rounded-full shrink-0"
                        style={{
                          width: "7px",
                          height: "7px",
                          background: "var(--color-purple)",
                        }}
                      />
                    )}
                    {i === 2 ? `${line}…` : line}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="text-xs text-[var(--color-red)] bg-[var(--color-red)]/10 border border-[var(--color-red)]/30 rounded px-3 py-2">
            {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="mt-3 flex items-center gap-2">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask the Mission Copilot about anomalies, risk, forecasts, or mission status…"
          className="flex-1 bg-[var(--color-panel)] border border-[var(--color-border-bright)] rounded-lg px-4 py-3 text-sm text-[var(--color-text)] placeholder:text-[var(--color-dim)] focus:border-[var(--color-cyan)] outline-none transition-colors"
        />
        <button
          onClick={() => send()}
          disabled={loading || !input.trim()}
          className="rounded-lg p-3 transition-all disabled:opacity-40"
          style={{ background: "var(--color-cyan)", color: "#051018" }}
        >
          <Send size={16} />
        </button>
      </div>
      <div className="mono text-[9px] text-[var(--color-dim)] text-center mt-1.5">
        All responses are grounded in current mission evidence — this system
        does not issue autonomous spacecraft commands
      </div>
    </div>
  );
}
