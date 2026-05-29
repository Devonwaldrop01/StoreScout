"use client";

import Link from "next/link";

interface ScoutBriefProps {
  narrative: string | null;
  cta_label: string;
  cta_href: string;
  stats: Array<{ label: string; value: string }>;
}

export function ScoutBrief({ narrative, cta_label, cta_href, stats }: ScoutBriefProps) {
  return (
    <div className="mb-5 pb-5" style={{ borderBottom: "1px solid var(--border)" }}>
      <div className="flex items-start justify-between gap-4">
        <p className="text-sm font-medium leading-relaxed" style={{ color: "var(--text-2)" }}>
          {narrative ?? "Monitoring your competitors. Signals will appear when they make moves."}
        </p>
        <Link
          href={cta_href}
          className="shrink-0 text-sm font-semibold px-4 py-2 rounded-lg transition-all hover:brightness-110"
          style={{ background: "var(--accent)", color: "#ffffff" }}
        >
          {cta_label}
        </Link>
      </div>
      {stats.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2.5">
          {stats.map((s, i) => (
            <span key={i} className="text-[11px]" style={{ color: "var(--muted)" }}>
              {i > 0 && <span className="mr-3">·</span>}
              <span className="font-semibold tabular-nums" style={{ color: "var(--text-2)" }}>{s.value}</span>
              {" "}{s.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
