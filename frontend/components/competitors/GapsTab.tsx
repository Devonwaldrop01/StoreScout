"use client";

import { useEffect, useState } from "react";
import { Lock, Target, TrendingUp, ChevronDown, ChevronUp, ArrowRight, Check, DollarSign, Package, Grid3X3, Tag, Rocket } from "lucide-react";
import { LockedValueCard } from "@/components/ui";
import { competitors as api, type GapsResponse, type Gap } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

function opportunityLabel(opp?: number): { label: string; color: string } {
  const o = opp ?? 0;
  if (o >= 0.6) return { label: "High opportunity", color: "#FFB224" };
  if (o >= 0.35) return { label: "Moderate opportunity", color: "var(--amber)" };
  return { label: "Opportunity", color: "#A8AC9E" };
}

function getGapAction(type: string): string {
  switch (type) {
    case "price_band":
      return "Source or price 1–2 products at this point. Run a small ad test this week to validate demand before committing to inventory.";
    case "availability":
      return "Update your in-stock product pages to lead with availability. Run retargeting to their audience while they have stock gaps — those shoppers are actively looking for an alternative.";
    case "category":
      return "Pick one hero SKU in this category to test. A single well-positioned product launched this week beats a perfect catalog in 6 weeks.";
    case "discount":
      return "Own the full-price lane — don't race them on markdowns. Add trust signals (reviews, guarantees) and quality messaging to your product pages and email footer.";
    case "launch_momentum":
      return "Launch something in this space before they recover pace. Speed matters more than perfection — being first to capture search demand compounds over time.";
    default:
      return "Investigate this gap in full and decide whether your catalog can credibly fill it. Even one targeted SKU can establish a foothold.";
  }
}

function getGapIcon(type: string): React.ElementType {
  switch (type) {
    case "price_band":       return DollarSign;
    case "availability":     return Package;
    case "category":         return Grid3X3;
    case "discount":         return Tag;
    case "launch_momentum":  return Rocket;
    default:                 return ArrowRight;
  }
}

const REVIEWED_PREFIX = "gaps_reviewed_";

