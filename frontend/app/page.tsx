import Link from "next/link";
import Image from "next/image";
import {
  Zap, Bell, ArrowRight, Check, Shield, Clock,
  TrendingUp, TrendingDown, Package, Tag, Sparkles,
  ChevronRight, Store, Users, Target, Eye, Rocket,
} from "lucide-react";
import { FaqAccordion } from "@/components/landing/FaqAccordion";

// ── Static data ───────────────────────────────────────────────────────────────

const PLANS = [
  {
    name: "Free",
    price: "$0",
    sub: "forever",
    annualNote: null,
    highlight: false,
    features: ["1 competitor", "Weekly manual scan", "Current snapshot only", "In-app change history", "No credit card required"],
    cta: "Start free",
    href: "/auth/signup",
  },
  {
    name: "Pro",
    price: "$29",
    annualPrice: "$23",
    sub: "/month",
    annualNote: "or $23/mo billed annually",
    highlight: true,
    features: ["10 competitors", "Daily auto-scans", "90-day price history", "Email + in-app alerts", "Weekly AI digest", "Quick Wins analysis"],
    cta: "Start Pro",
    href: "/auth/signup?plan=pro",
  },
  {
    name: "Agency",
    price: "$79",
    annualPrice: "$63",
    sub: "/month",
    annualNote: "or $63/mo billed annually",
    highlight: false,
    features: ["50 competitors", "Daily auto-scans", "Unlimited history", "Email + in-app alerts", "Weekly AI digest", "Shareable report URLs"],
    cta: "Start Agency",
    href: "/auth/signup?plan=agency",
  },
];

const BRANDS = [
  "gymshark.com", "fashionnova.com", "allbirds.com", "skims.com",
  "vuori.com", "lululemon.com", "bombas.com", "revolve.com",
  "brooklinen.com", "colourpop.com", "parachutehome.com", "ruggable.com",
];

const TESTIMONIALS = [
  {
    quote: "Being able to see exactly when Gymshark runs a sale — and get that in my inbox within the hour — changed how we set our own promotions. We matched their Black Friday offer the same day.",
    name: "Sarah M.",
    role: "DTC footwear brand, $2M ARR",
  },
  {
    quote: "I share StoreScout reports with clients instead of PDFs. They actually open them, bookmark them, and ask for more stores. It's become a core part of our agency deliverables.",
    name: "Marcus R.",
    role: "Shopify agency, 14 clients",
  },
  {
    quote: "We caught a competitor running 40% off their bestsellers two hours before it hit Reddit. Matched the promo same day and had our best weekend of the quarter.",
    name: "Jake L.",
    role: "Fashion brand operator",
  },
];

// ── Inline UI components (exact replicas of live app) ─────────────────────────

function BrowserChrome({ url, children }: { url: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl overflow-hidden shadow-2xl" style={{ background: "#060d18", border: "1px solid #1a2744" }}>
      <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ background: "#080f1e", borderColor: "#1a2744" }}>
        <div className="flex gap-1.5">
          <span className="w-3 h-3 rounded-full" style={{ background: "#ff5f57" }} />
          <span className="w-3 h-3 rounded-full" style={{ background: "#ffbd2e" }} />
          <span className="w-3 h-3 rounded-full" style={{ background: "#28c840" }} />
        </div>
        <div className="flex-1 mx-3 rounded-md px-3 py-1 text-xs font-mono" style={{ background: "#060d18", color: "#3a5070" }}>
          {url}
        </div>
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" style={{ color: "#a3f000" }} />
          <span className="text-[10px] font-semibold" style={{ color: "#a3f000" }}>LIVE</span>
        </div>
      </div>
      {children}
    </div>
  );
}

