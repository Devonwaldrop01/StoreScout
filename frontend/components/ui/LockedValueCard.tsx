"use client";

import { Lock } from "lucide-react";
import Link from "next/link";

interface LockedValueCardProps {
  title: string;
  teaser: string;
  plan?: "pro" | "agency";
}

export function LockedValueCard({ title, teaser, plan = "pro" }: LockedValueCardProps) {
  const planLabel = plan === "agency" ? "Agency" : "Pro";
  return (
    <div
      className="rounded-xl px-5 py-4"
      style={{ background: "rgba(59,130,246,.04)", border: "1px solid rgba(59,130,246,.14)" }}
    >
      <div className="flex items-center gap-2 mb-2">
        <Lock className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--accent)" }} />
        <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>{title}</span>
      </div>
      <p className="text-xs leading-relaxed mb-3" style={{ color: "var(--muted)" }}>{teaser}</p>
      <Link
        href="/settings?tab=billing"
        className="text-xs font-semibold transition-opacity hover:opacity-70"
        style={{ color: "var(--accent)" }}
      >
        Unlock with {planLabel} →
      </Link>
    </div>
  );
}
