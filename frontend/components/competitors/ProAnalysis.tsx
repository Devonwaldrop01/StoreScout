"use client";

/**
 * Intelligence Pro — the strategist report (summary_type="pro").
 *
 * Deliberately a different product from the free Scout Brief digest: the
 * digest says WHAT happened; this interprets what the competitor's behavior
 * MEANS, predicts next moves with confidence, and evaluates the impact on
 * the user's own business. Visually it reads as a sectioned dossier with
 * confidence meters — not a card stack.
 */

import { RefreshCw, Brain, Shield, Eye, Zap, Activity } from "lucide-react";
import { SaveToPlaybook } from "@/components/SaveToPlaybook";
import { INSIGHT_LANGUAGE } from "@/lib/insight";

export interface ProAnalysisData {
  threat?: { level?: string; score?: number; why?: string };
  momentum?: { state?: string; evidence?: string[] };
  interpretation?: string;
  predictions?: Array<{ move?: string; confidence?: number; basis?: string }>;
  impact?: { opportunities?: string[]; risks?: string[]; posture?: string };
  evidence?: string[];
  confidence_basis?: string[];
}

const THREAT_COLOR: Record<string, string> = {
  high: "#F2555A",
  medium: "#FFB224",
  low: "#4CC38A",
};

const MOMENTUM_LABEL: Record<string, { label: string; color: string }> = {
  accelerating: { label: "Accelerating", color: "#F2555A" },
  stable: { label: "Stable", color: "#A8AC9E" },
  slowing: { label: "Slowing", color: "#4CC38A" },
};

function ConfidenceMeter({ value }: { value: number }) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className="flex items-center gap-2 shrink-0">
      <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--bg3)" }}>
        <div className="h-full rounded-full" style={{ width: `${v}%`, background: v >= 70 ? "var(--emerald)" : v >= 40 ? "var(--accent)" : "var(--muted)" }} />
      </div>
      <span className="num text-[11px] font-bold" style={{ color: "var(--text-2)" }}>{v}%</span>
    </div>
  );
}

function SectionLabel({ icon: Icon, children, color = "var(--text-2)" }: { icon: React.ElementType; children: React.ReactNode; color?: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon className="w-3.5 h-3.5 shrink-0" style={{ color }} />
      <span className="label-caps" style={{ color }}>{children}</span>
    </div>
  );
}

