import Link from "next/link";
import {
  Zap, Bell, ArrowRight, Check, Shield, Clock,
  TrendingUp, Package, Tag, Sparkles, ChevronRight,
} from "lucide-react";
import { FaqAccordion } from "@/components/landing/FaqAccordion";

// ── Static data ───────────────────────────────────────────────────────────────

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

const BRANDS = [
  "gymshark.com", "fashionnova.com", "allbirds.com", "skims.com",
  "vuori.com", "lululemon.com", "chubbies.com", "revolve.com",
  "gymshark.com", "fashionnova.com", "allbirds.com", "skims.com",
];

// ── Preview components ────────────────────────────────────────────────────────

function SignalCardPreview({
  type, headline, hostname, label, why, count, color, bg, border,
}: {
  type: string; headline: string; hostname: string; label: string;
  why: string; count: number; color: string; bg: string; border: string;
}) {
  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ background: bg, border: `1px solid ${border}` }}
    >
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span
                className="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full"
                style={{ background: `${color}20`, color }}
              >
                {headline}
              </span>
              <span className="text-xs font-semibold truncate" style={{ color: "#eef3fa" }}>{hostname}</span>
            </div>
            <p className="text-sm font-bold mt-0.5" style={{ color: "#eef3fa" }}>{label}</p>
          </div>
        </div>
        <span className="text-[11px] shrink-0 ml-3" style={{ color: "#4a6080" }}>2h ago</span>
      </div>
      <div
        className="mx-4 mb-3 px-3.5 py-2.5 rounded-xl text-xs leading-relaxed"
        style={{ background: "rgba(0,0,0,.25)", color: "#94a3b8" }}
      >
        <span className="font-semibold" style={{ color }}>{type} · </span>
        {why}
      </div>
      <div
        className="flex items-center justify-between px-4 py-2 text-xs font-semibold"
        style={{ borderTop: `1px solid ${border}`, color: "#4a6080" }}
      >
        <span>Show all {count} products</span>
        <span>↓</span>
      </div>
    </div>
  );
}

