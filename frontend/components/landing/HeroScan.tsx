"use client";

/**
 * The transformation sequence — the first thing a visitor experiences.
 * Not a dashboard screenshot: a live-feeling scan of a real store domain,
 * ending in an opportunity and a recommended move. Educates in ~8 seconds
 * what StoreScout actually does. CSS/React only, no assets.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Zap, TrendingUp, RotateCcw } from "lucide-react";

const DOMAIN = "gymshark.com";

// (label, duration ms) — the honest pipeline order
const STAGES = [
  { label: "Scanning storefront…", ms: 1100 },
  { label: "847 products found", ms: 900, stat: true },
  { label: "Analyzing pricing…", ms: 850 },
  { label: "Analyzing inventory…", ms: 850 },
  { label: "Analyzing brand & collections…", ms: 850 },
  { label: "Finding opportunities…", ms: 1000 },
];

export function HeroScan() {
  const [typed, setTyped] = useState(0);       // chars of DOMAIN typed
  const [stage, setStage] = useState(-1);      // -1 typing, 0..n stages, n+1 done
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const run = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    // Everything is scheduled — no synchronous setState from the effect body
    timers.current.push(setTimeout(() => { setTyped(0); setStage(-1); }, 0));

    // Type the domain
    for (let i = 1; i <= DOMAIN.length; i++) {
      timers.current.push(setTimeout(() => setTyped(i), 350 + i * 70));
    }
    // Walk the stages
    let t = 350 + DOMAIN.length * 70 + 500;
    STAGES.forEach((s, i) => {
      timers.current.push(setTimeout(() => setStage(i), t));
      t += s.ms;
    });
    timers.current.push(setTimeout(() => setStage(STAGES.length), t));
  }, []);

  useEffect(() => {
    run();
    const t = timers.current;
    return () => t.forEach(clearTimeout);
  }, [run]);

  const done = stage >= STAGES.length;

  return (
    <div className="max-w-xl mx-auto text-left">
      <div
        className={`rounded-md overflow-hidden shadow-2xl ${!done && stage >= 0 ? "analyzing-sweep" : ""}`}
        style={{ background: "#0B0C0A", border: "1px solid #262A22" }}
      >
        {/* Terminal chrome */}
        <div className="flex items-center gap-3 px-4 py-2.5 border-b" style={{ background: "#101110", borderColor: "#262A22" }}>
          <div className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#ff5f57" }} />
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#ffbd2e" }} />
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#28c840" }} />
          </div>
          <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "#6C7164" }}>
            StoreScout · first scan
          </span>
          {done && (
            <button
              onClick={run}
              className="ml-auto flex items-center gap-1 text-[10px] font-semibold transition-opacity hover:opacity-70"
              style={{ color: "#6C7164" }}
              aria-label="Replay"
            >
              <RotateCcw className="w-3 h-3" /> replay
            </button>
          )}
        </div>

        <div className="p-5 font-mono text-sm" style={{ minHeight: 240 }}>
          {/* Typed domain */}
          <div className="flex items-center gap-2 mb-4">
            <span style={{ color: "#6C7164" }}>track</span>
            <span style={{ color: "#ECEEE6" }}>
              {DOMAIN.slice(0, typed)}
              {typed < DOMAIN.length && <span className="animate-pulse" style={{ color: "#FFB224" }}>▎</span>}
            </span>
          </div>

          {/* Stage log */}
          <div className="space-y-2">
            {STAGES.map((s, i) => {
              if (stage < i) return null;
              const active = stage === i && !done;
              return (
                <div key={s.label} className="flex items-center gap-2 fade-in text-xs">
                  {active ? (
                    <span className="w-3.5 h-3.5 rounded-full border-2 border-t-transparent animate-spin shrink-0" style={{ borderColor: "#FFB224", borderTopColor: "transparent" }} />
                  ) : (
                    <Check className="w-3.5 h-3.5 shrink-0" style={{ color: "#4CC38A" }} />
                  )}
                  <span style={{ color: s.stat ? "#ECEEE6" : active ? "#A8AC9E" : "#6C7164", fontWeight: s.stat ? 700 : 400 }}>
                    {s.label}
                  </span>
                </div>
              );
            })}
          </div>

          {/* The payoff — an opportunity and a move, not a dashboard */}
          {done && (
            <div className="mt-4 space-y-2.5 fade-up">
              <div
                className="rounded-md p-3.5"
                style={{ background: "#101110", border: "1px solid #262A22", borderLeft: "3px solid #4CC38A" }}
              >
                <div className="flex items-center gap-1.5 mb-1.5">
                  <TrendingUp className="w-3.5 h-3.5" style={{ color: "#4CC38A" }} />
                  <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "#4CC38A" }}>Opportunity found</span>
                </div>
                <p className="text-xs leading-relaxed font-sans" style={{ color: "#A8AC9E" }}>
                  31% of their catalog is discounted — heavy markdown pressure. Their full-price lane is wide open.
                </p>
              </div>
              <div
                className="rounded-md p-3.5 flex items-start gap-2.5"
                style={{ background: "rgba(255,178,36,.05)", border: "1px solid rgba(255,178,36,.2)" }}
              >
                <Zap className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: "#FFB224" }} />
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "#FFB224" }}>Your move</span>
                  <p className="text-xs leading-relaxed mt-0.5 font-sans" style={{ color: "#ECEEE6" }}>
                    Hold full price. Lead with quality signals while they train customers to wait for sales.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      <p className="text-center text-xs mt-3" style={{ color: "var(--muted)", opacity: 0.55 }}>
        This is a real first scan — yours takes about 60 seconds.
      </p>
    </div>
  );
}
