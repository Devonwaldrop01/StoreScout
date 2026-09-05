"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

const FAQS = [
  { q: "What does StoreScout read?", a: "StoreScout reads publicly accessible Shopify catalog data. It does not access a competitor’s admin, customer records, checkout or sales data. Public availability is not a guarantee that every use is permitted; use the results responsibly." },
  { q: "How often are stores checked?", a: "Pro checks every 24 hours and Agency every 12 hours. Free includes a manual scan up to once a week. Changes are detected by comparing completed scans; short promotions between checks may be missed. Email delivery follows scanning and notification preferences, and may be batched." },
  { q: "Which stores can I track?", a: "Shopify stores with an accessible public product catalog. Some stores restrict access or use unsupported storefronts. Scan results depend on catalog access; large catalogs may be partially scanned and coverage is labeled." },
  { q: "What do the recommendations establish?", a: "The underlying evidence is observed catalog data. AI summaries suggest interpretations and possible next steps; they do not establish sales, revenue, customer demand or the reason behind a competitor’s change." },
  { q: "What happens at my competitor limit?", a: "StoreScout shows an upgrade prompt when you reach your plan’s active-competitor limit. Review your tracked stores or choose a plan with a higher limit in Settings." },
  { q: "How do I manage billing?", a: "Use Manage billing in Settings to open Stripe’s billing portal and review your subscription or cancellation options." },
  { q: "Do you support Amazon or TikTok Shop catalogs?", a: "No. The current monitoring workflow supports accessible Shopify storefront catalogs. A brand may also sell on other channels, but StoreScout does not monitor those marketplace listings." },
];

export function FaqAccordion() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <div className="space-y-2">
      {FAQS.map(({ q, a }, i) => (
        <div
          key={i}
          className="rounded-2xl overflow-hidden"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <button
            onClick={() => setOpen(open === i ? null : i)}
            aria-expanded={open === i}
            aria-controls={`faq-answer-${i}`}
            className="w-full flex items-center justify-between px-6 py-4 text-left"
          >
            <span className="font-semibold text-sm pr-4" style={{ color: "var(--text)" }}>{q}</span>
            <ChevronDown
              className="w-4 h-4 shrink-0 transition-transform"
              style={{ color: "var(--muted)", transform: open === i ? "rotate(180deg)" : "none" }}
            />
          </button>
          {open === i && (
            <div id={`faq-answer-${i}`} className="px-6 pb-5 border-t" style={{ borderColor: "var(--border)" }}>
              <p className="text-sm leading-relaxed pt-4" style={{ color: "var(--muted)" }}>{a}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
