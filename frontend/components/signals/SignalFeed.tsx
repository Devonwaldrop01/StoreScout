"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp } from "lucide-react";
import { type SignalGroup, SIGNAL_CONFIG } from "@/lib/signals";
import { formatDelta } from "@/lib/utils";
import { type AlertEvent } from "@/lib/api";
import { SignalCard } from "./SignalCard";
import { formatRelativeTime, formatPrice, formatPct, changeTypeIcon, changeTypeColor, changeTypeLabel } from "@/lib/utils";
import { cn } from "@/lib/utils";

// ── Tactical group row ────────────────────────────────────────────────────

function TacticalGroup({ group }: { group: SignalGroup }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = SIGNAL_CONFIG[group.type];
  const Icon = cfg.icon;

  return (
    <div
      className="rounded-xl overflow-hidden mb-2"
      style={{ border: `1px solid ${cfg.border}`, background: cfg.bg }}
    >
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-black/10 transition-colors"
      >
        <Icon className="w-3.5 h-3.5 shrink-0" style={{ color: cfg.color }} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="text-[10px] font-bold uppercase tracking-wider shrink-0"
              style={{ color: cfg.color }}
            >
              {group.headline}
            </span>
            <span className="text-xs truncate" style={{ color: "var(--muted)" }}>
              {group.hostname}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <p className="text-xs font-semibold" style={{ color: "var(--text-2)" }}>
              {group.label}
            </p>
            {group.avg_delta_pct != null && group.type !== "tactical_launches" && (
              <span className="text-[11px] font-mono" style={{ color: (group.avg_delta_pct ?? 0) < 0 ? "var(--red)" : "var(--emerald)" }}>
                avg {formatDelta(group.avg_delta_pct)}
              </span>
            )}
            {group.category_hint && (
              <span className="text-[11px]" style={{ color: "var(--muted)" }}>· {group.category_hint}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[11px]" style={{ color: "var(--muted)" }}>
            {formatRelativeTime(group.detected_at)}
          </span>
          {expanded
            ? <ChevronUp className="w-3.5 h-3.5" style={{ color: "var(--muted)" }} />
            : <ChevronDown className="w-3.5 h-3.5" style={{ color: "var(--muted)" }} />
          }
        </div>
      </button>

      {expanded && (
        <div style={{ borderTop: `1px solid ${cfg.border}` }}>
          {group.events.map((event) => (
            <RawEventRow key={event.id} event={event} indent />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Raw event row ─────────────────────────────────────────────────────────

function RawEventRow({ event, indent = false }: { event: AlertEvent; indent?: boolean }) {
  const Icon   = changeTypeIcon(event.change_type);
  const color  = changeTypeColor(event.change_type);
  const label  = changeTypeLabel(event.change_type);
  const ov = (event.old_value || {}) as Record<string, unknown>;
  const nv = (event.new_value || {}) as Record<string, unknown>;

  let detail = "";
  if (event.change_type === "price_change" && event.delta_pct != null) {
    detail = `${formatPrice(ov.price as number)} → ${formatPrice(nv.price as number)} (${formatDelta(event.delta_pct)})`;
  } else if (event.change_type === "new_product") {
    detail = nv.price_min ? `from ${formatPrice(nv.price_min as number)}` : "added to catalog";
  } else if (event.change_type === "product_removed") {
    detail = "removed from catalog";
  } else if (event.change_type === "discount_start") {
    const pct = nv.discounted_pct as number;
    detail = pct ? `${formatPct(pct)} of catalog on sale` : "markdown applied";
  } else if (event.change_type === "discount_end") {
    const pct = ov.discounted_pct as number;
    detail = pct ? `${formatPct(pct)} back to full price` : "sale ended";
  } else if (event.change_type === "availability_change") {
    const inStock = nv.available as boolean;
    detail = inStock === false ? "went out of stock" : inStock === true ? "back in stock" : "stock status changed";
  }

  const severityBorder =
    event.severity === "critical" ? "#f97316" :
    event.severity === "warning"  ? "var(--amber)" : "transparent";

  return (
    <Link
      href={`/dashboard/${event.competitor_id}`}
      className={cn(
        "flex items-start gap-3 py-2.5 border-b last:border-0 transition-colors hover:bg-white/[0.02]",
        indent ? "px-4" : "px-3"
      )}
      style={{ borderColor: "var(--border)", borderLeft: `2px solid ${severityBorder}` }}
    >
      <div
        className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 mt-0.5"
        style={{ background: `color-mix(in srgb, ${color} 12%, transparent)` }}
      >
        <Icon className="w-3 h-3" style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        {!indent && (
          <p className="text-[11px] font-semibold mb-0.5" style={{ color: "var(--muted)" }}>
            {event.hostname}
          </p>
        )}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold" style={{ color }}>{label}</span>
          {event.product_title && (
            <span className="text-xs truncate" style={{ color: "var(--text-2)" }}>
              · {event.product_title}
            </span>
          )}
        </div>
        {detail && (
          <p className="text-[11px] mt-0.5" style={{ color: "var(--muted)" }}>{detail}</p>
        )}
      </div>
      <span className="text-[11px] shrink-0" style={{ color: "var(--muted)" }}>
        {formatRelativeTime(event.detected_at)}
      </span>
    </Link>
  );
}

// ── Signal feed ───────────────────────────────────────────────────────────

interface Props {
  groups: SignalGroup[];
  loading?: boolean;
  maxRaw?: number;
}

export function SignalFeed({ groups, loading = false, maxRaw = 12 }: Props) {
  const [showAllRaw, setShowAllRaw] = useState(false);

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />
        ))}
      </div>
    );
  }

  if (groups.length === 0) return null;

  const strategic = groups.filter((g) => g.tier === "strategic");
  const tactical  = groups.filter((g) => g.tier === "tactical");
  const raw       = groups.filter((g) => g.tier === "raw");

  const visibleRaw = showAllRaw ? raw : raw.slice(0, maxRaw);
  const hiddenRawCount = raw.length - visibleRaw.length;

  return (
    <div>
      {/* Strategic signals */}
      {strategic.map((g) => (
        <SignalCard key={g.id} group={g} />
      ))}

      {/* Tactical groups */}
      {tactical.length > 0 && (
        <div className={strategic.length > 0 ? "mt-1" : ""}>
          {tactical.map((g) => (
            <TacticalGroup key={g.id} group={g} />
          ))}
        </div>
      )}

      {/* Raw events */}
      {raw.length > 0 && (tactical.length > 0 || strategic.length > 0) && (
        <div
          className="text-[11px] font-semibold uppercase tracking-widest mt-3 mb-2 px-1"
          style={{ color: "var(--muted)" }}
        >
          Individual events
        </div>
      )}
      {raw.length > 0 && (
        <div
          className="rounded-xl overflow-hidden"
          style={{ border: "1px solid var(--border)", background: "var(--bg3)" }}
        >
          {visibleRaw.map((g) => (
            <RawEventRow key={g.id} event={g.events[0]} />
          ))}
        </div>
      )}

      {hiddenRawCount > 0 && (
        <button
          onClick={() => setShowAllRaw(true)}
          className="w-full mt-2 py-2 text-xs font-semibold rounded-xl transition-colors hover:bg-white/[0.03]"
          style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
        >
          Show {hiddenRawCount} more
        </button>
      )}
    </div>
  );
}
