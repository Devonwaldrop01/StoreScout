"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

const FAQS = [
  {
    q: "Is tracking a competitor's Shopify store legal?",
    a: "Yes. StoreScout only reads publicly available product data from Shopify's public JSON endpoints — the same data any browser can access without logging in. We don't scrape private pages, checkout flows, or admin areas.",
  },
  {
    q: "Which stores can I track?",
    a: "Any store running Shopify with a public product catalog. This covers the vast majority of Shopify stores. A small number of stores restrict public product API access — we'll detect this and still attempt a scan.",
  },
  {
    q: "How current is the data?",
    a: "Free tier: manual scan on demand (max once per week). Pro and Agency: daily automatic scans with change detection running after every scan. Price changes and new products are detected within hours of the next scheduled scan.",
  },
  {
    q: "What happens when I hit my competitor limit?",
    a: "You'll see an upgrade prompt when you try to add more competitors than your plan allows. Your existing competitors keep scanning normally — nothing is paused or deleted.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. Cancel from your billing settings in one click — your account downgrades to Free at the end of your billing period and all your tracked data is preserved.",
  },
  {
    q: "Do you support non-Shopify stores?",
    a: "Not currently. Shopify's public products.json endpoint gives us structured, reliable data that makes pricing analysis possible. We may add WooCommerce and BigCommerce support in the future.",
  },
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
            className="w-full flex items-center justify-between px-6 py-4 text-left"
          >
            <span className="font-semibold text-sm pr-4" style={{ color: "var(--text)" }}>{q}</span>
            <ChevronDown
              className="w-4 h-4 shrink-0 transition-transform"
              style={{ color: "var(--muted)", transform: open === i ? "rotate(180deg)" : "none" }}
            />
          </button>
          {open === i && (
            <div className="px-6 pb-5 border-t" style={{ borderColor: "var(--border)" }}>
              <p className="text-sm leading-relaxed pt-4" style={{ color: "var(--muted)" }}>{a}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
