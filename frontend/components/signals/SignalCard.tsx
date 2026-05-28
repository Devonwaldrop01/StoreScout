"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp, ArrowRight } from "lucide-react";
import { type SignalGroup, SIGNAL_CONFIG } from "@/lib/signals";
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
      className="rounded-2xl overflow-hidden mb-3 fade-up"
      style={{
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        boxShadow: `0 0 0 1px ${cfg.border.replace(".25", ".06")}, 0 8px 32px rgba(0,0,0,.3)`,
      }}
    >
      {/* Header row */}
      <div className="flex items-center justify-between px-5 pt-4 pb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <Icon className="w-4 h-4 shrink-0" style={{ color: cfg.color }} />
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full shrink-0"
                style={{ background: `${cfg.color}20`, color: cfg.color }}
              >
                {group.headline}
              </span>
              <span className="text-xs font-semibold truncate" style={{ color: "var(--text)" }}>
                {group.hostname}
              </span>
            </div>
            <p className="text-sm font-bold mt-1 leading-snug" style={{ color: "var(--text)" }}>
              {group.label}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0 ml-3">
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

      {/* Why this matters */}
      {group.why_this_matters && (
        <div
          className="mx-5 mb-3 px-3.5 py-3 rounded-xl text-xs leading-relaxed"
          style={{ background: "rgba(0,0,0,.2)", color: "var(--text-2)" }}
        >
          <span className="font-semibold" style={{ color: cfg.color }}>Why this matters · </span>
          {group.why_this_matters}
        </div>
      )}

      {/* Your move */}
      {group.your_move && (
        <div
          className="mx-5 mb-3 px-3.5 py-3 rounded-xl text-xs leading-relaxed"
          style={{ background: "rgba(59,130,246,.05)", border: "1px solid rgba(59,130,246,.18)" }}
        >
          <span className="font-bold" style={{ color: "#3b82f6" }}>▶ Your move · </span>
          <span style={{ color: "var(--text-2)" }}>{group.your_move}</span>
        </div>
      )}

      {/* Metadata row */}
      <div className="flex items-center gap-4 px-5 pb-3">
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
        {group.category_hint && (
          <span
            className="text-[11px] px-2 py-0.5 rounded-full"
            style={{ background: `${cfg.color}15`, color: cfg.color }}
          >
            {group.category_hint}
          </span>
        )}
      </div>

      {/* Expandable product list */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-2.5 text-xs font-semibold transition-colors hover:bg-black/10"
        style={{
          borderTop: `1px solid ${cfg.border}`,
          color: "var(--muted)",
        }}
      >
        <span>{expanded ? "Hide" : `Show all ${group.count} products`}</span>
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {expanded && (
        <div style={{ borderTop: `1px solid ${cfg.border}` }}>
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
                  style={{ borderColor: cfg.border }}
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
                style={{ borderColor: cfg.border }}
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
