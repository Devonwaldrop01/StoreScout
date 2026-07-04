"use client";

import { useEffect, useState } from "react";
import { Building2, FileText, BookOpen, Lock, CheckCircle, XCircle, ChevronRight } from "lucide-react";
import { competitors as api, type StoreProfileResponse } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

// ── shared signal badge ──────────────────────────────────────────────────────

function Signal({ active, label }: { active: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 py-1.5">
      {active
        ? <CheckCircle className="w-4 h-4 shrink-0" style={{ color: "#FFB224" }} />
        : <XCircle className="w-4 h-4 shrink-0" style={{ color: "var(--muted)" }} />
      }
      <span className="text-sm" style={{ color: active ? "var(--text)" : "var(--muted)" }}>{label}</span>
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? "#FFB224" : score >= 40 ? "var(--amber)" : "#A8AC9E";
  const label = score >= 70 ? "High investment" : score >= 40 ? "Moderate" : "Low investment";
  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5">
        <span style={{ color: "var(--muted)" }}>Content investment</span>
        <span className="font-semibold" style={{ color }}>{label}</span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--bg3)" }}>
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${score}%`, background: color }}
        />
      </div>
      <span className="text-xs mt-1 block" style={{ color: "var(--muted)" }}>{score}/100</span>
    </div>
  );
}

// ── Free tier view ───────────────────────────────────────────────────────────

function FreeTierView({
  data,
  onUpgrade,
}: {
  data: StoreProfileResponse;
  onUpgrade: () => void;
}) {
  return (
    <div className="space-y-4">
      {/* Teasers */}
      <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2 mb-4">
          <Building2 className="w-4 h-4" style={{ color: "#FFB224" }} />
          <h4 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Catalog structure</h4>
        </div>
        <div className="grid grid-cols-2 gap-x-6">
          <div>
            <p className="text-2xl font-bold font-mono" style={{ color: "var(--text)" }}>
              {data.collection_count ?? "—"}
            </p>
            <p className="text-xs" style={{ color: "var(--muted)" }}>collections</p>
          </div>
          <div className="space-y-0.5">
            <Signal active={!!data.has_sale_collection} label="Sale collection" />
            <Signal active={!!data.has_new_arrivals} label="New arrivals" />
            <Signal active={!!data.has_best_sellers} label="Best sellers" />
          </div>
        </div>
      </div>

      <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-4 h-4" style={{ color: "#FFB224" }} />
          <h4 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Brand signals</h4>
        </div>
        <Signal active={!!data.has_wholesale} label="Wholesale / B2B channel" />
        <Signal active={!!data.has_blog} label="Publishes a blog" />
        {data.content_investment_score != null && (
          <div className="mt-3">
            <ScoreBar score={data.content_investment_score} />
          </div>
        )}
      </div>

      {/* Upgrade CTA */}
      <div
        className="rounded-2xl p-6 text-center"
        style={{ background: "rgba(255,178,36,.06)", border: "1px dashed rgba(255,178,36,.3)" }}
      >
        <Lock className="w-5 h-5 mx-auto mb-2" style={{ color: "#FFB224" }} />
        <p className="text-sm font-medium mb-1" style={{ color: "var(--text)" }}>
          Full brand intelligence locked
        </p>
        <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
          Unlock all collection names, wholesale/affiliate/press signals, content
          strategy, and how to use each one against them.
        </p>
        <button
          onClick={onUpgrade}
          className="font-semibold text-sm px-5 py-2.5 rounded-xl transition-all hover:brightness-110"
          style={{ background: "#FFB224", color: "#0B0C0A" }}
        >
          Unlock Brand Intelligence
        </button>
      </div>
    </div>
  );
}

// ── Pro/Agency view ──────────────────────────────────────────────────────────

function CollectionTag({ name }: { name: string }) {
  const lower = name.toLowerCase();
  const isSale = lower.includes("sale") || lower.includes("clearance");
  const isNew = lower.includes("new") || lower.includes("arrival");
  const isBest = lower.includes("best") || lower.includes("popular") || lower.includes("trend");
  const isBundle = lower.includes("bundle") || lower.includes("kit") || lower.includes("combo");

  const accent = isSale ? "#F2555A" : isNew ? "#FFB224" : isBest ? "#FFB224" : isBundle ? "#7DB8C9" : undefined;

  return (
    <span
      className="text-xs px-2 py-1 rounded-md"
      style={{
        background: accent ? `${accent}18` : "var(--bg3)",
        color: accent ?? "var(--muted)",
      }}
    >
      {name}
    </span>
  );
}

function ProView({ data }: { data: StoreProfileResponse }) {
  const col = data.collection_intel;
  const brand = data.brand_signals;
  const content = data.content_intel;

  return (
    <div className="space-y-5">
      {/* Collections */}
      {col && (
        <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4" style={{ color: "#FFB224" }} />
              <h4 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Collections ({col.count})</h4>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-8 mb-4">
            <div>
              <Signal active={col.has_sale} label="Sale collection" />
              <Signal active={col.has_new_arrivals} label="New arrivals" />
              <Signal active={col.has_best_sellers} label="Best sellers" />
            </div>
            <div>
              <Signal active={col.has_bundles} label="Bundles / kits" />
              <Signal active={col.has_subscription} label="Subscription" />
              <Signal active={col.has_gift} label="Gift shop" />
            </div>
          </div>

          {col.names.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-3 border-t" style={{ borderColor: "var(--border)" }}>
              {col.names.map((name) => <CollectionTag key={name} name={name} />)}
            </div>
          )}
        </div>
      )}

      {/* Brand signals */}
      {brand && (
        <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2 mb-3">
            <ChevronRight className="w-4 h-4" style={{ color: "#FFB224" }} />
            <h4 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Brand signals ({brand.page_count} pages)</h4>
          </div>
          <div className="grid grid-cols-2 gap-x-8">
            <div>
              <Signal active={brand.has_wholesale} label="Wholesale / B2B" />
              <Signal active={brand.has_affiliate} label="Affiliate / ambassador" />
              <Signal active={brand.has_press} label="Press / media page" />
            </div>
            <div>
              <Signal active={brand.has_sustainability} label="Sustainability page" />
              <Signal active={brand.has_size_guide} label="Size guide" />
              <Signal active={brand.has_rewards} label="Rewards / loyalty" />
            </div>
          </div>
        </div>
      )}

      {/* Content intelligence */}
      {content && (
        <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-4 h-4" style={{ color: "#7DB8C9" }} />
            <h4 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Content intelligence</h4>
          </div>
          <ScoreBar score={content.content_investment_score} />
          <div className="mt-4 grid grid-cols-2 gap-4 text-center">
            <div>
              <p className="text-xl font-bold font-mono" style={{ color: "var(--text)" }}>{content.blog_count}</p>
              <p className="text-xs" style={{ color: "var(--muted)" }}>blog{content.blog_count !== 1 ? "s" : ""}</p>
            </div>
            <div>
              <p className="text-xl font-bold font-mono" style={{ color: "var(--text)" }}>{content.sampled_article_count}</p>
              <p className="text-xs" style={{ color: "var(--muted)" }}>recent articles</p>
            </div>
          </div>
          {content.recent_article_titles.length > 0 && (
            <div className="mt-4 pt-3 border-t space-y-1.5" style={{ borderColor: "var(--border)" }}>
              <p className="text-xs font-medium mb-2" style={{ color: "var(--muted)" }}>Recent articles</p>
              {content.recent_article_titles.map((title, i) => (
                <p key={i} className="text-sm" style={{ color: "var(--text)" }}>· {title}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Fallback if all Pro fields are unexpectedly missing */}
      {!col && !brand && !content && (
        <div className="rounded-2xl p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <p style={{ color: "var(--muted)" }}>Brand profile data will appear after the next full rescan.</p>
        </div>
      )}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function StoreProfileTab({ competitorId }: { competitorId: string }) {
  const [data, setData] = useState<StoreProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  useEffect(() => {
    api.storeProfile(competitorId)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [competitorId]);

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => <div key={i} className="h-32 rounded-2xl animate-pulse" style={{ background: "var(--bg-card)" }} />)}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-2xl p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <p style={{ color: "var(--muted)" }}>Brand profile not available yet. Trigger a rescan to collect this data.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2">
        <Building2 className="w-5 h-5 mt-0.5" style={{ color: "#FFB224" }} />
        <div>
          <h3 className="font-semibold" style={{ color: "var(--text)" }}>Brand Intelligence</h3>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            How they organize their catalog, what channels they operate, and how much they invest in content.
            Scraped from public collections, pages, and blog endpoints.
          </p>
        </div>
      </div>

      {data.locked
        ? <FreeTierView data={data} onUpgrade={() => setUpgradeOpen(true)} />
        : <ProView data={data} />
      }

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
