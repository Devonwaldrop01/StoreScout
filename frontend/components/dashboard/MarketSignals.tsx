"use client";

/**
 * Market Signals — the executive layer above the raw signal feed. When several
 * competitors do the same thing at once (three run low on stock, four start
 * discounting), that's a market CONDITION, not a pile of near-identical cards.
 * This surfaces the strategic read first — what happened, why it matters, your
 * move — and tucks the per-competitor detail underneath. The top signal is
 * emphasized so a five-minute visit lands on the one decision that matters.
 *
 * When nothing significant is moving, QuietIntelligence takes over so the page
 * still teaches the user something about their market.
 */

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ArrowRight, Sparkles } from "lucide-react";
import { INSIGHT_LANGUAGE } from "@/lib/insight";
import { deriveMarketSignals, deriveQuietIntelligence, type MarketSignal, type MarketFact } from "@/lib/market";
import type { SignalGroup } from "@/lib/signals";
import type { Competitor } from "@/lib/api";

function SignalBlock({ signal, primary }: { signal: MarketSignal; primary: boolean }) {
  const [open, setOpen] = useState(false);
  const lang = INSIGHT_LANGUAGE[signal.kind];
  const Icon = lang.Icon;

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderLeft: `3px solid ${lang.color}`,
      }}
    >
      <div className={primary ? "p-5" : "p-4"}>
        {/* Category + breadth */}
        <div className="flex items-center gap-2 mb-2">
          <Icon className="w-3.5 h-3.5 shrink-0" style={{ color: lang.color }} />
          <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: lang.color }}>
            Market Signal · {lang.label}
          </span>
          <span
            className="num text-[10px] font-semibold px-1.5 py-0.5 rounded ml-auto"
            style={{ background: "var(--bg3)", color: "var(--muted)" }}
          >
            {signal.competitorCount} competitors
          </span>
        </div>

        {/* 1. What happened — the lead */}
        <h3
          className={primary ? "font-bold leading-snug mb-1" : "font-semibold leading-snug mb-1"}
          style={{ color: "var(--text)", fontSize: primary ? "1.05rem" : "0.95rem" }}
        >
          {signal.whatHappened}
        </h3>

        {/* 2. Why it matters — the interpretation */}
        <p className="text-[13px] leading-relaxed mb-3" style={{ color: "var(--text-2)" }}>
          {signal.whyItMatters}
        </p>

        {/* 3. Your move — the decision */}
        <div className="rounded-md px-3 py-2.5" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-1.5 mb-1">
            <INSIGHT_LANGUAGE.action.Icon className="w-3 h-3" style={{ color: INSIGHT_LANGUAGE.action.color }} />
            <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: INSIGHT_LANGUAGE.action.color }}>
              Your Move
            </span>
          </div>
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--text)" }}>{signal.yourMove}</p>
        </div>

        {/* 4. Evidence — who moved (the detail lives underneath) */}
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-1.5 mt-3 text-[11px] font-medium transition-colors hover:brightness-150"
          style={{ color: "var(--muted)" }}
        >
          <ChevronDown className="w-3 h-3 transition-transform" style={{ transform: open ? "rotate(180deg)" : "none" }} />
          {open ? "Hide" : "Show"} the {signal.members.length} competitors behind this signal
        </button>
        {open && (
          <div className="mt-2 space-y-1">
            {signal.members.map((m) => (
              <Link
                key={m.competitor_id}
                href={`/dashboard/${m.competitor_id}`}
                className="flex items-center gap-2 px-3 py-2 rounded-md transition-colors hover:bg-white/[.03]"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
              >
                <span className="num text-xs font-semibold truncate" style={{ color: "var(--text)" }}>{m.hostname}</span>
                <span className="text-[11px] truncate" style={{ color: "var(--muted)" }}>{m.label}</span>
                <ArrowRight className="w-3 h-3 ml-auto shrink-0" style={{ color: "var(--muted)" }} />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function MarketSignals({ groups }: { groups: SignalGroup[] }) {
  const signals = deriveMarketSignals(groups);
  if (signals.length === 0) return null;

  return (
    <div className="mb-5">
      <p className="tick-label mb-2.5">Market movement · what your landscape is doing at once</p>
      <div className="space-y-3">
        {signals.map((s, i) => (
          <SignalBlock key={s.id} signal={s} primary={i === 0} />
        ))}
      </div>
    </div>
  );
}

// ── Quiet-day intelligence ──────────────────────────────────────────────────

export function QuietIntelligence({ competitors }: { competitors: Competitor[] }) {
  const facts: MarketFact[] = deriveQuietIntelligence(competitors);
  if (facts.length === 0) return null;

  return (
    <div className="rounded-lg p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="w-4 h-4" style={{ color: "var(--accent)" }} />
        <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Quiet in the market — here&apos;s what StoreScout knows</p>
      </div>
      <p className="text-[13px] leading-relaxed mb-4" style={{ color: "var(--text-2)" }}>
        No major competitor moves in the last window. That&apos;s intelligence too — it means the category is stable
        right now. Here&apos;s the baseline you&apos;re operating against, so today isn&apos;t a wasted look.
      </p>
      <div className="grid sm:grid-cols-2 gap-2.5">
        {facts.map((f) => (
          <div key={f.label} className="rounded-md px-3 py-2.5" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
            <p className="text-[10px] uppercase tracking-wider mb-0.5" style={{ color: "var(--muted)" }}>{f.label}</p>
            <p className="text-sm font-bold leading-none mb-1" style={{ color: "var(--text)" }}>{f.value}</p>
            <p className="text-[11px] leading-snug" style={{ color: "var(--muted)" }}>{f.detail}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
