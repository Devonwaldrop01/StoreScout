"use client";

/**
 * Ask StoreScout — conversational exploration of a competitor.
 *
 * Turns the dossier from a set of tabs into a research conversation: the
 * merchant asks anything ("why are they winning?", "how would I compete?"),
 * StoreScout answers from the competitor's real scanned data, and every answer
 * suggests the next question — so there's always another thread to pull.
 */

import { useRef, useState } from "react";
import { Sparkles, ArrowUp, Loader2 } from "lucide-react";
import { competitors as api } from "@/lib/api";

const STARTERS = [
  "Why are they successful?",
  "How would you compete against them?",
  "Where are they vulnerable?",
  "What should I learn from them?",
  "What market are they targeting?",
  "What products should I launch to compete?",
];

interface Turn { q: string; a: string | null; followups: string[]; loading: boolean }

export function AskStoreScout({ competitorId, hostname }: { competitorId: string; hostname: string }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const busy = turns.some((t) => t.loading);
  const scrollRef = useRef<HTMLDivElement>(null);

  async function ask(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    const idx = turns.length;
    setTurns((t) => [...t, { q, a: null, followups: [], loading: true }]);
    setTimeout(() => scrollRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    try {
      const r = await api.ask(competitorId, q);
      setTurns((t) => t.map((x, i) => i === idx ? { ...x, a: r.data.answer || "I couldn't analyze that one.", followups: r.data.followups || [], loading: false } : x));
    } catch {
      setTurns((t) => t.map((x, i) => i === idx ? { ...x, a: "Something went wrong — try again.", loading: false } : x));
    }
    setTimeout(() => scrollRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }

  return (
    <div className="rounded-md" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2 px-4 sm:px-5 py-3.5" style={{ borderBottom: turns.length ? "1px solid var(--border)" : undefined }}>
        <Sparkles className="w-4 h-4" style={{ color: "var(--accent)" }} />
        <div>
          <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>Ask StoreScout</h3>
          <p className="text-[11px]" style={{ color: "var(--muted)" }}>Your analyst for {hostname} — ask anything, grounded in their real data.</p>
        </div>
      </div>

      {/* Conversation */}
      {turns.length > 0 && (
        <div className="px-4 sm:px-5 py-4 space-y-4 max-h-[440px] overflow-y-auto">
          {turns.map((t, i) => (
            <div key={i} className="space-y-2">
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>{t.q}</p>
              {t.loading ? (
                <p className="flex items-center gap-2 text-sm" style={{ color: "var(--muted)" }}><Loader2 className="w-4 h-4 animate-spin" /> Analyzing {hostname}…</p>
              ) : (
                <>
                  <div className="text-[13px] leading-relaxed whitespace-pre-wrap" style={{ color: "var(--text-2)" }}>{t.a}</div>
                  {t.followups.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {t.followups.map((f, j) => (
                        <button key={j} onClick={() => ask(f)} disabled={busy}
                          className="text-[11px] px-2.5 py-1 rounded-full transition-all hover:brightness-110 disabled:opacity-50"
                          style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text-2)" }}>
                          {f}
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
          <div ref={scrollRef} />
        </div>
      )}

      {/* Starter chips (only before the first question) */}
      {turns.length === 0 && (
        <div className="px-4 sm:px-5 py-3 flex flex-wrap gap-1.5">
          {STARTERS.map((s) => (
            <button key={s} onClick={() => ask(s)} disabled={busy}
              className="text-xs px-2.5 py-1.5 rounded-full transition-all hover:brightness-110 disabled:opacity-50"
              style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text-2)" }}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-4 sm:px-5 pb-4 pt-1">
        <div className="flex items-center gap-2 rounded-md px-3 py-2" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") ask(input); }}
            placeholder={`Ask anything about ${hostname}…`}
            className="flex-1 bg-transparent outline-none text-sm"
            style={{ color: "var(--text)" }}
          />
          <button onClick={() => ask(input)} disabled={busy || !input.trim()}
            className="w-7 h-7 flex items-center justify-center rounded-md transition-all hover:brightness-110 disabled:opacity-40"
            style={{ background: "var(--accent)", color: "var(--ink)" }}>
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowUp className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