function getReviewed(competitorId: string): Set<number> {
  try {
    const raw = localStorage.getItem(REVIEWED_PREFIX + competitorId);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function saveReviewed(competitorId: string, ids: Set<number>) {
  try {
    localStorage.setItem(REVIEWED_PREFIX + competitorId, JSON.stringify([...ids]));
  } catch {}
}

interface GapCardProps {
  gap: Gap;
  index: number;
  competitorId: string;
  reviewed: Set<number>;
  onReviewed: (i: number) => void;
}

function GapCard({ gap, index, reviewed, onReviewed }: GapCardProps) {
  const [expanded, setExpanded] = useState(false);
  const { label, color } = opportunityLabel(gap.opportunity);
  const action = getGapAction(gap.type || "");
  const isReviewed = reviewed.has(index);
  const GapIcon = getGapIcon(gap.type || "");

  return (
    <div
      className="rounded-md overflow-hidden transition-all"
      style={{
        background: "var(--bg-card)",
        border: `1px solid ${isReviewed ? "rgba(255,255,255,0.05)" : "var(--border)"}`,
        opacity: isReviewed ? 0.6 : 1,
      }}
    >
      {/* Header row — always visible */}
      <button
        className="w-full text-left px-5 pt-4 pb-4 flex items-start gap-3 transition-colors hover:bg-white/[0.02]"
        onClick={() => !gap.locked && setExpanded((v) => !v)}
        disabled={gap.locked}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 mb-1.5">
            <h4 className="font-semibold text-sm leading-snug" style={{ color: "var(--text)" }}>
              {gap.title}
            </h4>
            <div className="flex items-center gap-2 shrink-0">
              <span
                className="text-[10px] font-bold uppercase px-2 py-1 rounded-md whitespace-nowrap"
                style={{ background: `${color}1f`, color }}
              >
                {label}
              </span>
            </div>
          </div>

          {gap.locked ? (
            <div className="flex items-center gap-2 text-sm" style={{ color: "var(--muted)" }}>
              <Lock className="w-3.5 h-3.5 shrink-0" />
              <span className="italic text-xs">Upgrade to see the action playbook for this gap</span>
            </div>
          ) : (
            <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
              {gap.detail}
            </p>
          )}
        </div>

        {!gap.locked && (
          <div className="shrink-0 mt-0.5">
            {expanded
              ? <ChevronUp className="w-4 h-4" style={{ color: "var(--muted)" }} />
              : <ChevronDown className="w-4 h-4" style={{ color: "var(--muted)" }} />}
          </div>
        )}
      </button>

      {/* Expanded action panel */}
      {expanded && !gap.locked && (
        <div
          className="px-5 pb-4"
          style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
        >
          <div
            className="rounded-md p-4 mt-3"
            style={{
              background: `${color}09`,
              border: `1px solid ${color}28`,
            }}
          >
            <div className="flex items-start gap-3">
              <GapIcon className="w-4 h-4 shrink-0 mt-0.5" style={{ color }} />
              <div className="flex-1">
                <p
                  className="text-[10px] font-bold uppercase tracking-wider mb-1.5"
                  style={{ color }}
                >
                  What to do
                </p>
                <p className="text-sm leading-relaxed" style={{ color: "var(--text-2, var(--muted))" }}>
                  {action}
                </p>
              </div>
            </div>
          </div>

          {/* Mark as reviewed */}
          <div className="flex items-center justify-between mt-3">
            <p className="text-[11px]" style={{ color: "var(--muted)" }}>
              {gap.metric && typeof gap.metric === "string" && (
                <span>{gap.metric}</span>
              )}
            </p>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onReviewed(index);
                setExpanded(false);
              }}
              className="flex items-center gap-1.5 text-[11px] font-medium transition-opacity hover:opacity-70"
              style={{ color: isReviewed ? "#FFB224" : "var(--muted)" }}
            >
              <Check className="w-3.5 h-3.5" />
              {isReviewed ? "Reviewed" : "Mark as reviewed"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function GapsTab({ competitorId }: { competitorId: string }) {
  const [data, setData] = useState<GapsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [reviewed, setReviewed] = useState<Set<number>>(new Set());

  useEffect(() => {
    setReviewed(getReviewed(competitorId));
    api.gaps(competitorId)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [competitorId]);

  function markReviewed(index: number) {
    setReviewed((prev) => {
      const next = new Set(prev);
      next.has(index) ? next.delete(index) : next.add(index);
      saveReviewed(competitorId, next);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 rounded-md animate-pulse" style={{ background: "var(--bg-card)" }} />
        ))}
      </div>
    );
  }

  if (!data || data.gaps.length === 0) {
    return (
      <div className="rounded-md p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <p style={{ color: "var(--muted)" }}>
          No major gaps detected. Their catalog covers price bands evenly, inventory is
          well-stocked, and their launch pace is consistent — no obvious openings from the current snapshot.
        </p>
      </div>
    );
  }

  const reviewedCount = data.gaps.filter((_, i) => reviewed.has(i) && !data.gaps[i].locked).length;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <Target className="w-5 h-5 mt-0.5 shrink-0" style={{ color: "#FFB224" }} />
          <div>
            <h3 className="font-semibold" style={{ color: "var(--text)" }}>
              Market Openings
            </h3>
            <p className="text-sm mt-0.5" style={{ color: "var(--muted)" }}>
              Price points they ignore, demand they can&apos;t fulfill, categories they underserve.
              Expand each gap to see exactly what to do.
            </p>
          </div>
        </div>

        {reviewedCount > 0 && (
          <span
            className="text-[11px] font-medium px-2.5 py-1 rounded-lg shrink-0 whitespace-nowrap"
            style={{ background: "rgba(255,178,36,0.10)", color: "#FFB224" }}
          >
            {reviewedCount} reviewed
          </span>
        )}
      </div>

      {data.gaps.map((g, i) => (
        <GapCard
          key={i}
          gap={g}
          index={i}
          competitorId={competitorId}
          reviewed={reviewed}
          onReviewed={markReviewed}
        />
      ))}

      {data.locked && data.locked_count > 0 && (
        <LockedValueCard
          title={`${data.locked_count} more gap${data.locked_count !== 1 ? "s" : ""} identified`}
          teaser="Unlock every market opening with a specific action playbook for each one."
          plan="pro"
        />
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
