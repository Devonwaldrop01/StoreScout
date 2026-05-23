"use client";

import { useEffect, useState } from "react";
import { Lock, Target, TrendingUp } from "lucide-react";
import { competitors as api, type GapsResponse, type Gap } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

function opportunityLabel(opp?: number): { label: string; color: string } {
  const o = opp ?? 0;
  if (o >= 0.6) return { label: "High opportunity", color: "#a3f000" };
  if (o >= 0.35) return { label: "Moderate opportunity", color: "#facc15" };
  return { label: "Opportunity", color: "#94a3b8" };
}

function GapCard({ gap }: { gap: Gap }) {
  const { label, color } = opportunityLabel(gap.opportunity);
  return (
    <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <h4 className="font-semibold text-sm" style={{ color: "var(--text)" }}>{gap.title}</h4>
        <span
          className="text-[10px] font-bold uppercase px-2 py-1 rounded-md whitespace-nowrap shrink-0"
          style={{ background: `${color}1f`, color }}
        >
          {label}
        </span>
      </div>
      {gap.locked ? (
        <div className="flex items-center gap-2 text-sm" style={{ color: "var(--muted)" }}>
          <Lock className="w-3.5 h-3.5" />
          <span className="italic">Upgrade to see how to act on this gap</span>
        </div>
      ) : (
        <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{gap.detail}</p>
      )}
    </div>
  );
}

export default function GapsTab({ competitorId }: { competitorId: string }) {
  const [data, setData] = useState<GapsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  useEffect(() => {
    api.gaps(competitorId)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [competitorId]);

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => <div key={i} className="h-24 rounded-2xl animate-pulse" style={{ background: "var(--bg-card)" }} />)}
      </div>
    );
  }

  if (!data || data.gaps.length === 0) {
    return (
      <div className="rounded-2xl p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <p style={{ color: "var(--muted)" }}>No clear gaps detected for this store yet. Check back after the next scan.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2">
        <Target className="w-5 h-5 mt-0.5" style={{ color: "#a3f000" }} />
        <div>
          <h3 className="font-semibold" style={{ color: "var(--text)" }}>Where there&apos;s room to compete</h3>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Openings this store isn&apos;t serving — price points they ignore, demand they can&apos;t
            fulfill, and categories they only dabble in. Find your lane instead of fighting head-on.
          </p>
        </div>
      </div>

      {data.gaps.map((g, i) => <GapCard key={i} gap={g} />)}

      {data.locked && data.locked_count > 0 && (
        <div
          className="rounded-2xl p-6 text-center"
          style={{ background: "rgba(163,240,0,.06)", border: "1px dashed rgba(163,240,0,.3)" }}
        >
          <TrendingUp className="w-5 h-5 mx-auto mb-2" style={{ color: "#a3f000" }} />
          <p className="text-sm font-medium mb-1" style={{ color: "var(--text)" }}>
            {data.locked_count} more gap{data.locked_count !== 1 ? "s" : ""} identified
          </p>
          <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
            Unlock every gap with specific, actionable detail on how to move into each one.
          </p>
          <button
            onClick={() => setUpgradeOpen(true)}
            className="font-semibold text-sm px-5 py-2.5 rounded-xl transition-all hover:brightness-110"
            style={{ background: "#a3f000", color: "#060d18" }}
          >
            Unlock Full Gap Analysis
          </button>
        </div>
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
