"use client";

import { useEffect, useState } from "react";
import { Lock, Trophy, Sparkles, ExternalLink } from "lucide-react";
import { competitors as api, type WinningProductsResponse, type WinningProduct } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import UpgradeModal from "@/components/UpgradeModal";

function scoreColor(score: number): string {
  if (score >= 75) return "#a3f000";
  if (score >= 50) return "#facc15";
  return "#94a3b8";
}

function ScoreBadge({ score }: { score: number }) {
  const color = scoreColor(score);
  return (
    <div className="flex flex-col items-center shrink-0" style={{ width: 52 }}>
      <span className="text-lg font-bold font-mono" style={{ color }}>{score}</span>
      <span className="text-[10px]" style={{ color: "var(--muted)" }}>/ 100</span>
    </div>
  );
}

function ProductImage({ src, title }: { src?: string | null; title?: string }) {
  if (!src) {
    return (
      <div
        className="w-12 h-12 rounded-lg shrink-0 flex items-center justify-center"
        style={{ background: "var(--bg3)" }}
      >
        <Trophy className="w-4 h-4" style={{ color: "var(--muted)" }} />
      </div>
    );
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={title || ""} className="w-12 h-12 rounded-lg object-cover shrink-0" style={{ background: "var(--bg3)" }} />;
}

function WinningRow({ product, rank }: { product: WinningProduct; rank: number }) {
  return (
    <div className="flex items-center gap-3 py-3 border-b" style={{ borderColor: "var(--border)" }}>
      <span className="text-sm font-mono w-5 shrink-0" style={{ color: "var(--muted)" }}>{rank}</span>
      <ProductImage src={product.image} title={product.title} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <p className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>
            {product.title || "Untitled product"}
          </p>
          {product.product_url && (
            <a href={product.product_url} target="_blank" rel="noopener noreferrer" className="shrink-0">
              <ExternalLink className="w-3 h-3" style={{ color: "var(--muted)" }} />
            </a>
          )}
        </div>
        <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
          {formatPrice(product.price_min)} · {product.reason}
        </p>
        {product.signal_tags && product.signal_tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {product.signal_tags.map((t) => (
              <span
                key={t}
                className="text-[10px] px-1.5 py-0.5 rounded-md"
                style={{ background: "rgba(163,240,0,.1)", color: "#a3f000" }}
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
      <ScoreBadge score={product.score} />
    </div>
  );
}

export default function WinningProductsTab({ competitorId }: { competitorId: string }) {
  const [data, setData] = useState<WinningProductsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  useEffect(() => {
    api.winningProducts(competitorId)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [competitorId]);

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => <div key={i} className="h-16 rounded-2xl animate-pulse" style={{ background: "var(--bg-card)" }} />)}
      </div>
    );
  }

  if (!data || data.products.length === 0) {
    return (
      <div className="rounded-2xl p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <p style={{ color: "var(--muted)" }}>No products to score yet. Check back after the next scan.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-2">
        <Trophy className="w-5 h-5 mt-0.5" style={{ color: "#a3f000" }} />
        <div>
          <h3 className="font-semibold" style={{ color: "var(--text)" }}>Winning Products</h3>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Ranked by signals that usually mean a product is selling — variant depth, catalog longevity,
            full-price confidence, and stock health.
          </p>
        </div>
      </div>

      {/* Ranked list */}
      <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        {data.products.map((p, i) => <WinningRow key={p.handle || i} product={p} rank={i + 1} />)}

        {/* Locked CTA for free users */}
        {data.locked && data.locked_count > 0 && (
          <div
            className="mt-4 rounded-xl p-5 text-center"
            style={{ background: "rgba(163,240,0,.06)", border: "1px dashed rgba(163,240,0,.3)" }}
          >
            <Lock className="w-5 h-5 mx-auto mb-2" style={{ color: "#a3f000" }} />
            <p className="text-sm font-medium mb-1" style={{ color: "var(--text)" }}>
              {data.locked_count} more winning products identified
            </p>
            <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
              Unlock the full ranking, the signal breakdown, and why each product is winning.
            </p>
            <button
              onClick={() => setUpgradeOpen(true)}
              className="font-semibold text-sm px-5 py-2.5 rounded-xl transition-all hover:brightness-110"
              style={{ background: "#a3f000", color: "#060d18" }}
            >
              Unlock Winning Products
            </button>
          </div>
        )}
      </div>

      {/* Newest products (paid) */}
      {data.newest && data.newest.length > 0 && (
        <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4" style={{ color: "#60a5fa" }} />
            <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Newest launches</h3>
          </div>
          {data.newest.map((p, i) => (
            <div key={i} className="flex items-center gap-3 py-2.5 border-b" style={{ borderColor: "var(--border)" }}>
              <ProductImage src={p.image} title={p.title} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>{p.title || "Untitled"}</p>
                <p className="text-xs" style={{ color: "var(--muted)" }}>
                  {formatPrice(p.price_min)} · launched {p.age_days}d ago
                </p>
              </div>
              {p.product_url && (
                <a href={p.product_url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="w-3.5 h-3.5" style={{ color: "var(--muted)" }} />
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