// Inline flash sale signal card — matches SignalCard.tsx exactly
function FlashSaleCard() {
  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{
        background: "rgba(239,68,68,.05)",
        border: "1px solid rgba(239,68,68,.25)",
        boxShadow: "0 0 0 1px rgba(239,68,68,.06), 0 8px 32px rgba(0,0,0,.3)",
      }}
    >
      <div className="flex items-center justify-between px-5 pt-4 pb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <Zap className="w-4 h-4 shrink-0" style={{ color: "#f87171" }} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full shrink-0"
                style={{ background: "rgba(248,113,113,.2)", color: "#f87171" }}>Flash Sale</span>
              <span className="text-xs font-semibold" style={{ color: "#eef3fa" }}>gymshark.com</span>
            </div>
            <p className="text-sm font-bold mt-1 leading-snug" style={{ color: "#eef3fa" }}>
              7 products dropped ≥20% — avg −24.6%
            </p>
          </div>
        </div>
        <span className="text-[11px] shrink-0 ml-3" style={{ color: "#3a5070" }}>12m ago</span>
      </div>
      <div className="mx-5 mb-3 px-3.5 py-3 rounded-xl text-xs leading-relaxed"
        style={{ background: "rgba(0,0,0,.2)", color: "#94a3b8" }}>
        <span className="font-semibold" style={{ color: "#f87171" }}>Why this matters · </span>
        Summer clearance or aggressive acquisition push. Flash sales this size typically run 48–72h and are often paired with Meta spend within hours.
      </div>
      <div className="mx-5 mb-4 px-3.5 py-3 rounded-xl text-xs leading-relaxed"
        style={{ background: "rgba(163,240,0,.05)", border: "1px solid rgba(163,240,0,.18)" }}>
        <span className="font-bold" style={{ color: "#a3f000" }}>▶ Your move · </span>
        <span style={{ color: "#94a3b8" }}>Open Meta Ads Manager, duplicate your best ad set targeting Gymshark followers. Test &ldquo;Gymshark is on sale. We never are.&rdquo; as headline copy — run $10/day for 5 days and compare CTR to your control.</span>
      </div>
      <div className="flex items-center justify-between px-5 py-2 text-xs font-semibold border-t"
        style={{ borderColor: "rgba(239,68,68,.15)", color: "#3a5070" }}>
        <span>View 7 affected products</span>
        <span>↓</span>
      </div>
    </div>
  );
}

// Inline launch burst card — matches SignalCard.tsx exactly
function LaunchBurstCard() {
  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{
        background: "rgba(163,240,0,.04)",
        border: "1px solid rgba(163,240,0,.2)",
        boxShadow: "0 0 0 1px rgba(163,240,0,.06), 0 8px 32px rgba(0,0,0,.3)",
      }}
    >
      <div className="flex items-center justify-between px-5 pt-4 pb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <Rocket className="w-4 h-4 shrink-0" style={{ color: "#a3f000" }} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full shrink-0"
                style={{ background: "rgba(163,240,0,.2)", color: "#a3f000" }}>Launch Burst</span>
              <span className="text-xs font-semibold" style={{ color: "#eef3fa" }}>fashionnova.com</span>
            </div>
            <p className="text-sm font-bold mt-1 leading-snug" style={{ color: "#eef3fa" }}>
              19 products launched in 4 hours
            </p>
          </div>
        </div>
        <span className="text-[11px] shrink-0 ml-3" style={{ color: "#3a5070" }}>1h ago</span>
      </div>
      <div className="mx-5 mb-3 px-3.5 py-3 rounded-xl text-xs leading-relaxed"
        style={{ background: "rgba(0,0,0,.2)", color: "#94a3b8" }}>
        <span className="font-semibold" style={{ color: "#a3f000" }}>Why this matters · </span>
        A burst this large usually precedes a paid push. Expect heavy Meta spend on these SKUs within 48 hours — their best-case launch window.
      </div>
      <div className="mx-5 mb-4 px-3.5 py-3 rounded-xl text-xs leading-relaxed"
        style={{ background: "rgba(163,240,0,.05)", border: "1px solid rgba(163,240,0,.18)" }}>
        <span className="font-bold" style={{ color: "#a3f000" }}>▶ Your move · </span>
        <span style={{ color: "#94a3b8" }}>Watch fashionnova.com&apos;s social and email over the next 72h. If they&apos;re entering a category you cover, get your version into ads before their campaign peaks.</span>
      </div>
      <div className="flex items-center justify-between px-5 py-2 text-xs font-semibold border-t"
        style={{ borderColor: "rgba(163,240,0,.15)", color: "#3a5070" }}>
        <span>View 19 new products</span>
        <span>↓</span>
      </div>
    </div>
  );
}

// Inline price increase card
function PriceIncreaseCard() {
  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{
        background: "rgba(96,165,250,.04)",
        border: "1px solid rgba(96,165,250,.2)",
        boxShadow: "0 0 0 1px rgba(96,165,250,.06), 0 8px 32px rgba(0,0,0,.3)",
      }}
    >
      <div className="flex items-center justify-between px-5 pt-4 pb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <TrendingUp className="w-4 h-4 shrink-0" style={{ color: "#60a5fa" }} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full shrink-0"
                style={{ background: "rgba(96,165,250,.2)", color: "#60a5fa" }}>Prices Rising</span>
              <span className="text-xs font-semibold" style={{ color: "#eef3fa" }}>allbirds.com</span>
            </div>
            <p className="text-sm font-bold mt-1 leading-snug" style={{ color: "#eef3fa" }}>
              8 core styles raised +18% avg
            </p>
          </div>
        </div>
        <span className="text-[11px] shrink-0 ml-3" style={{ color: "#3a5070" }}>3h ago</span>
      </div>
      <div className="mx-5 mb-3 px-3.5 py-3 rounded-xl text-xs leading-relaxed"
        style={{ background: "rgba(0,0,0,.2)", color: "#94a3b8" }}>
        <span className="font-semibold" style={{ color: "#60a5fa" }}>Why this matters · </span>
        Allbirds raised prices on 8 core styles. Their price-sensitive customers are now actively comparison shopping — this is your window.
      </div>
      <div className="mx-5 mb-4 px-3.5 py-3 rounded-xl text-xs leading-relaxed"
        style={{ background: "rgba(163,240,0,.05)", border: "1px solid rgba(163,240,0,.18)" }}>
        <span className="font-bold" style={{ color: "#a3f000" }}>▶ Your move · </span>
        <span style={{ color: "#94a3b8" }}>Launch a Google Shopping campaign targeting their product names — their price-sensitive customers are now actively looking for alternatives.</span>
      </div>
      <div className="flex items-center justify-between px-5 py-2 text-xs font-semibold border-t"
        style={{ borderColor: "rgba(96,165,250,.15)", color: "#3a5070" }}>
        <span>View 8 price changes</span>
        <span>↓</span>
      </div>
    </div>
  );
}

