"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, ArrowRight } from "lucide-react";
import { type SignalGroup, SIGNAL_CONFIG, impactLevel } from "@/lib/signals";
import { formatRelativeTime, formatPrice, formatDelta } from "@/lib/utils";

interface Props {
  group: SignalGroup;
}

export function SignalCard({ group }: Props) {
  const [expanded, setExpanded] = useState(false);
  const cfg = SIGNAL_CONFIG[group.type];
  const Icon = cfg.icon;

  return (
    <div
      className="rounded-xl overflow-hidden mb-2.5 fade-up"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderLeft: `3px solid ${cfg.color}`,
      }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between px-4 pt-3.5 pb-2.5">
        <div className="flex items-start gap-2.5 min-w-0">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
            style={{ background: `${cfg.color}1a` }}
          >
            <Icon className="w-3.5 h-3.5" style={{ color: cfg.color }} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold shrink-0" style={{ color: cfg.color }}>
                {group.headline}
              </span>
              <span className="text-xs truncate" style={{ color: "var(--muted)" }}>
                {group.hostname}
              </span>
            </div>
            <p className="text-sm font-semibold mt-0.5 leading-snug" style={{ color: "var(--text)" }}>
              {group.label}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-3">
          <span className="text-[11px]" style={{ color: "var(--muted)" }}>
            {formatRelativeTime(group.detected_at)}
          </span>
          <Link
            href={`/dashboard/${group.competitor_id}`}
            className="p-1.5 rounded-lg transition-colors hover:bg-white/10"
            style={{ color: "var(--muted)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Your move — always visible, action-first */}
      {group.your_move && (
        <div
          className="mx-4 mb-2.5 px-3 py-2.5 rounded-lg text-xs leading-relaxed"
          style={{ background: "rgba(255,178,36,.06)", border: "1px solid rgba(255,178,36,.16)" }}
        >
          <span className="font-bold" style={{ color: "var(--accent)" }}>▶ Your move · </span>
          <span style={{ color: "var(--text-2)" }}>{group.your_move}</span>
        </div>
      )}

      {/* Why this matters — context, capped at 2 lines */}
      {group.why_this_matters && (
        <p
          className="mx-4 mb-2.5 px-3 py-2 rounded-lg text-xs leading-relaxed line-clamp-2"
          style={{ background: "var(--bg3)", color: "var(--muted)" }}
        >
          <span className="font-semibold" style={{ color: "var(--text-2)" }}>Why · </span>
          {group.why_this_matters}
        </p>
      )}

      {/* Impact + Category badges (strategic signals only) */}
      {group.tier === "strategic" && (() => {
        const level = impactLevel(group);
        const [impactBg, impactColor] =
          level === "High"   ? ["rgba(242,85,90,.12)",   "var(--red)"]   :
          level === "Medium" ? ["rgba(255,178,36,.12)",  "var(--amber)"] :
                               ["rgba(100,112,137,.12)", "var(--muted)"];
        return (
          <div className="flex items-center gap-1.5 px-4 pb-2">
            <span className="text-[10px] font-bold px-2 py-0.5 rounded" style={{ background: impactBg, color: impactColor }}>
              Impact: {level}
            </span>
            {group.category_hint && (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded" style={{ background: "var(--bg3)", color: "var(--muted)", border: "1px solid var(--border)" }}>
                {group.category_hint}
              </span>
            )}
          </div>
        );
      })()}

      {/* Metadata row */}
      {(group.avg_price != null || (group.avg_delta_pct != null && group.type !== "launch_burst") || (group.tier !== "strategic" && group.category_hint)) && (
        <div className="flex items-center gap-4 px-4 pb-3">
          {group.avg_price != null && (
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              Avg price: <span className="font-mono font-semibold" style={{ color: "var(--text-2)" }}>{formatPrice(group.avg_price)}</span>
            </span>
          )}
          {group.avg_delta_pct != null && group.type !== "launch_burst" && (
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              Avg change: <span className="font-mono font-semibold" style={{ color: (group.avg_delta_pct ?? 0) < 0 ? "var(--red)" : "var(--emerald)" }}>{formatDelta(group.avg_delta_pct)}</span>
            </span>
          )}
          {group.tier !== "strategic" && group.category_hint && (
            <span className="text-[11px] px-2 py-0.5 rounded-md" style={{ background: "var(--bg3)", color: "var(--muted)" }}>
              {group.category_hint}
            </span>
          )}
        </div>
      )}

      {/* Expandable product list */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-medium transition-colors hover:bg-white/[0.02]"
        style={{
          borderTop: "1px solid var(--border)",
          color: "var(--muted)",
        }}
      >
        <span>{expanded ? "Hide" : `Show all ${group.count} products`}</span>
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {expanded && (
        <div style={{ borderTop: "1px solid var(--border)" }}>
          {group.events.flatMap((event) => {
            const nv = (event.new_value || {}) as Record<string, unknown>;
            const ov = (event.old_value || {}) as Record<string, unknown>;
            const isBulk = event.change_type === "bulk_removal" ||
                           event.change_type === "bulk_new_products" ||
                           event.change_type === "bulk_price_change";

            if (isBulk) {
              const sample = (ov.sample as Array<{ title?: string; handle?: string; price?: number }> | undefined) ?? [];
              const totalCount = typeof ov.count === "number" ? ov.count : sample.length;
              const remaining = totalCount - sample.length;
              const rows = sample.map((item, i) => (
                <div
                  key={`${event.id}-${i}`}
                  className="flex items-start justify-between gap-3 px-5 py-2.5 border-b"
                  style={{ borderColor: "var(--border)" }}
                >
                  <p className="text-xs font-medium truncate" style={{ color: "var(--text-2)" }}>
                    {item.title || item.handle || "Product"}
                  </p>
                  {item.price != null && (
                    <span className="text-[11px] font-mono shrink-0" style={{ color: "var(--muted)" }}>
                      {formatPrice(item.price)}
                    </span>
                  )}
                </div>
              ));
              if (remaining > 0) {
                rows.push(
                  <div key={`${event.id}-more`} className="px-5 py-2">
                    <span className="text-[11px]" style={{ color: "var(--muted)" }}>…and {remaining} more</span>
                  </div>
                );
              }
              return rows;
            }

            let detail = "";
            if (event.change_type === "price_change" && event.delta_pct != null) {
              detail = `${formatPrice(ov.price as number)} → ${formatPrice(nv.price as number)} (${formatDelta(event.delta_pct)})`;
            } else if (nv.price_min) {
              detail = formatPrice(nv.price_min as number);
            }
            return [(
              <div
                key={event.id}
                className="flex items-start justify-between gap-3 px-5 py-2.5 border-b last:border-0"
                style={{ borderColor: "var(--border)" }}
              >
                <div className="min-w-0">
                  <p className="text-xs font-medium truncate" style={{ color: "var(--text-2)" }}>
                    {event.product_title || event.change_type}
                  </p>
                  {detail && (
                    <p className="text-[11px] font-mono mt-0.5" style={{ color: "var(--muted)" }}>{detail}</p>
                  )}
                </div>
                <span className="text-[11px] shrink-0" style={{ color: "var(--muted)" }}>
                  {formatRelativeTime(event.detected_at)}
                </span>
              </div>
            )];
          })}
        </div>
      )}
    </div>
  );
}
