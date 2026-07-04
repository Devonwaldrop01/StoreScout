"use client";

import { useEffect, useState, useCallback } from "react";
import { Bookmark, X, TrendingDown, TrendingUp } from "lucide-react";
import { watchlist as watchlistApi, type WatchedProduct } from "@/lib/api";
import { formatPrice } from "@/lib/utils";

interface Props {
  /** If set, only show pins for this competitor (used on the detail page). */
  competitorId?: string;
}

/** Pinned-product tracker. Shows each watched product's current price + the
 *  change since it was pinned, so a free user has a personal reason to return. */
export function WatchlistPanel({ competitorId }: Props) {
  const [items, setItems] = useState<WatchedProduct[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    watchlistApi.list()
      .then((r) => {
        const data = r.data || [];
        setItems(competitorId ? data.filter((w) => w.competitor_id === competitorId) : data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [competitorId]);

  useEffect(() => { load(); }, [load]);

  async function remove(id: string) {
    setItems((prev) => prev.filter((w) => w.id !== id));
    await watchlistApi.remove(id).catch(() => load());
  }

  if (loading) return null;

  return (
    <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2 mb-3">
        <Bookmark className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
        <h3 className="text-xs font-bold uppercase tracking-wide" style={{ color: "var(--text-2)" }}>Watching</h3>
      </div>

      {items.length === 0 ? (
        <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>
          Pin products from a competitor to track price &amp; stock changes here.
        </p>
      ) : (
        <div className="space-y-2">
          {items.map((w) => {
            const up = (w.delta_pct ?? 0) > 0;
            const down = (w.delta_pct ?? 0) < 0;
            return (
              <div key={w.id} className="flex items-center gap-2 group">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate" style={{ color: "var(--text)" }}>
                    {w.title || w.handle}
                  </p>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] font-mono" style={{ color: "var(--muted)" }}>
                      {w.removed ? "delisted" : w.current_price != null ? formatPrice(w.current_price) : "—"}
                    </span>
                    {w.delta_pct != null && w.delta_pct !== 0 && !w.removed && (
                      <span
                        className="text-[10px] font-bold inline-flex items-center gap-0.5"
                        style={{ color: down ? "var(--emerald)" : "var(--red)" }}
                      >
                        {down ? <TrendingDown className="w-2.5 h-2.5" /> : <TrendingUp className="w-2.5 h-2.5" />}
                        {up ? "+" : ""}{w.delta_pct}% since pinned
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => remove(w.id)}
                  className="p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                  style={{ color: "var(--muted)" }}
                  aria-label="Remove"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
