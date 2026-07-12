"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

const FAQS = [
  {
    q: "Is tracking a competitor's Shopify store legal?",
    a: "Yes. StoreScout only reads publicly available product data from Shopify's public JSON endpoints — the same data any browser can access without logging in. We don't scrape private pages, checkout flows, or admin areas. Thousands of businesses use publicly available competitor pricing data as a standard business practice.",
  },
  {
    q: "How fast are the alerts? Can I really act on them?",
    a: "Yes — alerts fire within 15 minutes of a scan completing, and Pro/Agency plans scan daily. If a competitor drops prices at 9am, you'll know by 9:15. We've had users match a competitor's flash sale the same morning it started.",
  },
  {
    q: "Which stores can I track?",
    a: "Any store running Shopify with a public product catalog — which is the vast majority of Shopify stores. A small number restrict public access; we'll tell you immediately when you add the URL. There's no limit on which stores you can enter, only on how many you can track simultaneously.",
  },
  {
    q: "How current is the data?",
    a: "Free tier: one automatic scan per week, plus on-demand rescans whenever you want. Pro and Agency: daily automatic scans (Agency twice daily) with change detection running after every scan. Price changes and new products are detected at the next scan — same-day on paid plans.",
  },
  {
    q: "What does the AI digest actually tell me?",
    a: "Every Monday, Claude writes a 4–6 sentence strategic summary for each competitor you track. It covers the most significant change pattern from the past week, what it likely signals about their strategy, and one specific action you could consider. It's written to be read in 20 seconds — not a report.",
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
    a: "Not currently. Shopify's public products.json endpoint gives us structured, reliable data that makes pricing analysis possible at this depth. WooCommerce and BigCommerce are on the roadmap.",
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