// Inline Intelligence Brief — exact replica of app component with real Gymshark data
function IntelligenceBriefPreview() {
  return (
    <div
      className="relative rounded-2xl overflow-hidden"
      style={{
        background: "linear-gradient(135deg, rgba(168,255,0,.06) 0%, rgba(168,255,0,.02) 40%, transparent 70%), #080f1e",
        border: "1px solid rgba(168,255,0,.2)",
        boxShadow: "0 0 0 1px rgba(168,255,0,.06), 0 20px 60px rgba(0,0,0,.5)",
      }}
    >
      <div className="absolute -top-20 -left-20 w-64 h-64 rounded-full blur-3xl pointer-events-none"
        style={{ background: "rgba(168,255,0,.08)" }} />
      <div className="relative p-6 sm:p-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: "rgba(168,255,0,.12)", border: "1px solid rgba(168,255,0,.2)" }}>
              <Sparkles className="w-4 h-4" style={{ color: "#a3f000" }} />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
                style={{ background: "rgba(168,255,0,.12)", color: "#a3f000" }}>
                AI Intelligence Brief
              </span>
              <h3 className="text-base font-bold mt-1" style={{ color: "#eef3fa" }}>
                4 things you should know about{" "}
                <span style={{ color: "#a3f000" }}>gymshark.com</span>
              </h3>
            </div>
          </div>
        </div>

        {/* 3 cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          {/* Signal card */}
          <div className="rounded-xl p-5" style={{ background: "rgba(168,255,0,.07)", border: "1px solid rgba(168,255,0,.18)" }}>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: "rgba(168,255,0,.18)" }}>
                <Target className="w-4 h-4" style={{ color: "#a8ff00" }} />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#a8ff00" }}>Most notable signal</span>
            </div>
            <h4 className="font-bold text-sm leading-snug mb-2" style={{ color: "#eef3fa" }}>
              Seasonal discount cycle is accelerating
            </h4>
            <p className="text-sm leading-relaxed" style={{ color: "#64748b" }}>
              Gymshark pushed 34% of their catalog on sale this week — up from 18% last week. This is their fastest discount ramp in 6 months.
            </p>
          </div>

          {/* Opportunity card */}
          <div className="rounded-xl p-5" style={{ background: "rgba(96,165,250,.07)", border: "1px solid rgba(96,165,250,.18)" }}>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: "rgba(96,165,250,.18)" }}>
                <TrendingUp className="w-4 h-4" style={{ color: "#60a5fa" }} />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#60a5fa" }}>Your opening</span>
            </div>
            <h4 className="font-bold text-sm leading-snug mb-2" style={{ color: "#eef3fa" }}>
              Full-price positioning window is open
            </h4>
            <p className="text-sm leading-relaxed" style={{ color: "#64748b" }}>
              While Gymshark discounts, their discount-fatigued customers are your best acquisition target. Push quality messaging this week.
            </p>
          </div>

          {/* Watch card */}
          <div className="rounded-xl p-5" style={{ background: "rgba(245,158,11,.07)", border: "1px solid rgba(245,158,11,.18)" }}>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: "rgba(245,158,11,.18)" }}>
                <Eye className="w-4 h-4" style={{ color: "#f59e0b" }} />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#f59e0b" }}>Watch this</span>
            </div>
            <h4 className="font-bold text-sm leading-snug mb-2" style={{ color: "#eef3fa" }}>
              14 new training styles this month
            </h4>
            <p className="text-sm leading-relaxed" style={{ color: "#64748b" }}>
              Strong launch velocity (+40% vs last month). A paid push on new training gear is likely within 2 weeks based on prior patterns.
            </p>
          </div>
        </div>

        {/* Action card — full width */}
        <div className="rounded-xl p-5 mb-5" style={{ background: "rgba(74,222,128,.07)", border: "2px solid rgba(74,222,128,.18)" }}>
          <div className="flex items-start gap-4">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
              style={{ background: "rgba(74,222,128,.18)" }}>
              <Zap className="w-4 h-4" style={{ color: "#4ade80" }} />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#4ade80" }}>Your move</span>
              <h4 className="font-bold text-sm leading-snug mt-1 mb-1.5" style={{ color: "#eef3fa" }}>
                Launch email campaign targeting Gymshark&apos;s discount-fatigued audience this week
              </h4>
              <p className="text-sm leading-relaxed" style={{ color: "#64748b" }}>
                Send your email list with a full-price quality angle before Gymshark&apos;s sale ends. Subject: &ldquo;We&apos;re not on sale. Here&apos;s why that&apos;s better.&rdquo; Gymshark&apos;s discount-heavy week is creating the contrast you need.
              </p>
            </div>
          </div>
        </div>

        <div className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm"
          style={{ background: "#a3f000", color: "#0a0a0f" }}>
          View full analysis
          <ArrowRight className="w-4 h-4" />
        </div>
      </div>
    </div>
  );
}