export function ProAnalysis({
  hostname, data, generatedAt, model, refreshing, onRegenerate, competitorId,
}: {
  hostname: string;
  data: ProAnalysisData;
  generatedAt: string;
  model: string;
  refreshing?: boolean;
  onRegenerate: () => void;
  competitorId?: string;
}) {
  const threatLevel = (data.threat?.level || "medium").toLowerCase();
  const threatColor = THREAT_COLOR[threatLevel] ?? THREAT_COLOR.medium;
  const threatScore = typeof data.threat?.score === "number" ? Math.max(0, Math.min(100, data.threat.score)) : null;
  const momentum = MOMENTUM_LABEL[(data.momentum?.state || "").toLowerCase()] ?? null;

  return (
    <div className="space-y-4">

      {/* ── Report header: threat verdict is the headline ── */}
      <div
        className="rounded-md p-5"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: `3px solid ${threatColor}` }}
      >
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <Brain className="w-4 h-4 shrink-0" style={{ color: "var(--text-2)" }} />
              <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>Intelligence Pro</span>
              <span className="label-caps" style={{ color: "var(--muted)" }}>{hostname}</span>
              {refreshing && (
                <span className="label-caps flex items-center gap-1" style={{ color: "var(--muted)" }}>
                  <RefreshCw className="w-3 h-3 animate-spin" /> updating
                </span>
              )}
            </div>
            <div className="flex items-baseline gap-3 flex-wrap mt-2">
              <span className="text-2xl font-bold capitalize" style={{ color: threatColor }}>
                {threatLevel} threat
              </span>
              {threatScore !== null && (
                <span className="num text-sm font-bold" style={{ color: "var(--text-2)" }}>{threatScore}/100</span>
              )}
              {momentum && (
                <span className="flex items-center gap-1.5 text-xs font-semibold" style={{ color: momentum.color }}>
                  <Activity className="w-3.5 h-3.5" /> {momentum.label}
                </span>
              )}
            </div>
            {data.threat?.why && (
              <p className="text-sm leading-relaxed mt-2" style={{ color: "var(--text-2)" }}>{data.threat.why}</p>
            )}
          </div>
          <button
            onClick={onRegenerate}
            className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg transition-all hover:bg-white/5 shrink-0"
            style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
          >
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>
      </div>

      {/* ── Momentum + interpretation ── */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <SectionLabel icon={Activity}>Momentum</SectionLabel>
          <div className="space-y-2">
            {(data.momentum?.evidence || []).map((e, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: momentum?.color ?? "var(--muted)" }} />
                <p className="text-sm leading-snug" style={{ color: "var(--text-2)" }}>{e}</p>
              </div>
            ))}
            {(data.momentum?.evidence || []).length === 0 && (
              <p className="text-sm" style={{ color: "var(--muted)" }}>Momentum evidence builds as scan history accumulates.</p>
            )}
          </div>
        </div>

        <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <SectionLabel icon={Eye}>Market interpretation</SectionLabel>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
            {data.interpretation || "Not enough history to interpret this competitor's strategy yet — this sharpens with every scan."}
          </p>
        </div>
      </div>

      {/* ── Predicted next moves — the shared "Prediction" category ── */}
      {(data.predictions?.length ?? 0) > 0 && (
        <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: `3px solid ${INSIGHT_LANGUAGE.prediction.color}` }}>
          <SectionLabel icon={INSIGHT_LANGUAGE.prediction.Icon} color={INSIGHT_LANGUAGE.prediction.color}>Predicted next moves</SectionLabel>
          <div className="space-y-3">
            {data.predictions!.map((p, i) => (
              <div key={i} className="flex items-start justify-between gap-4 pb-3" style={{ borderBottom: i < data.predictions!.length - 1 ? "1px solid var(--border)" : "none" }}>
                <div className="min-w-0">
                  <p className="text-sm font-semibold leading-snug" style={{ color: "var(--text)" }}>{p.move}</p>
                  {p.basis && <p className="text-xs mt-1 leading-snug" style={{ color: "var(--muted)" }}>Based on: {p.basis}</p>}
                </div>
                {typeof p.confidence === "number" && <ConfidenceMeter value={p.confidence} />}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Your business impact ── */}
      <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <SectionLabel icon={Zap} color="#4CC38A">Your business impact</SectionLabel>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wide mb-2" style={{ color: "var(--emerald)" }}>Opportunities</p>
            <div className="space-y-2">
              {(data.impact?.opportunities || []).map((o, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: "var(--emerald)" }} />
                  <p className="text-sm leading-snug flex-1 min-w-0" style={{ color: "var(--text-2)" }}>{o}</p>
                  {competitorId && (
                    <SaveToPlaybook
                      size="xs"
                      item={{
                        source_type: "pro_analysis",
                        source_ref: `${competitorId}:opp:${i}`,
                        competitor_id: competitorId,
                        hostname,
                        title: o.length > 180 ? `${o.slice(0, 177)}…` : o,
                        reason: `Intelligence Pro opportunity on ${hostname}`,
                        evidence: (data.evidence || []).slice(0, 3).join(" · "),
                        priority: (data.threat?.level || "").toLowerCase() === "high" ? "high" : "medium",
                      }}
                    />
                  )}
                </div>
              ))}
              {(data.impact?.opportunities || []).length === 0 && (
                <p className="text-sm" style={{ color: "var(--muted)" }}>No clear openings right now — that itself is useful to know.</p>
              )}
            </div>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wide mb-2" style={{ color: "#F2555A" }}>Risks</p>
            <div className="space-y-2">
              {(data.impact?.risks || []).map((r, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: "#F2555A" }} />
                  <p className="text-sm leading-snug" style={{ color: "var(--text-2)" }}>{r}</p>
                </div>
              ))}
              {(data.impact?.risks || []).length === 0 && (
                <p className="text-sm" style={{ color: "var(--muted)" }}>No active threats to your position detected.</p>
              )}
            </div>
          </div>
        </div>
        {data.impact?.posture && (
          <div className="mt-4 px-3 py-2.5 rounded-md" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
            <p className="text-sm font-semibold leading-snug" style={{ color: "var(--text)" }}>
              <span className="label-caps mr-2" style={{ color: "var(--accent)" }}>Posture</span>
              {data.impact.posture}
            </p>
          </div>
        )}
      </div>

      {/* ── Evidence + confidence basis ── */}
      <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <SectionLabel icon={Shield}>Evidence</SectionLabel>
        <div className="grid sm:grid-cols-2 gap-x-6 gap-y-1.5">
          {(data.evidence || []).map((e, i) => (
            <p key={i} className="num text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>· {e}</p>
          ))}
        </div>
        {(data.confidence_basis?.length ?? 0) > 0 && (
          <p className="text-[11px] mt-3" style={{ color: "var(--muted)" }}>
            Confidence drawn from: {data.confidence_basis!.join(" · ")}
          </p>
        )}
      </div>

      <p className="text-[11px]" style={{ color: "var(--muted)", opacity: 0.5 }}>
        {model} · refreshed daily · generated {new Date(generatedAt).toLocaleString()}
      </p>
    </div>
  );
}
