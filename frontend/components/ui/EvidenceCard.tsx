"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

interface EvidenceItem {
  icon?: React.ElementType;
  color?: string;
  label: string;
  detail?: string;
  time?: string;
}

interface EvidenceCardProps {
  title?: string;
  items: EvidenceItem[];
  maxVisible?: number;
}

export function EvidenceCard({ title, items, maxVisible = 5 }: EvidenceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? items : items.slice(0, maxVisible);
  const hidden = items.length - maxVisible;

  return (
    <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)", background: "var(--bg3)" }}>
      {title && (
        <div className="px-4 py-2.5" style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-card)" }}>
          <p className="label-caps">{title}</p>
        </div>
      )}
      {visible.map((item, i) => {
        const Icon = item.icon;
        const color = item.color ?? "var(--muted)";
        return (
          <div
            key={i}
            className="flex gap-3 px-4 py-2.5"
            style={i < visible.length - 1 ? { borderBottom: "1px solid var(--border)" } : undefined}
          >
            {Icon && (
              <div
                className="w-5 h-5 rounded-md flex items-center justify-center shrink-0 mt-0.5"
                style={{ background: `${color}18` }}
              >
                <Icon className="w-3 h-3" style={{ color }} />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium" style={{ color: "var(--text-2)" }}>{item.label}</p>
              {item.detail && (
                <p className="text-[11px] font-mono mt-0.5" style={{ color: "var(--muted)" }}>{item.detail}</p>
              )}
            </div>
            {item.time && (
              <span className="text-[11px] shrink-0 self-center" style={{ color: "var(--muted)" }}>{item.time}</span>
            )}
          </div>
        );
      })}
      {!expanded && hidden > 0 && (
        <button
          onClick={() => setExpanded(true)}
          className="w-full flex items-center justify-center gap-1.5 px-4 py-2.5 text-[11px] font-medium transition-colors hover:bg-white/[0.02]"
          style={{ color: "var(--muted)", borderTop: "1px solid var(--border)" }}
        >
          <ChevronDown className="w-3.5 h-3.5" />
          Show {hidden} more
        </button>
      )}
    </div>
  );
}