function AppPreview() {
  return (
    <div
      className="rounded-2xl overflow-hidden shadow-2xl"
      style={{ background: "#060d18", border: "1px solid #1a2744" }}
    >
      {/* Browser chrome */}
      <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ background: "#0a1628", borderColor: "#1a2744" }}>
        <div className="flex gap-1.5">
          <span className="w-3 h-3 rounded-full bg-red-400/70" />
          <span className="w-3 h-3 rounded-full bg-yellow-400/70" />
          <span className="w-3 h-3 rounded-full bg-green-400/70" />
        </div>
        <div className="flex-1 mx-3 rounded-md px-3 py-1 text-xs font-mono" style={{ background: "#060d18", color: "#4a6080" }}>
          app.storescout.com/dashboard
        </div>
      </div>

      <div className="flex" style={{ minHeight: 320 }}>
        {/* Sidebar */}
        <div className="w-12 shrink-0 flex flex-col items-center gap-4 py-4 border-r" style={{ borderColor: "#1a2744" }}>
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "rgba(163,240,0,.15)" }}>
            <Zap className="w-3.5 h-3.5" style={{ color: "#a3f000" }} />
          </div>
          {[TrendingUp, Bell, Package].map((Icon, i) => (
            <div key={i} className="w-7 h-7 rounded-lg flex items-center justify-center opacity-40">
              <Icon className="w-3.5 h-3.5" style={{ color: "#4a6080" }} />
            </div>
          ))}
        </div>

        {/* Center: Intelligence stream */}
        <div className="flex-1 min-w-0 p-4 space-y-2">
          {/* Narrative bar */}
          <div
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-[11px] font-medium mb-3"
            style={{ background: "rgba(239,68,68,.1)", border: "1px solid rgba(239,68,68,.2)", color: "#fca5a5" }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse shrink-0" />
            fashionnova.com: 19 launches · flash sale · 41 total events
          </div>

          {/* Strategic signal */}
          <SignalCardPreview
            type="Why this matters"
            headline="LAUNCH BURST"
            hostname="fashionnova.com"
            label="19 products launched in 4 hours"
            why="A burst this large usually precedes a paid push. Expect heavy Meta spend on these SKUs within 48 hours."
            count={19}
            color="#a3f000"
            bg="rgba(163,240,0,.05)"
            border="rgba(163,240,0,.2)"
          />

          {/* Tactical signal */}
          <div
            className="rounded-xl overflow-hidden"
            style={{ border: "1px solid rgba(239,68,68,.2)", background: "rgba(239,68,68,.05)" }}
          >
            <div className="flex items-center gap-3 px-3 py-2.5">
              <span className="text-[10px] font-black uppercase tracking-wider" style={{ color: "#f87171" }}>⚡ FLASH SALE</span>
              <span className="text-xs font-semibold" style={{ color: "#eef3fa" }}>gymshark.com</span>
              <span className="text-[11px] ml-auto" style={{ color: "#4a6080" }}>5m ago</span>
            </div>
          </div>
        </div>

        {/* Right panel */}
        <div className="w-44 shrink-0 border-l p-3 space-y-3" style={{ borderColor: "#1a2744" }}>
          <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "#4a6080" }}>Activity · 7 days</p>
          <div className="flex items-end gap-0.5 h-14">
            {[3, 7, 2, 9, 5, 12, 6].map((h, i) => (
              <div key={i} className="flex-1 rounded-sm" style={{ background: i === 5 ? "#a3f000" : "rgba(163,240,0,.2)", height: `${(h/12)*100}%` }} />
            ))}
          </div>
          <div className="space-y-1.5 pt-1">
            {[["gymshark.com", "2 changes"], ["allbirds.com", "1 change"]].map(([host, ch]) => (
              <div key={host} className="flex items-center justify-between">
                <span className="text-[10px] truncate" style={{ color: "#4a6080" }}>{host}</span>
                <span className="text-[10px] font-semibold" style={{ color: "#a3f000" }}>{ch}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Comparison table ──────────────────────────────────────────────────────────

function ComparisonTable() {
  const rows = [
    { feature: "Real-time change detection", ext: false, report: false, us: true },
    { feature: "Price history over time",    ext: false, report: false, us: true },
    { feature: "Email alerts within 15 min", ext: false, report: false, us: true },
    { feature: "Works without a Chrome tab", ext: false, report: true,  us: true },
    { feature: "AI weekly digest",           ext: false, report: false, us: true },
    { feature: "Multi-competitor dashboard", ext: false, report: false, us: true },
    { feature: "Starts free, no card",       ext: false, report: false, us: true },
  ];

  const col = (v: boolean) => v
    ? <span className="text-base" style={{ color: "#a3f000" }}>✓</span>
    : <span className="text-base opacity-20" style={{ color: "#94a3b8" }}>✕</span>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className="text-left py-3 pr-6 font-medium" style={{ color: "var(--muted)" }} />
            <th className="text-center py-3 px-4 font-semibold text-xs" style={{ color: "var(--muted)" }}>Chrome extensions</th>
            <th className="text-center py-3 px-4 font-semibold text-xs" style={{ color: "var(--muted)" }}>One-time reports</th>
            <th
              className="text-center py-3 px-4 font-semibold text-xs rounded-t-xl"
              style={{ color: "#a3f000", background: "rgba(163,240,0,.07)", border: "1px solid rgba(163,240,0,.2)", borderBottom: "none" }}
            >
              StoreScout
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ feature, ext, report, us }, i) => (
            <tr key={feature} style={{ borderTop: "1px solid var(--border)" }}>
              <td className="py-3 pr-6 font-medium" style={{ color: "var(--text-2)" }}>{feature}</td>
              <td className="text-center py-3 px-4">{col(ext)}</td>
              <td className="text-center py-3 px-4">{col(report)}</td>
              <td
                className={`text-center py-3 px-4 ${i === rows.length - 1 ? "rounded-b-xl" : ""}`}
                style={{ background: "rgba(163,240,0,.07)", border: "1px solid rgba(163,240,0,.2)", borderTop: "none", borderBottom: i === rows.length - 1 ? undefined : "none" }}
              >
                {col(us)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>

      {/* ── Nav ─────────────────────────────────────────────────────────────── */}
      <nav
        className="sticky top-0 z-40 flex items-center justify-between px-6 md:px-12 py-4 border-b backdrop-blur-md"
        style={{ borderColor: "var(--border)", background: "rgba(6,13,24,.9)" }}
      >
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5" style={{ color: "#a3f000" }} />
          <span className="font-bold text-lg" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>
        <div className="hidden md:flex items-center gap-6">
          <Link href="#how-it-works" className="text-sm font-medium hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>How it works</Link>
          <Link href="#pricing" className="text-sm font-medium hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>Pricing</Link>
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

      {/* ── Hero ────────────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pt-20 pb-12 text-center">
        <div
          className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-8"
          style={{ background: "rgba(163,240,0,.1)", color: "#a3f000", border: "1px solid rgba(163,240,0,.2)" }}
        >
          <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
          Live competitor intelligence for Shopify
        </div>

        <h1
          className="text-4xl md:text-6xl font-black tracking-tight mb-6"
          style={{ color: "var(--text)", letterSpacing: "-0.04em", lineHeight: 1.05 }}
        >
          Always know what your<br />
          <span style={{ color: "#a3f000" }}>Shopify competitors</span><br />
          are doing.
        </h1>

        <p className="text-lg md:text-xl mb-8 max-w-2xl mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
          Track prices, product launches, and discount campaigns across any Shopify store.
          Get alerted within 15 minutes when they make a move — automatically, every day.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-6">
          <Link
            href="/auth/signup"
            className="flex items-center gap-2 font-bold px-8 py-4 rounded-2xl text-lg transition-all hover:brightness-110"
            style={{ background: "#a3f000", color: "#060d18" }}
          >
            Start tracking free
            <ArrowRight className="w-5 h-5" />
          </Link>
          <Link
            href="#how-it-works"
            className="flex items-center gap-2 text-sm font-medium hover:opacity-80 transition-opacity"
            style={{ color: "var(--muted)" }}
          >
            See how it works
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>

        <p className="text-sm" style={{ color: "var(--muted)", opacity: 0.6 }}>
          No credit card required · Free forever · First scan ready in 60 seconds
        </p>
      </div>

      {/* ── Brand ticker ────────────────────────────────────────────────────── */}
      <div className="border-y overflow-hidden py-4 mb-20" style={{ borderColor: "var(--border)" }}>
        <p className="text-center text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "var(--muted)", opacity: 0.5 }}>
          Stores being tracked right now
        </p>
        <div className="flex items-center gap-8 px-8 flex-wrap justify-center">
          {BRANDS.slice(0, 8).map((b, i) => (
            <span key={i} className="text-sm font-mono font-medium" style={{ color: "var(--muted)", opacity: 0.45 }}>
              {b}
            </span>
          ))}
        </div>
      </div>

      {/* ── App preview ─────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-black mb-2" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Intelligence, not raw data
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            19 individual price changes collapse into one "Flash Sale" signal. You see what matters, not a spreadsheet.
          </p>
        </div>
        <AppPreview />
      </div>

      {/* ── How it works ────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28" id="how-it-works">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Live in 60 seconds
          </h2>
          <p className="text-base" style={{ color: "var(--muted)" }}>No setup, no API keys, no spreadsheets.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-8 relative">
          {/* Connector line */}
          <div className="hidden md:block absolute top-6 left-[calc(16.67%+24px)] right-[calc(16.67%+24px)] h-px" style={{ background: "linear-gradient(90deg, transparent, rgba(163,240,0,.3), transparent)" }} />

          {[
            { step: "01", icon: Package, title: "Paste any Shopify URL", desc: "Enter a competitor's store URL. We verify it's a Shopify store and kick off the first scan immediately — no browser extension needed." },
            { step: "02", icon: TrendingUp, title: "We analyze their full catalog", desc: "StoreScout fetches their entire product catalog, analyzes pricing patterns, launch velocity, and discount strategy. First results in under 2 minutes." },
            { step: "03", icon: Bell, title: "Get alerted when they move", desc: "Price drops, new launches, sale events — you're notified by email within 15 minutes. The dashboard updates automatically every day." },
          ].map(({ step, icon: Icon, title, desc }) => (
            <div key={step} className="text-center relative">
              <div
                className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4 relative z-10"
                style={{ background: "rgba(163,240,0,.1)", border: "1px solid rgba(163,240,0,.2)" }}
              >
                <Icon className="w-5 h-5" style={{ color: "#a3f000" }} />
              </div>
              <div
                className="text-[10px] font-black uppercase tracking-widest mb-2"
                style={{ color: "rgba(163,240,0,.4)" }}
              >
                Step {step}
              </div>
              <h3 className="font-bold mb-2" style={{ color: "var(--text)" }}>{title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── What you get (features) ──────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Everything in one place
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            Built for Shopify operators who make pricing and product decisions every week — and can't afford Similarweb.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {/* Large feature card */}
          <div
            className="rounded-2xl p-7 flex flex-col justify-between row-span-1 md:row-span-2"
            style={{ background: "rgba(163,240,0,.04)", border: "1px solid rgba(163,240,0,.15)" }}
          >
            <div>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-5" style={{ background: "rgba(163,240,0,.12)" }}>
                <Bell className="w-5 h-5" style={{ color: "#a3f000" }} />
              </div>
              <h3 className="text-lg font-bold mb-3" style={{ color: "var(--text)" }}>
                Flash sale detection in minutes
              </h3>
              <p className="text-sm leading-relaxed mb-5" style={{ color: "var(--muted)" }}>
                When a competitor drops 20+ prices in one session, StoreScout detects it as a "Flash Sale" event and emails you within 15 minutes — before it shows up on social.
              </p>
            </div>
            {/* Mini alert preview */}
            <div
              className="rounded-xl p-4"
              style={{ background: "rgba(0,0,0,.3)", border: "1px solid rgba(239,68,68,.2)" }}
            >
              <div className="flex items-center gap-2 mb-3">
                <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full" style={{ background: "rgba(239,68,68,.15)", color: "#f87171" }}>⚡ Flash sale</span>
                <span className="text-xs" style={{ color: "#94a3b8" }}>gymshark.com · just now</span>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: "#94a3b8" }}>
                7 products dropped ≥20% — avg −24.6%. Summer clearance or aggressive acquisition push.
              </p>
            </div>
          </div>

          {/* Regular features */}
          {[
            { icon: TrendingUp, title: "90-day price history", desc: "See how prices have moved over time. Spot seasonal patterns and predict the next sale." },
            { icon: Sparkles, title: "AI weekly digest", desc: "Every Monday, Claude writes a 4–6 sentence brief on what changed and what it likely signals strategically." },
            { icon: Package, title: "Launch velocity tracking", desc: "How many products are they launching per month? Are they accelerating or pulling back?" },
            { icon: Tag, title: "Discount monitoring", desc: "Track what % of their catalog is on sale, the average depth, and when new sale events start." },
          ].map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="rounded-2xl p-6"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-4" style={{ background: "rgba(163,240,0,.1)" }}>
                <Icon className="w-5 h-5" style={{ color: "#a3f000" }} />
              </div>
              <h3 className="font-bold mb-2" style={{ color: "var(--text)" }}>{title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Comparison ──────────────────────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto px-6 pb-28">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Why not a Chrome extension?
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            Extensions only work while you're browsing. Reports are a one-time snapshot. StoreScout monitors continuously — whether you're logged in or not.
          </p>
        </div>
        <div
          className="rounded-2xl p-6 md:p-8"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <ComparisonTable />
        </div>
      </div>

      {/* ── Trust signals ───────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { icon: Shield, label: "Public data only", desc: "Reads Shopify's public product endpoints — no login required, no private data touched, no ToS issues." },
            { icon: Clock, label: "Daily auto-scans", desc: "Pro and Agency plans scan automatically every 24 hours. Set it and never manually check again." },
            { icon: Zap, label: "Alerts within 15 minutes", desc: "Change detection runs immediately after each scan — you hear about it before it hits social media." },
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

      {/* ── Pricing ─────────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28" id="pricing">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Simple pricing
          </h2>
          <p className="text-base" style={{ color: "var(--muted)" }}>
            Start free. Upgrade when you need more competitors, history, or alerts.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {PLANS.map(({ name, price, sub, highlight, features, cta, href }) => (
            <div
              key={name}
              className="rounded-2xl p-6 flex flex-col relative"
              style={{
                background: highlight ? "rgba(163,240,0,.05)" : "var(--bg-card)",
                border: `1px solid ${highlight ? "rgba(163,240,0,.3)" : "var(--border)"}`,
              }}
            >
              {highlight && (
                <div
                  className="absolute -top-3 left-1/2 -translate-x-1/2 text-xs font-bold uppercase tracking-wide px-3 py-1 rounded-full"
                  style={{ background: "#a3f000", color: "#060d18" }}
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

      {/* ── FAQ ─────────────────────────────────────────────────────────────── */}
      <div className="max-w-2xl mx-auto px-6 pb-28">
        <h2 className="text-3xl font-black mb-10 text-center" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
          Common questions
        </h2>
        <FaqAccordion />
      </div>

      {/* ── Final CTA ───────────────────────────────────────────────────────── */}
      <div className="max-w-3xl mx-auto px-6 pb-28 text-center">
        <div
          className="rounded-3xl p-12 relative overflow-hidden"
          style={{ background: "rgba(163,240,0,.06)", border: "1px solid rgba(163,240,0,.2)" }}
        >
          {/* Ambient glow */}
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-32 rounded-full blur-3xl pointer-events-none"
            style={{ background: "rgba(163,240,0,.12)" }}
          />
          <div className="relative">
            <h2 className="text-3xl md:text-4xl font-black mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
              Stop guessing what your competitors are doing.
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
      </div>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <footer className="border-t" style={{ borderColor: "var(--border)" }}>
        <div className="max-w-5xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4" style={{ color: "#a3f000" }} />
            <span className="font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="#how-it-works" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>How it works</Link>
            <Link href="#pricing" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>Pricing</Link>
            <Link href="/auth/login" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>Sign in</Link>
          </div>
          <p className="text-xs" style={{ color: "var(--muted)" }}>© 2025 StoreScout</p>
        </div>
      </footer>

    </div>
  );
}