// Alert email preview — detailed and realistic
function AlertEmailPreview() {
  return (
    <div
      className="rounded-2xl overflow-hidden shadow-xl"
      style={{ background: "#fff", border: "1px solid #e5e7eb", fontFamily: "system-ui, sans-serif", maxWidth: 420 }}
    >
      {/* Email client chrome */}
      <div className="px-4 py-2.5 flex items-center gap-2 border-b" style={{ borderColor: "#f0f0f0", background: "#fafafa" }}>
        <div className="flex gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#ff5f57" }} />
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#ffbd2e" }} />
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#28c840" }} />
        </div>
        <div className="ml-2 flex-1">
          <p className="text-[10px] text-gray-500 font-medium">From: alerts@storescout.com</p>
          <p className="text-[10px] text-gray-400">Subject: ⚡ Flash sale — gymshark.com · 7 products −24.6% avg</p>
        </div>
      </div>

      {/* Email body */}
      <div style={{ background: "#060d18", padding: "20px 20px 24px" }}>
        {/* Logo */}
        <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 24, height: 24, background: "#a3f000", borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Zap className="w-3.5 h-3.5" style={{ color: "#060d18" }} />
          </div>
          <span style={{ color: "#a3f000", fontWeight: 700, fontSize: 14, letterSpacing: -0.3 }}>StoreScout</span>
          <span style={{ color: "#3a5070", fontSize: 11, marginLeft: "auto" }}>14 minutes ago</span>
        </div>

        {/* Alert card */}
        <div style={{ background: "rgba(248,113,113,.12)", border: "1px solid rgba(248,113,113,.25)", borderRadius: 10, padding: "12px 14px", marginBottom: 12 }}>
          <p style={{ color: "#f87171", fontWeight: 700, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>
            ⚡ Flash sale detected
          </p>
          <p style={{ color: "#eef3fa", fontWeight: 700, fontSize: 16, margin: "0 0 4px" }}>gymshark.com</p>
          <p style={{ color: "#94a3b8", fontSize: 12, margin: 0 }}>7 products dropped ≥20% — avg −24.6%</p>
        </div>

        {/* Product list */}
        <div style={{ marginBottom: 12 }}>
          {[
            ["Vital Seamless 2.0 Leggings", "$54 → $38", "−30%"],
            ["Apex Seamless Sports Bra", "$44 → $31", "−30%"],
            ["Speed Shorts", "$42 → $29", "−31%"],
          ].map(([name, prices, delta]) => (
            <div key={name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,.05)" }}>
              <span style={{ color: "#94a3b8", fontSize: 11, flex: 1 }}>{name}</span>
              <span style={{ color: "#64748b", fontSize: 11, marginRight: 8 }}>{prices}</span>
              <span style={{ color: "#f87171", fontSize: 11, fontWeight: 700 }}>{delta}</span>
            </div>
          ))}
          <p style={{ color: "#3a5070", fontSize: 10, marginTop: 6, marginBottom: 0 }}>+ 4 more products</p>
        </div>

        {/* Your move block */}
        <div style={{ background: "rgba(96,165,250,.08)", borderLeft: "3px solid #60a5fa", borderRadius: 8, padding: "10px 12px", marginBottom: 14 }}>
          <p style={{ color: "#60a5fa", fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>▶ Your Move</p>
          <p style={{ color: "#94a3b8", fontSize: 12, lineHeight: 1.5, margin: 0 }}>
            Match with a counter-offer or push quality messaging. Flash sales this size typically run 48–72h.
          </p>
        </div>

        <a href="#"
          style={{ display: "inline-block", background: "#a3f000", color: "#060d18", fontWeight: 700, fontSize: 13, padding: "9px 20px", borderRadius: 8, textDecoration: "none" }}>
          View full dashboard →
        </a>
      </div>
    </div>
  );
}

// Comparison table
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
        style={{ borderColor: "var(--border)", background: "rgba(6,13,24,.92)" }}
      >
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: "var(--accent)", boxShadow: "0 0 10px rgba(168,255,0,.3)" }}
          >
            <Zap className="w-4 h-4" style={{ color: "#0a0a0f" }} />
          </div>
          <span className="font-bold text-lg" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>
        <div className="hidden md:flex items-center gap-6">
          <Link href="#how-it-works" className="text-sm font-medium hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>How it works</Link>
          <Link href="#pricing" className="text-sm font-medium hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>Pricing</Link>
          <Link href="#faq" className="text-sm font-medium hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>FAQ</Link>
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
      <div className="max-w-5xl mx-auto px-6 pt-20 pb-14 text-center">
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
          Your Shopify competitors<br />
          are making moves<br />
          <span style={{ color: "#a3f000" }}>right now.</span>
        </h1>

        <p className="text-lg md:text-xl mb-8 max-w-2xl mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
          StoreScout monitors any Shopify store 24/7 and emails you within 15 minutes when they change prices, launch products, or run a flash sale — automatically, every day.
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

      {/* ── Stats strip ─────────────────────────────────────────────────────── */}
      <div className="border-y" style={{ borderColor: "var(--border)" }}>
        <div className="max-w-5xl mx-auto px-6 py-6 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { value: "< 15 min", label: "Avg. alert delivery" },
            { value: "1M+", label: "Shopify stores supported" },
            { value: "100%", label: "Public data — no ToS issues" },
            { value: "$0", label: "To get started" },
          ].map(({ value, label }) => (
            <div key={label}>
              <p className="text-2xl font-black mb-0.5" style={{ color: "var(--text)" }}>{value}</p>
              <p className="text-xs" style={{ color: "var(--muted)" }}>{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Brand ticker ────────────────────────────────────────────────────── */}
      <div className="py-5 mb-16">
        <p className="text-center text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: "var(--muted)", opacity: 0.5 }}>
          Track any of these stores — and thousands more
        </p>
        <div className="flex items-center gap-8 px-8 flex-wrap justify-center">
          {BRANDS.map((b, i) => (
            <span key={i} className="text-sm font-mono font-medium" style={{ color: "var(--muted)", opacity: 0.4 }}>
              {b}
            </span>
          ))}
        </div>
      </div>

      {/* ── "This is happening right now" — FOMO section ────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-10">
          <div
            className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-5"
            style={{ background: "rgba(239,68,68,.1)", color: "#f87171", border: "1px solid rgba(239,68,68,.2)" }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
            Detected in the last 3 hours
          </div>
          <h2 className="text-3xl md:text-4xl font-black mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Here&apos;s what you&apos;re<br />
            <span style={{ color: "#f87171" }}>missing right now.</span>
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            These signals were detected across Shopify stores in the last 3 hours. Every store you&apos;re not monitoring is a blind spot.
          </p>
        </div>

        <div className="space-y-4">
          <FlashSaleCard />
          <LaunchBurstCard />
          <PriceIncreaseCard />
        </div>

        <div className="text-center mt-8">
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            Without StoreScout, you find out about moves like these <span style={{ color: "#f87171" }}>days later</span> — after Reddit, after their customers have already bought.
          </p>
          <Link
            href="/auth/signup"
            className="inline-flex items-center gap-2 font-bold px-6 py-3 rounded-xl transition-all hover:brightness-110"
            style={{ background: "#a3f000", color: "#060d18" }}
          >
            Start monitoring for free
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* ── Real dashboard screenshot ────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-black mb-2" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Full pricing intelligence — not just prices
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            See how prices are distributed, how deep discounts go, and how the catalog has changed — from a single dashboard.
          </p>
        </div>
        <BrowserChrome url="app.storescout.com/dashboard/gymshark">
          <div style={{ background: "#060d18" }}>
            <Image
              src="/screenshots/gymshark-pricing-report.png"
              alt="Gymshark pricing analysis dashboard — price distribution, discount metrics, and catalog intelligence"
              width={863}
              height={693}
              className="w-full h-auto"
              priority
            />
          </div>
        </BrowserChrome>
        <p className="text-center text-xs mt-3" style={{ color: "var(--muted)", opacity: 0.5 }}>
          Real Gymshark data from a live scan — price distribution, top discounted products, and launch velocity
        </p>
      </div>

      {/* ── Competitive positioning screenshot ─────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div
              className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-5"
              style={{ background: "rgba(96,165,250,.1)", color: "#60a5fa", border: "1px solid rgba(96,165,250,.2)" }}
            >
              <Target className="w-3 h-3" />
              Strategic positioning analysis
            </div>
            <h2 className="text-3xl font-black mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
              Know exactly where they sit in the market.
            </h2>
            <p className="text-base leading-relaxed mb-6" style={{ color: "var(--muted)" }}>
              StoreScout scores every competitor across 4 dimensions: Market Position, Launch Velocity, Promo Intensity, and Catalog Complexity. One glance tells you how aggressive they&apos;re being and where they&apos;re vulnerable.
            </p>
            <ul className="space-y-3">
              {[
                "Market Position — where they sit on price vs. volume",
                "Launch Velocity — how fast they're growing their catalog",
                "Promo Intensity — how heavily they rely on discounts",
                "Catalog Complexity — breadth and variety of their range",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm" style={{ color: "var(--muted)" }}>
                  <Check className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "#a3f000" }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <BrowserChrome url="app.storescout.com/dashboard/gymshark">
            <Image
              src="/screenshots/competitive-positioning.png"
              alt="Competitive positioning analysis showing Market Position, Launch Velocity, Promo Intensity, and Catalog Complexity scores"
              width={870}
              height={505}
              className="w-full h-auto"
            />
          </BrowserChrome>
        </div>
      </div>

      {/* ── Intelligence Brief section ───────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-10">
          <div
            className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-5"
            style={{ background: "rgba(163,240,0,.1)", color: "#a3f000", border: "1px solid rgba(163,240,0,.2)" }}
          >
            <Sparkles className="w-3 h-3" />
            AI-powered weekly brief
          </div>
          <h2 className="text-3xl font-black mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Your AI strategist, already looking at the data.
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            Every week, Claude analyzes 7 days of scan data and writes a 4-card brief: what changed, what it signals, where your opening is, and exactly what to do. Not summaries — actionable moves.
          </p>
        </div>
        <IntelligenceBriefPreview />
      </div>

      {/* ── Alert email section ──────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div
              className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-5"
              style={{ background: "rgba(239,68,68,.1)", color: "#f87171", border: "1px solid rgba(239,68,68,.2)" }}
            >
              <Bell className="w-3 h-3" />
              In your inbox within 15 minutes
            </div>
            <h2 className="text-3xl font-black mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
              Beat your competitors to their own move.
            </h2>
            <p className="text-base leading-relaxed mb-6" style={{ color: "var(--muted)" }}>
              By the time a competitor&apos;s flash sale shows up on Reddit, their best customers have already bought. StoreScout alerts you while the sale is still running — so you can match it, counter it, or let it pass informed.
            </p>
            <ul className="space-y-3">
              {[
                "Price drops ≥10% trigger an immediate alert",
                "Flash sale events grouped and explained by AI",
                "Product list with exact price changes included",
                "\"Your Move\" action item in every email",
                "New launches and discount campaigns tracked start-to-finish",
              ].map((item) => (
                <li key={item} className="flex items-center gap-3 text-sm" style={{ color: "var(--muted)" }}>
                  <Check className="w-4 h-4 shrink-0" style={{ color: "#a3f000" }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <AlertEmailPreview />
        </div>
      </div>

      {/* ── Screenshot showcase grid ─────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Every angle covered
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            Launch timelines, discount depth, top products, pricing patterns — everything a Shopify operator needs to make better decisions, faster.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Launch timeline */}
          <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid #1a2744" }}>
            <div className="px-4 py-3 border-b flex items-center gap-2" style={{ background: "#080f1e", borderColor: "#1a2744" }}>
              <Rocket className="w-3.5 h-3.5" style={{ color: "#a3f000" }} />
              <span className="text-xs font-semibold" style={{ color: "#eef3fa" }}>Launch Velocity</span>
              <span className="text-[10px] ml-auto" style={{ color: "#3a5070" }}>gymshark.com</span>
            </div>
            <Image
              src="/screenshots/launch-timeline.png"
              alt="Launch velocity timeline showing monthly product launches for gymshark.com"
              width={740}
              height={891}
              className="w-full h-auto"
            />
          </div>

          {/* Top products */}
          <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid #1a2744" }}>
            <div className="px-4 py-3 border-b flex items-center gap-2" style={{ background: "#080f1e", borderColor: "#1a2744" }}>
              <TrendingUp className="w-3.5 h-3.5" style={{ color: "#60a5fa" }} />
              <span className="text-xs font-semibold" style={{ color: "#eef3fa" }}>Winning Products</span>
              <span className="text-[10px] ml-auto" style={{ color: "#3a5070" }}>gymshark.com</span>
            </div>
            <Image
              src="/screenshots/top-products.png"
              alt="Top products and winning catalog analysis for gymshark.com"
              width={841}
              height={634}
              className="w-full h-auto"
            />
          </div>

          {/* Pricing & discounts */}
          <div className="rounded-2xl overflow-hidden md:col-span-2" style={{ border: "1px solid #1a2744" }}>
            <div className="px-4 py-3 border-b flex items-center gap-2" style={{ background: "#080f1e", borderColor: "#1a2744" }}>
              <Tag className="w-3.5 h-3.5" style={{ color: "#f59e0b" }} />
              <span className="text-xs font-semibold" style={{ color: "#eef3fa" }}>Pricing &amp; Discount Analysis</span>
              <span className="text-[10px] ml-auto" style={{ color: "#3a5070" }}>gymshark.com · 90-day view</span>
            </div>
            <Image
              src="/screenshots/pricing-discount.png"
              alt="Pricing and discount analysis showing 90-day history for gymshark.com"
              width={860}
              height={713}
              className="w-full h-auto"
            />
          </div>
        </div>
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
          <div className="hidden md:block absolute top-6 left-[calc(16.67%+24px)] right-[calc(16.67%+24px)] h-px"
            style={{ background: "linear-gradient(90deg, transparent, rgba(163,240,0,.3), transparent)" }} />
          {[
            {
              step: "01", icon: Package, title: "Paste any Shopify URL",
              desc: "Enter a competitor's store URL. We verify it's a Shopify store and kick off the first scan immediately — no browser extension needed.",
            },
            {
              step: "02", icon: TrendingUp, title: "We analyze their full catalog",
              desc: "StoreScout fetches their entire product catalog, analyzes pricing patterns, launch velocity, and discount strategy. First results in under 2 minutes.",
            },
            {
              step: "03", icon: Bell, title: "Get alerted when they move",
              desc: "Price drops, new launches, sale events — you're notified by email within 15 minutes. The dashboard updates automatically every day.",
            },
          ].map(({ step, icon: Icon, title, desc }) => (
            <div key={step} className="text-center relative">
              <div
                className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4 relative z-10"
                style={{ background: "rgba(163,240,0,.1)", border: "1px solid rgba(163,240,0,.2)" }}
              >
                <Icon className="w-5 h-5" style={{ color: "#a3f000" }} />
              </div>
              <div className="text-[10px] font-black uppercase tracking-widest mb-2" style={{ color: "rgba(163,240,0,.4)" }}>
                Step {step}
              </div>
              <h3 className="font-bold mb-2" style={{ color: "var(--text)" }}>{title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Who it's for ────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Built for two types of operators
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            Whether you run one brand or manage 50 clients, StoreScout adapts to your workflow.
          </p>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="rounded-2xl p-7" style={{ background: "rgba(163,240,0,.04)", border: "1px solid rgba(163,240,0,.15)" }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-5" style={{ background: "rgba(163,240,0,.12)" }}>
              <Store className="w-5 h-5" style={{ color: "#a3f000" }} />
            </div>
            <h3 className="text-lg font-bold mb-2" style={{ color: "var(--text)" }}>DTC brand operators</h3>
            <p className="text-sm leading-relaxed mb-5" style={{ color: "var(--muted)" }}>
              You make pricing and product decisions every week. StoreScout keeps you ahead of the 2–4 competitors who matter most — without spreadsheets or manual checking.
            </p>
            <ul className="space-y-2">
              {[
                "Know before you react, not after",
                "Match competitor promos same-day",
                "Spot product trends early",
                "Up to 10 competitors on Pro",
              ].map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm" style={{ color: "var(--muted)" }}>
                  <Check className="w-3.5 h-3.5 shrink-0" style={{ color: "#a3f000" }} />
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl p-7" style={{ background: "rgba(96,165,250,.04)", border: "1px solid rgba(96,165,250,.15)" }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-5" style={{ background: "rgba(96,165,250,.12)" }}>
              <Users className="w-5 h-5" style={{ color: "#60a5fa" }} />
            </div>
            <h3 className="text-lg font-bold mb-2" style={{ color: "var(--text)" }}>Shopify agencies</h3>
            <p className="text-sm leading-relaxed mb-5" style={{ color: "var(--muted)" }}>
              Run competitive analysis for multiple clients without the overhead. Shareable report URLs replace PDF attachments — clients bookmark them and ask for more.
            </p>
            <ul className="space-y-2">
              {[
                "Track 50 competitors across all clients",
                "Shareable report URLs per brand",
                "White-label ready with your branding",
                "Weekly AI digest per competitor",
              ].map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm" style={{ color: "var(--muted)" }}>
                  <Check className="w-3.5 h-3.5 shrink-0" style={{ color: "#60a5fa" }} />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* ── Features grid ───────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Everything in one place
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            Built for Shopify operators who make pricing and product decisions every week — and can&apos;t afford Similarweb.
          </p>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div
            className="rounded-2xl p-7 flex flex-col justify-between md:row-span-2"
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
                When a competitor drops 20+ prices in one session, StoreScout detects it as a &ldquo;Flash Sale&rdquo; event and emails you within 15 minutes — before it shows up on social.
              </p>
            </div>
            <div className="rounded-xl p-4" style={{ background: "rgba(0,0,0,.3)", border: "1px solid rgba(239,68,68,.2)" }}>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full"
                  style={{ background: "rgba(239,68,68,.15)", color: "#f87171" }}>⚡ Flash sale</span>
                <span className="text-xs" style={{ color: "#94a3b8" }}>gymshark.com · just now</span>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: "#94a3b8" }}>
                7 products dropped ≥20% — avg −24.6%. Summer clearance or aggressive acquisition push.
              </p>
            </div>
          </div>
          {[
            { icon: TrendingDown, title: "90-day price history", desc: "See how prices have moved over time. Spot seasonal patterns and predict the next sale before it happens." },
            { icon: Sparkles, title: "AI weekly digest", desc: "Every Monday, Claude writes a 4-card brief on what changed, what it signals, and exactly what to do about it." },
            { icon: Rocket, title: "Launch velocity tracking", desc: "How many products are they launching per month? Are they accelerating into a new category or pulling back?" },
            { icon: Tag, title: "Discount monitoring", desc: "Track what % of their catalog is on sale, the average depth, and when new sale events start and end." },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="rounded-2xl p-6" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-4" style={{ background: "rgba(163,240,0,.1)" }}>
                <Icon className="w-5 h-5" style={{ color: "#a3f000" }} />
              </div>
              <h3 className="font-bold mb-2" style={{ color: "var(--text)" }}>{title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Testimonials ────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-black mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            What operators say
          </h2>
          <p className="text-sm" style={{ color: "var(--muted)" }}>From our early access group</p>
        </div>
        <div className="grid md:grid-cols-3 gap-5">
          {TESTIMONIALS.map(({ quote, name, role }) => (
            <div
              key={name}
              className="rounded-2xl p-6 flex flex-col gap-4"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <div className="flex gap-0.5">
                {[1,2,3,4,5].map((s) => (
                  <span key={s} className="text-sm" style={{ color: "#a3f000" }}>★</span>
                ))}
              </div>
              <p className="text-sm leading-relaxed flex-1" style={{ color: "var(--muted)" }}>
                &ldquo;{quote}&rdquo;
              </p>
              <div>
                <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>{name}</p>
                <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{role}</p>
              </div>
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
            Extensions only work while you&apos;re browsing. Reports are a one-time snapshot. StoreScout monitors continuously — whether you&apos;re logged in or not.
          </p>
        </div>
        <div className="rounded-2xl p-6 md:p-8" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
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
            <div key={label} className="flex items-start gap-4 rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
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
          <p className="text-sm mt-2" style={{ color: "var(--accent)" }}>
            Annual plans available — save 20%
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {PLANS.map(({ name, price, sub, annualNote, highlight, features, cta, href }) => (
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
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-3xl font-black" style={{ color: highlight ? "#a3f000" : "var(--text)" }}>{price}</span>
                <span className="text-sm" style={{ color: "var(--muted)" }}>{sub}</span>
              </div>
              {annualNote && (
                <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>{annualNote}</p>
              )}
              {!annualNote && <div className="mb-5" />}
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
                style={highlight
                  ? { background: "#a3f000", color: "#060d18" }
                  : { border: "1px solid var(--border)", color: "var(--text)" }}
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
      <div className="max-w-2xl mx-auto px-6 pb-28" id="faq">
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
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-32 rounded-full blur-3xl pointer-events-none"
            style={{ background: "rgba(163,240,0,.12)" }}
          />
          <div className="relative">
            <h2 className="text-3xl md:text-4xl font-black mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
              Your competitors are already moving.<br />
              <span style={{ color: "#a3f000" }}>Now you will be too.</span>
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
            <p className="text-sm mt-4" style={{ color: "var(--muted)", opacity: 0.6 }}>
              No credit card · Cancel anytime · Setup in 60 seconds
            </p>
          </div>
        </div>
      </div>

      {/* ── PeerPush badge ──────────────────────────────────────────────────── */}
      <div className="flex justify-center pb-12">
        <a href="https://peerpush.net/p/storescout" target="_blank" rel="noopener" style={{ width: 230 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="https://peerpush.net/p/storescout/badge.png" alt="StoreScout on PeerPush" style={{ width: 230 }} />
        </a>
      </div>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <footer className="border-t" style={{ borderColor: "var(--border)" }}>
        <div className="max-w-5xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md flex items-center justify-center" style={{ background: "var(--accent)" }}>
              <Zap className="w-3.5 h-3.5" style={{ color: "#0a0a0f" }} />
            </div>
            <span className="font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="#how-it-works" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>How it works</Link>
            <Link href="#pricing" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>Pricing</Link>
            <Link href="#faq" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>FAQ</Link>
            <Link href="/auth/login" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>Sign in</Link>
          </div>
          <p className="text-xs" style={{ color: "var(--muted)" }}>© 2025 StoreScout</p>
        </div>
      </footer>

    </div>
  );
}
