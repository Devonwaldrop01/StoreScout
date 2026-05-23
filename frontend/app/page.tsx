import Link from "next/link";
import { Zap, TrendingUp, Bell, Cpu, ArrowRight, Check, Shield, Clock, BarChart3, Package, Tag } from "lucide-react";

// ── Static data ───────────────────────────────────────────────────────────────

const FEATURES = [
  { icon: BarChart3, title: "Full catalog intelligence", desc: "Price distribution, median, min/max, and percentile breakdowns across every product in the store." },
  { icon: Bell, title: "Instant change alerts", desc: "Detected within 15 minutes of a scan. Flash sales, price drops ≥10%, and new product launches trigger emails automatically." },
  { icon: TrendingUp, title: "Launch velocity tracking", desc: "See how many products they're launching per month and whether they're accelerating or pulling back." },
  { icon: Cpu, title: "AI weekly digest", desc: "Every Monday, Claude analyzes your competitor data and writes a 4–6 sentence strategic summary of what changed and what it likely signals." },
  { icon: Tag, title: "Discount monitoring", desc: "Track what percentage of their catalog is on sale, the median discount depth, and when new sale events start or end." },
  { icon: Package, title: "Quick Wins", desc: "Automatically surfaced opportunities: price gaps to exploit, discount dependence signals, stalled launches, and catalog stock gaps." },
];

const PLANS = [
  {
    name: "Free",
    price: "$0",
    sub: "forever",
    highlight: false,
    features: ["1 competitor", "Weekly manual scan", "Current snapshot only", "In-app change history", "No credit card required"],
    cta: "Start free",
    href: "/auth/signup",
  },
  {
    name: "Pro",
    price: "$29",
    sub: "/month",
    highlight: true,
    features: ["10 competitors", "Daily auto-scans", "90-day price history", "Email + in-app alerts", "Weekly AI digest", "Quick Wins analysis"],
    cta: "Start Pro",
    href: "/auth/signup?plan=pro",
  },
  {
    name: "Agency",
    price: "$79",
    sub: "/month",
    highlight: false,
    features: ["50 competitors", "Daily auto-scans", "Unlimited history", "Email + in-app alerts", "Weekly AI digest", "Shareable report URLs"],
    cta: "Start Agency",
    href: "/auth/signup?plan=agency",
  },
];

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
];

// ── Components ────────────────────────────────────────────────────────────────

