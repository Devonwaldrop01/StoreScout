"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronUp } from "lucide-react";
import { type SignalGroup, SIGNAL_CONFIG } from "@/lib/signals";
import { type AlertEvent } from "@/lib/api";
import { SignalCard } from "./SignalCard";
import { formatRelativeTime, formatPrice, formatDelta, changeTypeIcon } from "@/lib/utils";
import { cn } from "@/lib/utils";

// ── Tactical group row ────────────────────────────────────────────────────

function TacticalGroup({ group }: { group: SignalGroup }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = SIGNAL_CONFIG[group.type];

  return (
    <div
      className="rounded-xl overflow-hidden mb-2"
      style={{ border: `1px solid ${cfg.border}`, background: cfg.bg }}
    >
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-black/10 transition-colors"
      >
        <span className="text-sm leading-none shrink-0">{cfg.icon}</span>
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
          <p className="text-xs font-semibold mt-0.5" style={{ color: "var(--text-2)" }}>
            {group.label}
          </p>
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
  const icon = changeTypeIcon(event.change_type);
  const ov = (event.old_value || {}) as Record<string, unknown>;
  const nv = (event.new_value || {}) as Record<string, unknown>;

  let detail = "";
  if (event.change_type === "price_change" && event.delta_pct != null) {
    detail = `${formatPrice(ov.price as number)} → ${formatPrice(nv.price as number)} (${formatDelta(event.delta_pct)})`;
  } else if (event.change_type === "new_product" && nv.price_min) {
    detail = formatPrice(nv.price_min as number);
  }

  const severityColor =
    event.severity === "critical" ? "var(--red)" :
    event.severity === "warning" ? "var(--amber)" : "transparent";

  return (
    <Link
      href={`/dashboard/${event.competitor_id}`}
      className={cn(
        "flex items-start gap-3 py-2.5 border-b last:border-0 transition-colors hover:bg-white/[0.02]",
        indent ? "px-4" : "px-3"
      )}
      style={{ borderColor: "var(--border)", borderLeft: `2px solid ${severityColor}` }}
    >
      <span className="text-sm leading-none mt-0.5 shrink-0">{icon}</span>
      <div className="flex-1 min-w-0">
        {!indent && (
          <p className="text-[11px] font-semibold mb-0.5" style={{ color: "var(--muted)" }}>
            {event.hostname}
          </p>
        )}
        <p className="text-xs truncate" style={{ color: "var(--text-2)" }}>
          {event.product_title || event.change_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        </p>
        {detail && (
          <p className="text-[11px] font-mono mt-0.5" style={{ color: "var(--blue)" }}>{detail}</p>
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
