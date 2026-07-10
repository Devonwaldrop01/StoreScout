"use client";

/**
 * Guided Research — turns the dossier's tabs into a research journey with a
 * clear finish line that transitions the user from Research Mode into
 * Monitoring Mode. Tracks which areas they've explored, always suggests the
 * next thread to pull ("never a dead end"), and on completion tells them
 * StoreScout will now watch this market for them.
 */

import { useCallback, useEffect, useState } from "react";
import { Check, ArrowRight, Radar, CheckCircle2 } from "lucide-react";

type TabKey = "overview" | "catalog" | "pricing" | "changes" | "intelligence";

const STEPS: { key: TabKey; label: string; teaser: string }[] = [
  { key: "overview", label: "The big picture", teaser: "who they are at a glance" },
  { key: "pricing", label: "Pricing strategy", teaser: "how they price and discount" },
  { key: "catalog", label: "Product strategy", teaser: "their hero products and gaps" },
  { key: "intelligence", label: "Brand & how you compare", teaser: "positioning, weaknesses, head-to-head" },
];

function keyFor(id: string) { return `research_progress_${id}`; }

export function ResearchProgress({
  competitorId, currentTab, onNavigate, isFree, onUpgrade,
}: {
  competitorId: string;
  currentTab: TabKey;
  onNavigate: (tab: TabKey) => void;
  isFree: boolean;
  onUpgrade: () => void;
}) {
  const [visited, setVisited] = useState<Set<string>>(new Set());
  const [dismissed, setDismissed] = useState(false);

  // Mark the current tab visited (persisted per competitor).
  useEffect(() => {
    try {
      const raw = localStorage.getItem(keyFor(competitorId));
      const set = new Set<string>(raw ? JSON.parse(raw) : []);
      if (!set.has(currentTab)) {
        set.add(currentTab);
        localStorage.setItem(keyFor(competitorId), JSON.stringify([...set]));
      }
      setVisited(set);
      if (localStorage.getItem(keyFor(competitorId) + "_done")) setDismissed(true);
    } catch { /* ignore */ }
  }, [competitorId, currentTab]);

  const doneCount = STEPS.filter((s) => visited.has(s.key)).length;
  const complete = doneCount >= STEPS.length;
  const next = STEPS.find((s) => !visited.has(s.key));

  const finish = useCallback(() => {
    try { localStorage.setItem(keyFor(competitorId) + "_done", "1"); } catch { /* ignore */ }
    setDismissed(true);
  }, [competitorId]);

  // Completion → the transition into Monitoring Mode.
  if (complete && !dismissed) {
    return (
      <div className="rounded-md p-5" style={{ background: "var(--bg-card)", border: "1px solid rgba(76,195,138,.3)", borderLeft: "3px solid #4CC38A" }}>
        <div className="flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 mt-0.5 shrink-0" style={{ color: "#4CC38A" }} />
          <div className="flex-1">
            <h3 className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>You&apos;ve completed your first competitive analysis</h3>
            <p className="text-[13px] leading-relaxed mb-3" style={{ color: "var(--text-2)" }}>
              From here, StoreScout watches this market for you — tracking their prices, launches, and promotions, and
              telling you the moment something meaningful changes. Research becomes monitoring.
            </p>
            <div className="flex items-center gap-2 flex-wrap">
              <button onClick={() => (window.location.href = "/playbook")} className="text-xs font-semibold px-3 py-2 rounded-md transition-all hover:brightness-110" style={{ background: "var(--accent)", color: "var(--ink)" }}>
                See your Playbook →
              </button>
              <button onClick={isFree ? onUpgrade : () => (window.location.href = "/settings#notifications")} className="text-xs font-medium px-3 py-2 rounded-md transition-all hover:bg-white/[.05]" style={{ color: "var(--text-2)", border: "1px solid var(--border)" }}>
                {isFree ? "Unlock daily monitoring & alerts" : "Set up alerts"}
              </button>
              <button onClick={finish} className="text-xs ml-auto" style={{ color: "var(--muted)" }}>Dismiss</button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (dismissed) return null;

  // In-progress → a slim guide with the next thread to pull.
  return (
    <div className="rounded-md px-4 py-3" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Radar className="w-4 h-4" style={{ color: "var(--accent)" }} />
          <span className="text-xs font-semibold" style={{ color: "var(--text)" }}>Your research trail</span>
          <span className="num text-[11px]" style={{ color: "var(--muted)" }}>{doneCount}/{STEPS.length}</span>
        </div>
        <div className="flex items-center gap-1.5">
          {STEPS.map((s) => {
            const done = visited.has(s.key);
            const active = s.key === currentTab;
            return (
              <button key={s.key} onClick={() => onNavigate(s.key)} title={s.label}
                className="flex items-center gap-1 text-[11px] px-2 py-1 rounded-md transition-all"
                style={{ background: active ? "var(--bg3)" : "transparent", border: `1px solid ${done ? "rgba(76,195,138,.35)" : "var(--border)"}`, color: done ? "#4CC38A" : active ? "var(--text)" : "var(--muted)" }}>
                {done && <Check className="w-3 h-3" />}<span className="hidden sm:inline">{s.label}</span>
              </button>
            );
          })}
        </div>
      </div>
      {next && (
        <button onClick={() => onNavigate(next.key)} className="mt-2 flex items-center gap-1.5 text-[12px] font-medium transition-colors hover:brightness-110" style={{ color: "var(--accent)" }}>
          <ArrowRight className="w-3.5 h-3.5" /> Next: explore their {next.label.toLowerCase()} — {next.teaser}
        </button>
      )}
    </div>
  );
}
