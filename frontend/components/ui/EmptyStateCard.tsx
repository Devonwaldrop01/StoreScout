"use client";

import Link from "next/link";

interface EmptyStateCardProps {
  icon?: React.ElementType;
  headline: string;
  body: string;
  hint?: string;
  examples?: Array<{ icon?: string; text: string }>;
  cta_label?: string;
  cta_href?: string;
  cta_onClick?: () => void;
}

export function EmptyStateCard({ icon: Icon, headline, body, hint, examples, cta_label, cta_href, cta_onClick }: EmptyStateCardProps) {
  return (
    <div
      className="rounded-md p-8 text-center fade-in"
      style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
    >
      {Icon && (
        <div
          className="w-10 h-10 rounded-md flex items-center justify-center mx-auto mb-4"
          style={{ background: "rgba(255,255,255,.04)", border: "1px solid var(--border)" }}
        >
          <Icon className="w-5 h-5" style={{ color: "var(--muted)" }} />
        </div>
      )}

      <h3 className="text-sm font-semibold mb-2" style={{ color: "var(--text)" }}>{headline}</h3>
      <p className="text-xs leading-relaxed max-w-xs mx-auto" style={{ color: "var(--muted)" }}>{body}</p>

      {hint && examples && examples.length > 0 && (
        <div className="mt-5 text-left max-w-xs mx-auto">
          <p className="label-caps mb-2">{hint}</p>
          <div className="space-y-1.5 opacity-40 pointer-events-none select-none">
            {examples.map((ex, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                {ex.icon && <span className="text-base">{ex.icon}</span>}
                <span className="text-xs" style={{ color: "var(--text-2)" }}>{ex.text}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {cta_label && (cta_href || cta_onClick) && (
        <div className="mt-6">
          {cta_href ? (
            <Link
              href={cta_href}
              className="inline-flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-lg transition-all hover:brightness-110"
              style={{ background: "var(--accent)", color: "var(--ink)" }}
            >
              {cta_label}
            </Link>
          ) : (
            <button
              onClick={cta_onClick}
              className="inline-flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-lg transition-all hover:brightness-110"
              style={{ background: "var(--accent)", color: "var(--ink)" }}
            >
              {cta_label}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
