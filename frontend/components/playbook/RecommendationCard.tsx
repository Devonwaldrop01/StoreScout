"use client";

/**
 * Playbook 2.0 — the strategy-first recommendation card.
 *
 * A recommendation is a piece of operator advice, structured as: what happened →
 * why it matters → StoreScout's interpretation → the objective → multiple ways
 * to execute (tool-agnostic) → expected outcome → the evidence, with clearly
 * labelled confidence / priority / effort / timeframe / category. It never tells
 * a merchant to "run Meta ads" — the strategy is the recommendation; channels
 * are just options.
 */

import { useState } from "react";
import {
  ChevronDown, Check, Target, Eye, Lightbulb, Flag, ListChecks, TrendingUp,
  ShieldCheck, CircleDashed, Sparkles,
} from "lucide-react";
import type { PlaybookPlay } from "@/lib/api";
import { SaveToPlaybook } from "@/components/SaveToPlaybook";

const CONFIDENCE_META: Record<string, { label: string; color: string; Icon: typeof ShieldCheck }> = {
  verified:  { label: "Verified",  color: "#4CC38A", Icon: ShieldCheck },
  estimated: { label: "Estimated", color: "#FFB224", Icon: CircleDashed },
  predicted: { label: "Predicted", color: "#7DB8C9", Icon: Sparkles },
};

const PRIORITY_COLOR: Record<string, string> = { high: "#F2555A", medium: "#FFB224", low: "#7DB8C9" };

export function RecommendationCard({ play, done, onDone }: { play: PlaybookPlay; done: boolean; onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const conf = CONFIDENCE_META[play.confidence || "estimated"] || CONFIDENCE_META.estimated;
  const prioColor = PRIORITY_COLOR[play.priority_label || "medium"] || "#FFB224";
  const paths = play.execution_paths ?? [];

  return (
    <div className="rounded-md overflow-hidden transition-opacity" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: `3px solid ${prioColor}`, opacity: done ? 0.55 : 1 }}>
      {/* Header — category + confidence + the strategy title */}
      <button onClick={() => setOpen((v) => !v)} className="w-full text-left px-4 sm:px-5 py-4 transition-colors hover:bg-white/[.015]">
        <div className="flex items-center gap-2 flex-wrap mb-2">
          {play.category && (
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded" style={{ background: "var(--bg3)", color: "var(--text-2)" }}>{play.category}</span>
          )}
          <span className="flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded" style={{ background: `${conf.color}18`, color: conf.color }}>
            <conf.Icon className="w-3 h-3" /> {conf.label}
          </span>
          <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded" style={{ color: prioColor }}>{play.priority_label || "medium"} priority</span>
          <span className="ml-auto flex items-center gap-2 text-[10px]" style={{ color: "var(--muted)" }}>
            {play.effort && <span>⏱ {play.effort}</span>}
            {play.timeframe && <span>· {play.timeframe}</span>}
            <ChevronDown className={`w-4 h-4 transition-transform ${open ? "rotate-180" : ""}`} />
          </span>
        </div>
        <h3 className="text-[15px] font-semibold leading-snug" style={{ color: "var(--text)" }}>{play.title || play.headline}</h3>
        {play.objective && (
          <p className="text-xs mt-1 flex items-center gap-1.5" style={{ color: "var(--accent)" }}>
            <Target className="w-3.5 h-3.5" /> Objective: {play.objective}
          </p>
        )}
        {!open && play.why_it_matters && (
          <p className="text-[13px] mt-1.5 line-clamp-2" style={{ color: "var(--muted)" }}>{play.why_it_matters}</p>
        )}
      </button>

      {open && (
        <div className="px-4 sm:px-5 pb-5 space-y-4" style={{ borderTop: "1px solid var(--border)" }}>
          {/* The reasoning chain */}
          <div className="grid gap-3 pt-4">
            {([
              [Eye, "What happened", play.what_happened, "var(--text-2)"],
              [TrendingUp, "Why it matters", play.why_it_matters, "var(--text-2)"],
              [Lightbulb, "StoreScout's read", play.interpretation, "var(--accent)"],
            ] as [typeof Eye, string, string | undefined, string][]).filter(([, , v]) => v).map(([Icon, label, v, color]) => (
              <div key={label}>
                <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide mb-1" style={{ color }}>
                  <Icon className="w-3.5 h-3.5" /> {label}
                </p>
                <p className="text-[13px] leading-relaxed" style={{ color: "var(--text-2)" }}>{v}</p>
              </div>
            ))}
          </div>

          {/* Execution paths — multiple, tool-agnostic */}
          {paths.length > 0 && (
            <div className="rounded-md p-3" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
              <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide mb-2" style={{ color: "var(--text)" }}>
                <ListChecks className="w-3.5 h-3.5" /> Ways to execute — pick what fits your stack
              </p>
              <div className="space-y-2">
                {paths.map((ep, i) => (
                  <div key={i} className="flex items-start gap-2.5">
                    <span className="text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded shrink-0 mt-0.5" style={{ background: "var(--bg-card)", color: "var(--text-2)", minWidth: 68, textAlign: "center" }}>{ep.surface}</span>
                    <p className="text-[13px] leading-snug" style={{ color: "var(--text-2)" }}>{ep.action}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Expected outcome */}
          {play.expected_outcome && (
            <div className="flex items-start gap-2">
              <Flag className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "#4CC38A" }} />
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "#4CC38A" }}>Expected outcome</p>
                <p className="text-[13px] leading-snug" style={{ color: "var(--text)" }}>{play.expected_outcome}</p>
              </div>
            </div>
          )}

          {/* Evidence */}
          {(play.evidence?.length ?? 0) > 0 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide mb-1" style={{ color: "var(--muted)" }}>Evidence StoreScout used</p>
              <div className="flex flex-wrap gap-1.5">
                {play.evidence!.map((e, i) => (
                  <span key={i} className="text-[11px] px-2 py-0.5 rounded num" style={{ background: "var(--bg3)", color: "var(--muted)" }}>{e}</span>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 pt-1">
            <button onClick={onDone} className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-md transition-all hover:brightness-110"
              style={done ? { background: "var(--bg3)", color: "var(--muted)", border: "1px solid var(--border)" } : { background: "#4CC38A", color: "#07120C" }}>
              <Check className="w-3.5 h-3.5" /> {done ? "Done" : "Mark done"}
            </button>
            <SaveToPlaybook size="sm" item={{
              source_type: "pro_analysis",
              source_ref: `rec:${play.id}`,
              competitor_id: play.competitor_id || undefined,
              hostname: play.hostname,
              title: play.title || play.headline,
              reason: play.why_it_matters || play.interpretation,
              evidence: (play.evidence || []).join(" · "),
              priority: (play.priority_label as "high" | "medium" | "low") || "medium",
            }} />
          </div>
        </div>
      )}
    </div>
  );
}
