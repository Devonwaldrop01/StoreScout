"use client";

/**
 * Intelligence Sources — "what does StoreScout currently know about my
 * business?" Not an integrations list: a knowledge panel. Shows the
 * Business Understanding score (how well StoreScout understands the
 * business — NOT a health score), what each connected source teaches it,
 * and what connecting the missing ones would unlock — phrased as outcomes,
 * never as APIs. Renders above the actual connect flows in settings.
 */

import { useEffect, useState } from "react";
import { Brain, Check, Square } from "lucide-react";
import { integrations as api, type BusinessKnowledge } from "@/lib/api";

const TIER_LABEL: Record<string, string> = {
  strategic: "Strategic — connect your store to make recommendations operational",
  operational: "Operational — recommendations reference your real products & pricing",
  customer: "Customer-aware — segments and campaign timing included",
  full: "Full picture — traffic, search, segments, and store data all inform every play",
};

export function IntelligenceSources() {
  const [data, setData] = useState<BusinessKnowledge | null>(null);

  useEffect(() => {
    api.intelligenceSources().then((r) => setData(r.data)).catch(() => {});
  }, []);

  if (!data) return null;

  const score = data.understanding_score;
  const scoreColor = score >= 70 ? "#4CC38A" : score >= 40 ? "#FFB224" : "var(--muted)";

  return (
    <div className="mb-6 rounded-md p-5" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
      {/* Score header */}
      <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Brain className="w-4 h-4" style={{ color: "var(--text-2)" }} />
            <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Business Understanding</p>
          </div>
          <p className="text-xs max-w-md leading-relaxed" style={{ color: "var(--muted)" }}>
            How well StoreScout knows your business — every source below makes recommendations more yours.
          </p>
        </div>
        <div className="text-right">
          <p className="num text-3xl font-bold leading-none" style={{ color: scoreColor }}>{score}%</p>
          <p className="text-[10px] uppercase tracking-wider mt-1" style={{ color: "var(--muted)" }}>understood</p>
        </div>
      </div>

      {/* Score bar */}
      <div className="h-1.5 rounded-full overflow-hidden mb-1.5" style={{ background: "var(--bg)" }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, background: scoreColor }} />
      </div>
      <p className="text-[11px] mb-4" style={{ color: "var(--text-2)" }}>
        {TIER_LABEL[data.depth_tier]}
      </p>

      <div className="grid sm:grid-cols-2 gap-4">
        {/* Understands */}
        <div>
          <p className="label-caps mb-2">StoreScout understands</p>
          {data.understood.length === 0 ? (
            <p className="text-xs" style={{ color: "var(--muted)" }}>Nothing yet — start by tracking a competitor.</p>
          ) : (
            <div className="space-y-1">
              {data.understood.slice(0, 8).map((u) => (
                <div key={u} className="flex items-center gap-2">
                  <Check className="w-3 h-3 shrink-0" style={{ color: "#4CC38A" }} />
                  <span className="text-xs" style={{ color: "var(--text-2)" }}>{u}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Missing knowledge — sold as outcomes */}
        <div>
          <p className="label-caps mb-2">Missing knowledge</p>
          {data.missing.length === 0 ? (
            <p className="text-xs" style={{ color: "#4CC38A" }}>Full picture — StoreScout knows your business.</p>
          ) : (
            <div className="space-y-1.5">
              {data.missing.map((m) => (
                <div key={m.name} className="flex items-start gap-2">
                  <Square className="w-3 h-3 shrink-0 mt-0.5" style={{ color: "var(--muted)", opacity: 0.5 }} />
                  <p className="text-xs leading-snug" style={{ color: "var(--muted)" }}>
                    <span className="font-semibold" style={{ color: "var(--text-2)" }}>{m.name} · </span>
                    {m.unlock}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