function ProductPreview() {
  const kpis = [
    ["Products", "2,500"],
    ["Median Price", "$45.00"],
    ["Promo Rate", "12.3%"],
    ["New (30d)", "47"],
  ];
  const events = [
    { icon: "📉", title: "Hooded Sweatshirt Slim", detail: "$65.00 → $52.00 (−20%)", color: "#facc15", border: "rgba(250,204,21,.3)", time: "2h ago" },
    { icon: "🆕", title: "Lifting Belt Pro Series", detail: "New product · $89.99", color: "#60a5fa", border: "rgba(96,165,250,.2)", time: "5h ago" },
    { icon: "🏷️", title: "Summer Sale started", detail: "+18 pp of catalog now discounted", color: "#a3f000", border: "rgba(163,240,0,.2)", time: "1d ago" },
  ];

  return (
    <div
      className="rounded-2xl overflow-hidden shadow-2xl"
      style={{ background: "#060d18", border: "1px solid #1e3a5f" }}
    >
      {/* Browser chrome */}
      <div
        className="flex items-center gap-3 px-4 py-3 border-b"
        style={{ background: "#0a1628", borderColor: "#1e3a5f" }}
      >
        <div className="flex gap-1.5">
          <span className="w-3 h-3 rounded-full" style={{ background: "#f87171" }} />
          <span className="w-3 h-3 rounded-full" style={{ background: "#facc15" }} />
          <span className="w-3 h-3 rounded-full" style={{ background: "#22c55e" }} />
        </div>
        <div
          className="flex-1 mx-3 rounded-md px-3 py-1 text-xs font-mono"
          style={{ background: "#060d18", color: "#4a6080" }}
        >
          app.storescout.com/dashboard/gymshark
        </div>
      </div>

      <div className="p-5">
        {/* KPI strip */}
        <div className="grid grid-cols-4 gap-2 mb-4">
          {kpis.map(([label, value]) => (
            <div
              key={label}
              className="rounded-xl p-3"
              style={{ background: "#0e1d35", border: "1px solid #1e3a5f" }}
            >
              <p className="text-xs mb-1" style={{ color: "#4a6080" }}>{label}</p>
              <p className="text-base font-bold font-mono" style={{ color: "#eef3fa" }}>{value}</p>
            </div>
          ))}
        </div>

        {/* Alert rows */}
        <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "#4a6080" }}>Recent activity</p>
        <div className="space-y-2">
          {events.map(({ icon, title, detail, color, border, time }) => (
            <div
              key={title}
              className="flex items-center gap-3 rounded-xl p-3"
              style={{ background: "#0e1d35", border: `1px solid ${border}` }}
            >
              <span className="text-base shrink-0">{icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" style={{ color: "#eef3fa" }}>{title}</p>
                <p className="text-xs font-mono" style={{ color }}>{detail}</p>
              </div>
              <p className="text-xs shrink-0" style={{ color: "#4a6080" }}>{time}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      {/* Nav */}
      <nav
        className="sticky top-0 z-40 flex items-center justify-between px-6 md:px-12 py-4 border-b backdrop-blur-md"
        style={{ borderColor: "var(--border)", background: "rgba(6,13,24,.9)" }}
      >
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5" style={{ color: "#a3f000" }} />
          <span className="font-bold text-lg" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/auth/login" className="text-sm font-medium hover:opacity-80 transition-opacity hidden sm:block" style={{ color: "var(--muted)" }}>
            Sign in
          </Link>
          <Link
            href="/auth/signup"
            className="text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:brightness-110"
            style={{ background: "#a3f000", color: "#060d18" }}
          >
            Start free
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-5xl mx-auto px-6 pt-20 pb-16 text-center">
        <div
          className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-8"
          style={{ background: "rgba(163,240,0,.1)", color: "#a3f000", border: "1px solid rgba(163,240,0,.2)" }}
        >
          <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
          Trending on PeerPush
        </div>
        <h1
          className="text-4xl md:text-6xl font-black tracking-tight mb-6"
          style={{ color: "var(--text)", letterSpacing: "-0.04em", lineHeight: 1.05 }}
        >
          Always know what your<br />
          <span style={{ color: "#a3f000" }}>Shopify competitors</span><br />
          are doing.
        </h1>
        <p className="text-lg md:text-xl mb-10 max-w-2xl mx-auto" style={{ color: "var(--muted)", lineHeight: 1.6 }}>
          Track prices, product launches, and discount campaigns across any Shopify store. Get alerted within minutes when they make a move — automatically.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/auth/signup"
            className="flex items-center gap-2 font-bold px-8 py-4 rounded-2xl text-lg transition-all hover:brightness-110"
            style={{ background: "#a3f000", color: "#060d18" }}
          >
            Start tracking free
            <ArrowRight className="w-5 h-5" />
          </Link>
          <p className="text-sm" style={{ color: "var(--muted)" }}>No credit card required · Free forever</p>
        </div>
      </div>

      {/* Product preview */}
      <div className="max-w-4xl mx-auto px-6 pb-24">
        <ProductPreview />
      </div>

      {/* How it works */}
      <div className="max-w-5xl mx-auto px-6 pb-24">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Live in 60 seconds
          </h2>
          <p className="text-base" style={{ color: "var(--muted)" }}>No setup, no API keys, no spreadsheets.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-8 relative">
          {[
            { step: "01", title: "Paste any Shopify URL", desc: "Enter a competitor's store URL. We verify it's a Shopify store and kick off the first scan immediately." },
            { step: "02", title: "We scan their full catalog", desc: "StoreScout fetches their entire product catalog, analyzes pricing patterns, launch velocity, and discount strategy." },
            { step: "03", title: "Get alerted when they move", desc: "Price drops, new launches, sale events — you're notified by email within minutes. No manual checking required." },
          ].map(({ step, title, desc }) => (
            <div key={step} className="text-center">
              <div
                className="w-12 h-12 rounded-2xl flex items-center justify-center text-lg font-black mx-auto mb-4"
                style={{ background: "rgba(163,240,0,.1)", border: "1px solid rgba(163,240,0,.2)", color: "#a3f000" }}
              >
                {step}
              </div>
              <h3 className="font-bold mb-2" style={{ color: "var(--text)" }}>{title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <div className="max-w-5xl mx-auto px-6 pb-24">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Everything you need to stay ahead
          </h2>
          <p className="text-base" style={{ color: "var(--muted)" }}>Built for Shopify operators who make pricing and product decisions every week.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-5">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="rounded-2xl p-6"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center mb-4"
                style={{ background: "rgba(163,240,0,.1)" }}
              >
                <Icon className="w-5 h-5" style={{ color: "#a3f000" }} />
              </div>
              <h3 className="font-bold mb-2" style={{ color: "var(--text)" }}>{title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Trust signals */}
      <div className="max-w-5xl mx-auto px-6 pb-24">
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { icon: Shield, label: "Public data only", desc: "Only reads Shopify's public product endpoints — no login, no private data." },
            { icon: Clock, label: "Daily auto-scans", desc: "Pro and Agency plans scan automatically every 24 hours. Set it and forget it." },
            { icon: Zap, label: "Alerts within minutes", desc: "Change detection runs immediately after each scan — you hear about it fast." },
          ].map(({ icon: Icon, label, desc }) => (
            <div
              key={label}
              className="flex items-start gap-4 rounded-2xl p-5"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <div className="rounded-xl p-2 shrink-0" style={{ background: "rgba(163,240,0,.1)" }}>
                <Icon className="w-4 h-4" style={{ color: "#a3f000" }} />
              </div>
              <div>
                <p className="font-semibold text-sm mb-1" style={{ color: "var(--text)" }}>{label}</p>
                <p className="text-xs leading-relaxed" style={{ color: "var(--muted)" }}>{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pricing */}
      <div className="max-w-5xl mx-auto px-6 pb-24" id="pricing">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Simple pricing
          </h2>
          <p className="text-base" style={{ color: "var(--muted)" }}>Start free. Upgrade when you need more competitors, history, or alerts.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {PLANS.map(({ name, price, sub, highlight, features, cta, href }) => (
            <div
              key={name}
              className="rounded-2xl p-6 flex flex-col"
              style={{
                background: highlight ? "rgba(163,240,0,.05)" : "var(--bg-card)",
                border: `1px solid ${highlight ? "rgba(163,240,0,.3)" : "var(--border)"}`,
              }}
            >
              {highlight && (
                <div
                  className="text-xs font-bold uppercase tracking-wide px-2.5 py-1 rounded-full self-start mb-3"
                  style={{ background: "rgba(163,240,0,.15)", color: "#a3f000" }}
                >
                  Most popular
                </div>
              )}
              <h3 className="font-bold text-lg mb-1" style={{ color: "var(--text)" }}>{name}</h3>
              <div className="flex items-baseline gap-1 mb-5">
                <span className="text-3xl font-black" style={{ color: highlight ? "#a3f000" : "var(--text)" }}>{price}</span>
                <span className="text-sm" style={{ color: "var(--muted)" }}>{sub}</span>
              </div>
              <ul className="space-y-2.5 mb-6 flex-1">
                {features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm" style={{ color: "var(--muted)" }}>
                    <Check className="w-4 h-4 shrink-0" style={{ color: highlight ? "#a3f000" : "var(--muted)" }} />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href={href}
                className="block text-center font-semibold py-3 rounded-xl transition-all hover:brightness-110"
                style={
                  highlight
                    ? { background: "#a3f000", color: "#060d18" }
                    : { border: "1px solid var(--border)", color: "var(--text)" }
                }
              >
                {cta}
              </Link>
            </div>
          ))}
        </div>
        <p className="text-center text-sm mt-6" style={{ color: "var(--muted)" }}>
          Annual plans available at 20% off · Cancel anytime · No hidden fees
        </p>
      </div>

      {/* FAQ */}
      <div className="max-w-2xl mx-auto px-6 pb-24">
        <h2 className="text-3xl font-black mb-10 text-center" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
          Common questions
        </h2>
        <div className="space-y-4">
          {FAQS.map(({ q, a }) => (
            <div
              key={q}
              className="rounded-2xl p-6"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <p className="font-semibold mb-2" style={{ color: "var(--text)" }}>{q}</p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{a}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Final CTA */}
      <div className="max-w-3xl mx-auto px-6 pb-24 text-center">
        <div
          className="rounded-3xl p-12"
          style={{ background: "rgba(163,240,0,.06)", border: "1px solid rgba(163,240,0,.2)" }}
        >
          <h2 className="text-3xl md:text-4xl font-black mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Start tracking your competitors today
          </h2>
          <p className="mb-8 text-lg" style={{ color: "var(--muted)" }}>
            Free forever. No credit card. First scan ready in under 60 seconds.
          </p>
          <Link
            href="/auth/signup"
            className="inline-flex items-center gap-2 font-bold px-8 py-4 rounded-2xl text-lg transition-all hover:brightness-110"
            style={{ background: "#a3f000", color: "#060d18" }}
          >
            Start tracking free
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t" style={{ borderColor: "var(--border)" }}>
        <div className="max-w-5xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4" style={{ color: "#a3f000" }} />
            <span className="font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="#pricing" className="text-sm hover:opacity-80" style={{ color: "var(--muted)" }}>Pricing</Link>
            <Link href="/auth/login" className="text-sm hover:opacity-80" style={{ color: "var(--muted)" }}>Sign in</Link>
            <Link href="/auth/signup" className="text-sm hover:opacity-80" style={{ color: "var(--muted)" }}>Sign up</Link>
          </div>
          <p className="text-xs" style={{ color: "var(--muted)" }}>© 2025 StoreScout</p>
        </div>
      </footer>
    </div>
  );
}
