import Link from "next/link";
import {
  Zap, Bell, ArrowRight, Check, Shield, Clock,
  TrendingUp, TrendingDown, Package, Tag, Sparkles,
  ChevronRight, Store, Users, Target, Eye, Rocket,
} from "lucide-react";
import { FaqAccordion } from "@/components/landing/FaqAccordion";
import { Testimonials } from "@/components/landing/Testimonials";
import { HeroScan } from "@/components/landing/HeroScan";

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

// ── Inline UI components (exact replicas of live app) ─────────────────────────

function BrowserChrome({ url, children }: { url: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md overflow-hidden shadow-2xl" style={{ background: "#0B0C0A", border: "1px solid #262A22" }}>
      <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ background: "#101110", borderColor: "#262A22" }}>
        <div className="flex gap-1.5">
          <span className="w-3 h-3 rounded-full" style={{ background: "#ff5f57" }} />
          <span className="w-3 h-3 rounded-full" style={{ background: "#ffbd2e" }} />
          <span className="w-3 h-3 rounded-full" style={{ background: "#28c840" }} />
        </div>
        <div className="flex-1 mx-3 rounded-md px-3 py-1 text-xs font-mono" style={{ background: "#0B0C0A", color: "#6C7164" }}>
          {url}
        </div>
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" style={{ color: "#FFB224" }} />
          <span className="text-[10px] font-semibold" style={{ color: "#FFB224" }}>LIVE</span>
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
      className="rounded-md overflow-hidden"
      style={{
        background: "rgba(242,85,90,.05)",
        border: "1px solid rgba(242,85,90,.25)",
        boxShadow: "0 0 0 1px rgba(242,85,90,.06), 0 8px 32px rgba(0,0,0,.3)",
      }}
    >
      <div className="flex items-center justify-between px-5 pt-4 pb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <Zap className="w-4 h-4 shrink-0" style={{ color: "#F2555A" }} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full shrink-0"
                style={{ background: "rgba(242,85,90,.2)", color: "#F2555A" }}>Flash Sale</span>
              <span className="text-xs font-semibold" style={{ color: "#ECEEE6" }}>gymshark.com</span>
            </div>
            <p className="text-sm font-bold mt-1 leading-snug" style={{ color: "#ECEEE6" }}>
              7 products dropped ≥20% — avg −24.6%
            </p>
          </div>
        </div>
        <span className="text-[11px] shrink-0 ml-3" style={{ color: "#6C7164" }}>12m ago</span>
      </div>
      <div className="mx-5 mb-3 px-3.5 py-3 rounded-md text-xs leading-relaxed"
        style={{ background: "rgba(0,0,0,.2)", color: "#A8AC9E" }}>
        <span className="font-semibold" style={{ color: "#F2555A" }}>Why this matters · </span>
        Summer clearance or aggressive acquisition push. Flash sales this size typically run 48–72h and are often paired with Meta spend within hours.
      </div>
      <div className="mx-5 mb-4 px-3.5 py-3 rounded-md text-xs leading-relaxed"
        style={{ background: "rgba(255,178,36,.05)", border: "1px solid rgba(255,178,36,.18)" }}>
        <span className="font-bold" style={{ color: "#FFB224" }}>▶ Your move · </span>
        <span style={{ color: "#A8AC9E" }}>Open Meta Ads Manager, duplicate your best ad set targeting Gymshark followers. Test &ldquo;Gymshark is on sale. We never are.&rdquo; as headline copy — run $10/day for 5 days and compare CTR to your control.</span>
      </div>
      <div className="flex items-center justify-between px-5 py-2 text-xs font-semibold border-t"
        style={{ borderColor: "rgba(242,85,90,.15)", color: "#6C7164" }}>
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
      className="rounded-md overflow-hidden"
      style={{
        background: "rgba(255,178,36,.04)",
        border: "1px solid rgba(255,178,36,.2)",
        boxShadow: "0 0 0 1px rgba(255,178,36,.06), 0 8px 32px rgba(0,0,0,.3)",
      }}
    >
      <div className="flex items-center justify-between px-5 pt-4 pb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <Rocket className="w-4 h-4 shrink-0" style={{ color: "#FFB224" }} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full shrink-0"
                style={{ background: "rgba(255,178,36,.2)", color: "#FFB224" }}>Launch Burst</span>
              <span className="text-xs font-semibold" style={{ color: "#ECEEE6" }}>fashionnova.com</span>
            </div>
            <p className="text-sm font-bold mt-1 leading-snug" style={{ color: "#ECEEE6" }}>
              19 products launched in 4 hours
            </p>
          </div>
        </div>
        <span className="text-[11px] shrink-0 ml-3" style={{ color: "#6C7164" }}>1h ago</span>
      </div>
      <div className="mx-5 mb-3 px-3.5 py-3 rounded-md text-xs leading-relaxed"
        style={{ background: "rgba(0,0,0,.2)", color: "#A8AC9E" }}>
        <span className="font-semibold" style={{ color: "#FFB224" }}>Why this matters · </span>
        A burst this large usually precedes a paid push. Expect heavy Meta spend on these SKUs within 48 hours — their best-case launch window.
      </div>
      <div className="mx-5 mb-4 px-3.5 py-3 rounded-md text-xs leading-relaxed"
        style={{ background: "rgba(255,178,36,.05)", border: "1px solid rgba(255,178,36,.18)" }}>
        <span className="font-bold" style={{ color: "#FFB224" }}>▶ Your move · </span>
        <span style={{ color: "#A8AC9E" }}>Watch fashionnova.com&apos;s social and email over the next 72h. If they&apos;re entering a category you cover, get your version into ads before their campaign peaks.</span>
      </div>
      <div className="flex items-center justify-between px-5 py-2 text-xs font-semibold border-t"
        style={{ borderColor: "rgba(255,178,36,.15)", color: "#6C7164" }}>
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
      className="rounded-md overflow-hidden"
      style={{
        background: "rgba(255,178,36,.04)",
        border: "1px solid rgba(255,178,36,.2)",
        boxShadow: "0 0 0 1px rgba(255,178,36,.06), 0 8px 32px rgba(0,0,0,.3)",
      }}
    >
      <div className="flex items-center justify-between px-5 pt-4 pb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <TrendingUp className="w-4 h-4 shrink-0" style={{ color: "#FFB224" }} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full shrink-0"
                style={{ background: "rgba(255,178,36,.2)", color: "#FFB224" }}>Prices Rising</span>
              <span className="text-xs font-semibold" style={{ color: "#ECEEE6" }}>allbirds.com</span>
            </div>
            <p className="text-sm font-bold mt-1 leading-snug" style={{ color: "#ECEEE6" }}>
              8 core styles raised +18% avg
            </p>
          </div>
        </div>
        <span className="text-[11px] shrink-0 ml-3" style={{ color: "#6C7164" }}>3h ago</span>
      </div>
      <div className="mx-5 mb-3 px-3.5 py-3 rounded-md text-xs leading-relaxed"
        style={{ background: "rgba(0,0,0,.2)", color: "#A8AC9E" }}>
        <span className="font-semibold" style={{ color: "#FFB224" }}>Why this matters · </span>
        Allbirds raised prices on 8 core styles. Their price-sensitive customers are now actively comparison shopping — this is your window.
      </div>
      <div className="mx-5 mb-4 px-3.5 py-3 rounded-md text-xs leading-relaxed"
        style={{ background: "rgba(255,178,36,.05)", border: "1px solid rgba(255,178,36,.18)" }}>
        <span className="font-bold" style={{ color: "#FFB224" }}>▶ Your move · </span>
        <span style={{ color: "#A8AC9E" }}>Launch a Google Shopping campaign targeting their product names — their price-sensitive customers are now actively looking for alternatives.</span>
      </div>
      <div className="flex items-center justify-between px-5 py-2 text-xs font-semibold border-t"
        style={{ borderColor: "rgba(255,178,36,.15)", color: "#6C7164" }}>
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
      className="rounded-md overflow-hidden"
      style={{
        background: "#101110",
        border: "1px solid rgba(255,178,36,.2)",
      }}
    >
      <div className="p-6 sm:p-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-md flex items-center justify-center shrink-0"
              style={{ background: "rgba(255,178,36,.12)", border: "1px solid rgba(255,178,36,.2)" }}>
              <Sparkles className="w-4 h-4" style={{ color: "#FFB224" }} />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
                style={{ background: "rgba(255,178,36,.12)", color: "#FFB224" }}>
                AI Intelligence Brief
              </span>
              <h3 className="text-base font-bold mt-1" style={{ color: "#ECEEE6" }}>
                4 things you should know about{" "}
                <span style={{ color: "#FFB224" }}>gymshark.com</span>
              </h3>
            </div>
          </div>
        </div>

        {/* 3 cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          {/* Signal card */}
          <div className="rounded-md p-5" style={{ background: "rgba(255,178,36,.07)", border: "1px solid rgba(255,178,36,.18)" }}>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: "rgba(255,178,36,.18)" }}>
                <Target className="w-4 h-4" style={{ color: "#FFB224" }} />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#FFB224" }}>Most notable signal</span>
            </div>
            <h4 className="font-bold text-sm leading-snug mb-2" style={{ color: "#ECEEE6" }}>
              Seasonal discount cycle is accelerating
            </h4>
            <p className="text-sm leading-relaxed" style={{ color: "#6C7164" }}>
              Gymshark pushed 34% of their catalog on sale this week — up from 18% last week. This is their fastest discount ramp in 6 months.
            </p>
          </div>

          {/* Opportunity card */}
          <div className="rounded-md p-5" style={{ background: "rgba(255,178,36,.07)", border: "1px solid rgba(255,178,36,.18)" }}>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: "rgba(255,178,36,.18)" }}>
                <TrendingUp className="w-4 h-4" style={{ color: "#FFB224" }} />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#FFB224" }}>Your opening</span>
            </div>
            <h4 className="font-bold text-sm leading-snug mb-2" style={{ color: "#ECEEE6" }}>
              Full-price positioning window is open
            </h4>
            <p className="text-sm leading-relaxed" style={{ color: "#6C7164" }}>
              While Gymshark discounts, their discount-fatigued customers are your best acquisition target. Push quality messaging this week.
            </p>
          </div>

          {/* Watch card */}
          <div className="rounded-md p-5" style={{ background: "rgba(255,178,36,.07)", border: "1px solid rgba(255,178,36,.18)" }}>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: "rgba(255,178,36,.18)" }}>
                <Eye className="w-4 h-4" style={{ color: "#FFB224" }} />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#FFB224" }}>Watch this</span>
            </div>
            <h4 className="font-bold text-sm leading-snug mb-2" style={{ color: "#ECEEE6" }}>
              14 new training styles this month
            </h4>
            <p className="text-sm leading-relaxed" style={{ color: "#6C7164" }}>
              Strong launch velocity (+40% vs last month). A paid push on new training gear is likely within 2 weeks based on prior patterns.
            </p>
          </div>
        </div>

        {/* Action card — full width */}
        <div className="rounded-md p-5 mb-5" style={{ background: "rgba(76,195,138,.07)", border: "2px solid rgba(76,195,138,.18)" }}>
          <div className="flex items-start gap-4">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
              style={{ background: "rgba(76,195,138,.18)" }}>
              <Zap className="w-4 h-4" style={{ color: "#4CC38A" }} />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#4CC38A" }}>Your move</span>
              <h4 className="font-bold text-sm leading-snug mt-1 mb-1.5" style={{ color: "#ECEEE6" }}>
                Launch email campaign targeting Gymshark&apos;s discount-fatigued audience this week
              </h4>
              <p className="text-sm leading-relaxed" style={{ color: "#6C7164" }}>
                Send your email list with a full-price quality angle before Gymshark&apos;s sale ends. Subject: &ldquo;We&apos;re not on sale. Here&apos;s why that&apos;s better.&rdquo; Gymshark&apos;s discount-heavy week is creating the contrast you need.
              </p>
            </div>
          </div>
        </div>

        <div className="w-full flex items-center justify-center gap-2 py-3 rounded-md font-semibold text-sm"
          style={{ background: "#FFB224", color: "var(--ink)" }}>
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
      className="rounded-md overflow-hidden shadow-xl"
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
      <div style={{ background: "#0B0C0A", padding: "20px 20px 24px" }}>
        {/* Logo */}
        <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 24, height: 24, background: "#FFB224", borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Zap className="w-3.5 h-3.5" style={{ color: "#0B0C0A" }} />
          </div>
          <span style={{ color: "#FFB224", fontWeight: 700, fontSize: 14, letterSpacing: -0.3 }}>StoreScout</span>
          <span style={{ color: "#6C7164", fontSize: 11, marginLeft: "auto" }}>14 minutes ago</span>
        </div>

        {/* Alert card */}
        <div style={{ background: "rgba(242,85,90,.12)", border: "1px solid rgba(242,85,90,.25)", borderRadius: 10, padding: "12px 14px", marginBottom: 12 }}>
          <p style={{ color: "#F2555A", fontWeight: 700, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>
            ⚡ Flash sale detected
          </p>
          <p style={{ color: "#ECEEE6", fontWeight: 700, fontSize: 16, margin: "0 0 4px" }}>gymshark.com</p>
          <p style={{ color: "#A8AC9E", fontSize: 12, margin: 0 }}>7 products dropped ≥20% — avg −24.6%</p>
        </div>

        {/* Product list */}
        <div style={{ marginBottom: 12 }}>
          {[
            ["Vital Seamless 2.0 Leggings", "$54 → $38", "−30%"],
            ["Apex Seamless Sports Bra", "$44 → $31", "−30%"],
            ["Speed Shorts", "$42 → $29", "−31%"],
          ].map(([name, prices, delta]) => (
            <div key={name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,.05)" }}>
              <span style={{ color: "#A8AC9E", fontSize: 11, flex: 1 }}>{name}</span>
              <span style={{ color: "#6C7164", fontSize: 11, marginRight: 8 }}>{prices}</span>
              <span style={{ color: "#F2555A", fontSize: 11, fontWeight: 700 }}>{delta}</span>
            </div>
          ))}
          <p style={{ color: "#6C7164", fontSize: 10, marginTop: 6, marginBottom: 0 }}>+ 4 more products</p>
        </div>

        {/* Your move block */}
        <div style={{ background: "rgba(255,178,36,.08)", borderLeft: "3px solid #FFB224", borderRadius: 8, padding: "10px 12px", marginBottom: 14 }}>
          <p style={{ color: "#FFB224", fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px" }}>▶ Your Move</p>
          <p style={{ color: "#A8AC9E", fontSize: 12, lineHeight: 1.5, margin: 0 }}>
            Match with a counter-offer or push quality messaging. Flash sales this size typically run 48–72h.
          </p>
        </div>

        <a href="#"
          style={{ display: "inline-block", background: "#FFB224", color: "var(--ink)", fontWeight: 700, fontSize: 13, padding: "9px 20px", borderRadius: 8, textDecoration: "none" }}>
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
    { feature: "Instant alerts on critical moves", ext: false, report: false, us: true },
    { feature: "Works without a Chrome tab", ext: false, report: true,  us: true },
    { feature: "AI weekly digest",           ext: false, report: false, us: true },
    { feature: "Multi-competitor dashboard", ext: false, report: false, us: true },
    { feature: "Starts free, no card",       ext: false, report: false, us: true },
  ];
  const col = (v: boolean) => v
    ? <span className="text-base" style={{ color: "#FFB224" }}>✓</span>
    : <span className="text-base opacity-20" style={{ color: "#A8AC9E" }}>✕</span>;

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
              style={{ color: "#FFB224", background: "rgba(255,178,36,.07)", border: "1px solid rgba(255,178,36,.2)", borderBottom: "none" }}
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
                style={{ background: "rgba(255,178,36,.07)", border: "1px solid rgba(255,178,36,.2)", borderTop: "none", borderBottom: i === rows.length - 1 ? undefined : "none" }}
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

// ── Inline product mockups (replace PDF-era screenshots; always current) ──────

function MiniKpi({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="rounded-md px-3 py-2.5" style={{ background: "#101110", border: "1px solid #262A22" }}>
      <p className="text-lg font-bold leading-none" style={{ color: accent || "#ECEEE6", fontFamily: "var(--font-mono)" }}>{value}</p>
      <p className="text-[10px] mt-1.5" style={{ color: "#6C7164" }}>{label}</p>
    </div>
  );
}

// "Full pricing intelligence" — dashboard-style pricing view
function PricingDashboardMock() {
  const dist = [["<$25", 18], ["$25–49", 64], ["$50–99", 100], ["$100–199", 47], ["$200+", 16]] as const;
  return (
    <div className="p-5 sm:p-6" style={{ background: "#0B0C0A" }}>
      <div className="grid grid-cols-4 gap-2.5 mb-5">
        <MiniKpi label="Products" value="312" />
        <MiniKpi label="Median price" value="$58" accent="#FFB224" />
        <MiniKpi label="On sale" value="44%" accent="#FFB224" />
        <MiniKpi label="New · 30d" value="18" accent="#4CC38A" />
      </div>
      <div className="rounded-md p-4" style={{ background: "#101110", border: "1px solid #262A22" }}>
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-semibold" style={{ color: "#ECEEE6" }}>Price distribution</span>
          <span className="text-[10px]" style={{ color: "#6C7164" }}>p25 $34 · median $58 · p75 $96</span>
        </div>
        <div className="flex items-end gap-2 h-28">
          {dist.map(([label, h]) => (
            <div key={label} className="flex-1 flex flex-col items-center gap-1.5">
              <div className="w-full rounded-t" style={{ height: `${h}%`, background: "linear-gradient(180deg,#FFB224,#1e40af)", minHeight: 6 }} />
              <span className="text-[9px]" style={{ color: "#6C7164" }}>{label}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2.5 mt-3">
        <MiniKpi label="Discounted catalog" value="44%" accent="#FFB224" />
        <MiniKpi label="Median discount" value="−32%" accent="#F2555A" />
        <MiniKpi label="In stock" value="91%" accent="#4CC38A" />
      </div>
    </div>
  );
}

function ScoreBar({ label, score, tag }: { label: string; score: number; tag: string }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-medium" style={{ color: "#ECEEE6" }}>{label}</span>
        <span className="text-[11px] font-semibold" style={{ color: "#FFB224" }}>{tag}</span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: "#0d1626" }}>
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: "linear-gradient(90deg,#FFB224,#FFB224)" }} />
      </div>
    </div>
  );
}

// "Know exactly where they sit" — positioning scores
function PositioningMock() {
  return (
    <div className="p-6" style={{ background: "#0B0C0A" }}>
      <div className="space-y-5">
        <ScoreBar label="Market Position" score={72} tag="Premium" />
        <ScoreBar label="Launch Velocity" score={84} tag="Aggressive" />
        <ScoreBar label="Promo Intensity" score={58} tag="Moderate" />
        <ScoreBar label="Catalog Complexity" score={66} tag="Broad" />
      </div>
    </div>
  );
}

// "Launch Velocity" — monthly launch bar chart
function LaunchVelocityMock() {
  const months = [3, 5, 4, 8, 6, 11, 9, 14, 12, 18, 16, 22];
  const max = Math.max(...months);
  return (
    <div className="p-5" style={{ background: "#0B0C0A" }}>
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-2xl font-bold" style={{ color: "#ECEEE6", fontFamily: "var(--font-mono)" }}>22</span>
        <span className="text-xs" style={{ color: "#6C7164" }}>launches last month · accelerating ↑</span>
      </div>
      <div className="flex items-end gap-1.5 h-40">
        {months.map((v, i) => (
          <div key={i} className="flex-1 rounded-t" style={{ height: `${(v / max) * 100}%`, background: i >= 9 ? "#FFB224" : "rgba(255,178,36,.35)", minHeight: 4 }} />
        ))}
      </div>
      <div className="flex justify-between mt-2 text-[9px]" style={{ color: "#6C7164" }}>
        <span>Jul</span><span>Oct</span><span>Jan</span><span>Apr</span><span>Jun</span>
      </div>
    </div>
  );
}

// "Winning Products" — scored product list
function WinningProductsMock() {
  const rows = [
    { t: "Vital Seamless Leggings", p: "$60", v: "Hero Product", c: "#FFB224" },
    { t: "Power Hoodie", p: "$75", v: "Strong Performer", c: "#4CC38A" },
    { t: "Apex Sports Bra", p: "$45", v: "Watch First", c: "#FFB224" },
    { t: "Studio Joggers", p: "$68", v: "Watch First", c: "#FFB224" },
  ];
  return (
    <div style={{ background: "#0B0C0A" }}>
      {rows.map((r, i) => (
        <div key={r.t} className="flex items-center gap-3 px-4 py-3" style={i < rows.length - 1 ? { borderBottom: "1px solid #262A22" } : undefined}>
          <span className="text-[11px] w-4 text-center shrink-0" style={{ color: "#6C7164", fontFamily: "var(--font-mono)" }}>{i + 1}</span>
          <div className="w-9 h-9 rounded-lg shrink-0" style={{ background: "#1B1E19" }} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate" style={{ color: "#ECEEE6" }}>{r.t}</p>
            <p className="text-xs" style={{ color: "#6C7164" }}>{r.p} · full price · 1.2yr in catalog</p>
          </div>
          <span className="text-[10px] font-bold px-2 py-1 rounded-lg shrink-0" style={{ background: `${r.c}1f`, color: r.c }}>{r.v}</span>
        </div>
      ))}
    </div>
  );
}

// "Pricing & Discount Analysis" — distribution + discount depth
function PricingDiscountMock() {
  const dist = [22, 48, 100, 63, 28, 12];
  const max = Math.max(...dist);
  return (
    <div className="p-5 grid sm:grid-cols-2 gap-5" style={{ background: "#0B0C0A" }}>
      <div>
        <p className="text-xs font-semibold mb-3" style={{ color: "#ECEEE6" }}>Price distribution</p>
        <div className="flex items-end gap-1.5 h-32">
          {dist.map((v, i) => (
            <div key={i} className="flex-1 rounded-t" style={{ height: `${(v / max) * 100}%`, background: "linear-gradient(180deg,#FFB224,#1e40af)", minHeight: 4 }} />
          ))}
        </div>
      </div>
      <div className="space-y-3">
        <div className="rounded-md p-3.5" style={{ background: "#101110", border: "1px solid #262A22" }}>
          <p className="text-[11px]" style={{ color: "#6C7164" }}>Discounted catalog</p>
          <div className="flex items-center gap-2 mt-1.5">
            <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: "#0d1626" }}>
              <div className="h-full rounded-full" style={{ width: "44%", background: "#FFB224" }} />
            </div>
            <span className="text-sm font-bold" style={{ color: "#FFB224", fontFamily: "var(--font-mono)" }}>44%</span>
          </div>
        </div>
        <MiniKpi label="Median discount depth" value="−32%" accent="#F2555A" />
        <MiniKpi label="Deepest active markdown" value="−55%" accent="#F2555A" />
      </div>
    </div>
  );
}


// ── Journey mocks: Discover + Win ─────────────────────────────────────────────

function DiscoveryMock() {
  const verified = [
    { domain: "ryderwear.com", conf: 94, reason: "gym apparel, similar $40-70 price point" },
    { domain: "youngla.com", conf: 91, reason: "same audience, aggressive launch cadence" },
    { domain: "rawgear.com", conf: 88, reason: "emerging lifter brand, overlapping fits" },
  ];
  return (
    <div className="rounded-md overflow-hidden shadow-2xl" style={{ background: "#0B0C0A", border: "1px solid #262A22" }}>
      <div className="px-4 py-3 border-b flex items-center gap-2" style={{ background: "#101110", borderColor: "#262A22" }}>
        <Sparkles className="w-3.5 h-3.5" style={{ color: "#A8AC9E" }} />
        <span className="text-xs font-semibold" style={{ color: "#ECEEE6" }}>Find competitors</span>
        <span className="text-[10px] ml-auto" style={{ color: "#6C7164" }}>&ldquo;gym apparel, $40&ndash;80, lifters&rdquo;</span>
      </div>
      <div className="p-4 space-y-2">
        <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "#6C7164" }}>
          Verified Shopify · trackable — 3
        </p>
        {verified.map((v) => (
          <div key={v.domain} className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-md" style={{ background: "#161814", border: "1px solid #262A22" }}>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-xs font-mono font-semibold" style={{ color: "#ECEEE6" }}>{v.domain}</p>
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: "rgba(76,195,138,.1)", color: "#4CC38A", border: "1px solid rgba(76,195,138,.2)" }}>
                  {v.conf}% Shopify
                </span>
              </div>
              <p className="text-[10px] truncate mt-0.5" style={{ color: "#6C7164" }}>{v.reason}</p>
            </div>
            <span className="text-[10px] font-semibold shrink-0 px-2 py-1 rounded" style={{ background: "rgba(255,178,36,.1)", color: "#FFB224", border: "1px solid rgba(255,178,36,.2)" }}>
              Track →
            </span>
          </div>
        ))}
        <p className="text-[10px] font-bold uppercase tracking-widest pt-2" style={{ color: "#6C7164" }}>
          Direct competitors we can&apos;t monitor yet — 1
        </p>
        <div className="flex items-center justify-between gap-3 px-3 py-2 rounded-md" style={{ background: "#101110", border: "1px dashed #262A22", opacity: 0.7 }}>
          <p className="text-xs font-mono" style={{ color: "#A8AC9E" }}>nike.com</p>
          <span className="text-[10px]" style={{ color: "#6C7164" }}>Not Shopify</span>
        </div>
      </div>
    </div>
  );
}

function WinCompareMock() {
  const rows = [
    { label: "Median price", you: "$54", them: "$48", verdict: "Premium position", color: "#4CC38A" },
    { label: "Catalog on sale", you: "6%", them: "31%", verdict: "Ahead — full-price brand", color: "#4CC38A" },
    { label: "Launches · 30d", you: "2", them: "9", verdict: "Behind — ship faster", color: "#F2555A" },
  ];
  return (
    <div className="rounded-md overflow-hidden shadow-2xl" style={{ background: "#0B0C0A", border: "1px solid #262A22" }}>
      <div className="px-4 py-3 border-b flex items-center gap-2" style={{ background: "#101110", borderColor: "#262A22" }}>
        <Target className="w-3.5 h-3.5" style={{ color: "#A8AC9E" }} />
        <span className="text-xs font-semibold" style={{ color: "#ECEEE6" }}>Your store vs gymshark.com</span>
      </div>
      <div className="p-4 space-y-2">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center gap-3 px-3 py-2.5 rounded-md" style={{ background: "#161814", border: "1px solid #262A22" }}>
            <p className="text-[11px] w-28 shrink-0" style={{ color: "#6C7164" }}>{r.label}</p>
            <p className="text-xs font-mono font-bold" style={{ color: "#ECEEE6" }}>{r.you}</p>
            <p className="text-[10px]" style={{ color: "#6C7164" }}>vs {r.them}</p>
            <span className="text-[10px] font-semibold ml-auto shrink-0" style={{ color: r.color }}>{r.verdict}</span>
          </div>
        ))}
        <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-md" style={{ background: "rgba(255,178,36,.05)", border: "1px solid rgba(255,178,36,.2)" }}>
          <Zap className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: "#FFB224" }} />
          <p className="text-[11px] leading-relaxed" style={{ color: "#ECEEE6" }}>
            <span className="font-bold" style={{ color: "#FFB224" }}>YOUR MOVE · </span>
            You own the premium lane. Close the launch gap with one new product this month.
          </p>
        </div>
      </div>
    </div>
  );
}

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
            style={{ background: "var(--accent)" }}
          >
            <Zap className="w-4 h-4" style={{ color: "var(--ink)" }} />
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
            className="text-sm font-semibold px-4 py-2 rounded-md transition-all hover:brightness-110"
            style={{ background: "#FFB224", color: "var(--ink)" }}
          >
            Start free
          </Link>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pt-20 pb-14 text-center">
        <div
          className="label-caps inline-flex items-center gap-2 px-3 py-1.5 rounded mb-8"
          style={{ background: "rgba(255,178,36,.08)", color: "#FFB224", border: "1px solid rgba(255,178,36,.2)" }}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
          Live competitor intelligence for Shopify
        </div>

        <h1
          className="text-4xl md:text-6xl font-bold tracking-tight mb-6"
          style={{ color: "var(--text)", letterSpacing: "-0.04em", lineHeight: 1.05 }}
        >
          Your Shopify competitors<br />
          are making moves<br />
          <span style={{ color: "#FFB224" }}>right now.</span>
        </h1>

        <p className="text-lg md:text-xl mb-8 max-w-2xl mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
          StoreScout scans your competitors every day, detects the moves that matter — price cuts, launches, flash sales — and delivers them in one Daily Intelligence Brief, with an instant alert the moment a critical move is detected.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-6">
          <Link
            href="/auth/signup"
            className="flex items-center gap-2 font-bold px-8 py-4 rounded-md text-lg transition-all hover:opacity-90"
            style={{ background: "#FFB224", color: "var(--ink)" }}
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

        <p className="text-sm mb-12" style={{ color: "var(--muted)", opacity: 0.6 }}>
          No credit card required · Free forever · First scan ready in 60 seconds
        </p>

        {/* The transformation, not the interface */}
        <HeroScan />
      </div>

      {/* ── Stats strip ─────────────────────────────────────────────────────── */}
      <div className="border-y" style={{ borderColor: "var(--border)" }}>
        <div className="max-w-5xl mx-auto px-6 py-6 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { value: "Daily", label: "Auto-scans on Pro" },
            { value: "1M+", label: "Shopify stores supported" },
            { value: "100%", label: "Public data — no ToS issues" },
            { value: "$0", label: "To get started" },
          ].map(({ value, label }) => (
            <div key={label}>
              <p className="text-2xl font-bold mb-0.5" style={{ color: "var(--text)" }}>{value}</p>
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

      {/* ── 01 · Discover ───────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>01 · Discover</p>
            <h2 className="text-3xl font-bold mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
              Find the competitors you didn&apos;t know you had.
            </h2>
            <p className="text-base leading-relaxed mb-6" style={{ color: "var(--muted)" }}>
              Describe what you sell — StoreScout maps your competitive landscape, verifies which rivals run
              scannable Shopify storefronts, and tells you honestly which ones it can&apos;t watch yet. No guessing,
              no dead links.
            </p>
            <ul className="space-y-3">
              {[
                "AI maps the brands your customers actually compare",
                "Every result verified as a real, trackable Shopify store",
                "Peers your size first — not just the giants",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm" style={{ color: "var(--muted)" }}>
                  <Check className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "#FFB224" }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <DiscoveryMock />
        </div>
      </div>

      {/* ── Real dashboard screenshot ────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-10">
          <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>02 · Analyze</p>
          <h2 className="text-2xl font-bold mb-2" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Full pricing intelligence — not just prices
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            See how prices are distributed, how deep discounts go, and how the catalog has changed — from a single dashboard.
          </p>
        </div>
        <BrowserChrome url="app.storescout.com/dashboard/gymshark">
          <PricingDashboardMock />
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
              style={{ background: "rgba(255,178,36,.1)", color: "#FFB224", border: "1px solid rgba(255,178,36,.2)" }}
            >
              <Target className="w-3 h-3" />
              Strategic positioning analysis
            </div>
            <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>02 · Analyze</p>
            <h2 className="text-3xl font-bold mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
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
                  <Check className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "#FFB224" }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <BrowserChrome url="app.storescout.com/dashboard/gymshark">
            <PositioningMock />
          </BrowserChrome>
        </div>
      </div>

      {/* ── "This is happening right now" — FOMO section ────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-10">
          <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>03 · Monitor</p>
          <div
            className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-5"
            style={{ background: "rgba(242,85,90,.1)", color: "#F2555A", border: "1px solid rgba(242,85,90,.2)" }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
            Detected in the last 3 hours
          </div>
          <h2 className="text-3xl md:text-4xl font-bold mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Here&apos;s what you&apos;re<br />
            <span style={{ color: "#F2555A" }}>missing right now.</span>
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
            Without StoreScout, you find out about moves like these <span style={{ color: "#F2555A" }}>days later</span> — after Reddit, after their customers have already bought.
          </p>
          <Link
            href="/auth/signup"
            className="inline-flex items-center gap-2 font-bold px-6 py-3 rounded-md transition-all hover:opacity-90"
            style={{ background: "#FFB224", color: "var(--ink)" }}
          >
            Start monitoring for free
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* ── Alert email section ──────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div
              className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-5"
              style={{ background: "rgba(242,85,90,.1)", color: "#F2555A", border: "1px solid rgba(242,85,90,.2)" }}
            >
              <Bell className="w-3 h-3" />
              Critical moves alert you instantly
            </div>
            <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>03 · Monitor</p>
            <h2 className="text-3xl font-bold mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
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
                  <Check className="w-4 h-4 shrink-0" style={{ color: "#FFB224" }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <AlertEmailPreview />
        </div>
      </div>

      {/* ── Intelligence Brief section ───────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-10">
          <div
            className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-5"
            style={{ background: "rgba(255,178,36,.1)", color: "#FFB224", border: "1px solid rgba(255,178,36,.2)" }}
          >
            <Sparkles className="w-3 h-3" />
            AI-powered weekly brief
          </div>
          <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>04 · Act</p>
          <h2 className="text-3xl font-bold mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Your AI strategist, already looking at the data.
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            Every week, Claude analyzes 7 days of scan data and writes a 4-card brief: what changed, what it signals, where your opening is, and exactly what to do. Not summaries — actionable moves.
          </p>
        </div>
        <IntelligenceBriefPreview />
      </div>

      {/* ── 05 · Win ────────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div className="md:order-2">
            <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>05 · Win</p>
            <h2 className="text-3xl font-bold mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
              Stop guessing where you stand.
            </h2>
            <p className="text-base leading-relaxed mb-6" style={{ color: "var(--muted)" }}>
              Connect your own store and every insight becomes personal: where you&apos;re ahead, where you&apos;re
              exposed, and the one move that changes the picture. Not another report — a position.
            </p>
            <ul className="space-y-3">
              {[
                "Side-by-side pricing, catalog, and promo comparison",
                "Recommendations reference YOUR products and inventory",
                "Every insight can become a saved Playbook task with evidence",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm" style={{ color: "var(--muted)" }}>
                  <Check className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "#FFB224" }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="md:order-1">
            <WinCompareMock />
          </div>
        </div>
      </div>

      {/* ── Screenshot showcase grid ─────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="text-center mb-12">
          <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>Coverage</p>
          <h2 className="text-3xl font-bold mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Every angle covered
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            Launch timelines, discount depth, top products, pricing patterns — everything a Shopify operator needs to make better decisions, faster.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Launch timeline */}
          <div className="rounded-md overflow-hidden" style={{ border: "1px solid #262A22" }}>
            <div className="px-4 py-3 border-b flex items-center gap-2" style={{ background: "#101110", borderColor: "#262A22" }}>
              <Rocket className="w-3.5 h-3.5" style={{ color: "#FFB224" }} />
              <span className="text-xs font-semibold" style={{ color: "#ECEEE6" }}>Launch Velocity</span>
              <span className="text-[10px] ml-auto" style={{ color: "#6C7164" }}>gymshark.com</span>
            </div>
            <LaunchVelocityMock />
          </div>

          {/* Top products */}
          <div className="rounded-md overflow-hidden" style={{ border: "1px solid #262A22" }}>
            <div className="px-4 py-3 border-b flex items-center gap-2" style={{ background: "#101110", borderColor: "#262A22" }}>
              <TrendingUp className="w-3.5 h-3.5" style={{ color: "#FFB224" }} />
              <span className="text-xs font-semibold" style={{ color: "#ECEEE6" }}>Winning Products</span>
              <span className="text-[10px] ml-auto" style={{ color: "#6C7164" }}>gymshark.com</span>
            </div>
            <WinningProductsMock />
          </div>

          {/* Pricing & discounts */}
          <div className="rounded-md overflow-hidden md:col-span-2" style={{ border: "1px solid #262A22" }}>
            <div className="px-4 py-3 border-b flex items-center gap-2" style={{ background: "#101110", borderColor: "#262A22" }}>
              <Tag className="w-3.5 h-3.5" style={{ color: "#FFB224" }} />
              <span className="text-xs font-semibold" style={{ color: "#ECEEE6" }}>Pricing &amp; Discount Analysis</span>
              <span className="text-[10px] ml-auto" style={{ color: "#6C7164" }}>gymshark.com · 90-day view</span>
            </div>
            <PricingDiscountMock />
          </div>
        </div>
      </div>

      {/* ── How it works ────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28" id="how-it-works">
        <div className="text-center mb-14">
          <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>How it works</p>
          <h2 className="text-3xl font-bold mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Live in 60 seconds
          </h2>
          <p className="text-base" style={{ color: "var(--muted)" }}>No setup, no API keys, no spreadsheets.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-8 relative">
          <div className="hidden md:block absolute top-6 left-[calc(16.67%+24px)] right-[calc(16.67%+24px)] h-px"
            style={{ background: "linear-gradient(90deg, transparent, rgba(255,178,36,.3), transparent)" }} />
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
              desc: "Critical moves — flash sales, steep price cuts — alert you the moment they're detected. Everything else lands in your Daily Intelligence Brief. Scans run every day.",
            },
          ].map(({ step, icon: Icon, title, desc }) => (
            <div key={step} className="text-center relative">
              <div
                className="w-12 h-12 rounded-md flex items-center justify-center mx-auto mb-4 relative z-10"
                style={{ background: "rgba(255,178,36,.1)", border: "1px solid rgba(255,178,36,.2)" }}
              >
                <Icon className="w-5 h-5" style={{ color: "#FFB224" }} />
              </div>
              <div className="text-[10px] font-bold uppercase tracking-widest mb-2" style={{ color: "rgba(255,178,36,.4)" }}>
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
          <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>Who it&apos;s for</p>
          <h2 className="text-3xl font-bold mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Built for two types of operators
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            Whether you run one brand or manage 50 clients, StoreScout adapts to your workflow.
          </p>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="rounded-md p-7" style={{ background: "rgba(255,178,36,.04)", border: "1px solid rgba(255,178,36,.15)" }}>
            <div className="w-10 h-10 rounded-md flex items-center justify-center mb-5" style={{ background: "rgba(255,178,36,.12)" }}>
              <Store className="w-5 h-5" style={{ color: "#FFB224" }} />
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
                  <Check className="w-3.5 h-3.5 shrink-0" style={{ color: "#FFB224" }} />
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-md p-7" style={{ background: "rgba(255,178,36,.04)", border: "1px solid rgba(255,178,36,.15)" }}>
            <div className="w-10 h-10 rounded-md flex items-center justify-center mb-5" style={{ background: "rgba(255,178,36,.12)" }}>
              <Users className="w-5 h-5" style={{ color: "#FFB224" }} />
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
                  <Check className="w-3.5 h-3.5 shrink-0" style={{ color: "#FFB224" }} />
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
          <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>Why StoreScout</p>
          <h2 className="text-3xl font-bold mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Everything in one place
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            Built for Shopify operators who make pricing and product decisions every week — and can&apos;t afford Similarweb.
          </p>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div
            className="rounded-md p-7 flex flex-col justify-between md:row-span-2"
            style={{ background: "rgba(255,178,36,.04)", border: "1px solid rgba(255,178,36,.15)" }}
          >
            <div>
              <div className="w-10 h-10 rounded-md flex items-center justify-center mb-5" style={{ background: "rgba(255,178,36,.12)" }}>
                <Bell className="w-5 h-5" style={{ color: "#FFB224" }} />
              </div>
              <h3 className="text-lg font-bold mb-3" style={{ color: "var(--text)" }}>
                Flash sale detection in minutes
              </h3>
              <p className="text-sm leading-relaxed mb-5" style={{ color: "var(--muted)" }}>
                When a competitor drops 20+ prices in one session, StoreScout flags it as a critical &ldquo;Flash Sale&rdquo; event and alerts you immediately — before it shows up on social.
              </p>
            </div>
            <div className="rounded-md p-4" style={{ background: "rgba(0,0,0,.3)", border: "1px solid rgba(242,85,90,.2)" }}>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                  style={{ background: "rgba(242,85,90,.15)", color: "#F2555A" }}>⚡ Flash sale</span>
                <span className="text-xs" style={{ color: "#A8AC9E" }}>gymshark.com · just now</span>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: "#A8AC9E" }}>
                7 products dropped ≥20% — avg −24.6%. Summer clearance or aggressive acquisition push.
              </p>
            </div>
          </div>
          {[
            { icon: TrendingDown, title: "Know when they raise or lower prices", desc: "90 days of price history per competitor. Spot seasonal patterns and predict the next sale before it happens." },
            { icon: Sparkles, title: "AI weekly digest", desc: "Every Monday, Claude writes a 4-card brief on what changed, what it signals, and exactly what to do about it." },
            { icon: Rocket, title: "Catch every launch — and what it signals", desc: "How many products are they shipping per month? Are they accelerating into a new category or pulling back?" },
            { icon: Tag, title: "Never miss a sale event again", desc: "What % of their catalog is on sale, how deep the discounts go, and when each event starts and ends." },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="rounded-md p-6" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <div className="w-10 h-10 rounded-md flex items-center justify-center mb-4" style={{ background: "rgba(255,178,36,.1)" }}>
                <Icon className="w-5 h-5" style={{ color: "#FFB224" }} />
              </div>
              <h3 className="font-bold mb-2" style={{ color: "var(--text)" }}>{title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Testimonials (live opt-in reviews; hidden until real ones exist) ── */}
      <Testimonials />

      {/* ── Comparison ──────────────────────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto px-6 pb-28">
        <div className="text-center mb-12">
          <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>Why StoreScout</p>
          <h2 className="text-3xl font-bold mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Why not a Chrome extension?
          </h2>
          <p className="text-base max-w-xl mx-auto" style={{ color: "var(--muted)" }}>
            Extensions only work while you&apos;re browsing. Reports are a one-time snapshot. StoreScout monitors continuously — whether you&apos;re logged in or not.
          </p>
        </div>
        <div className="rounded-md p-6 md:p-8" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <ComparisonTable />
        </div>
      </div>

      {/* ── Trust signals ───────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 pb-28">
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { icon: Shield, label: "Public data only", desc: "Reads Shopify's public product endpoints — no login required, no private data touched, no ToS issues." },
            { icon: Clock, label: "Daily auto-scans", desc: "Pro and Agency plans scan automatically every 24 hours. Set it and never manually check again." },
            { icon: Zap, label: "Instant critical alerts", desc: "Critical moves alert you the moment a scan detects them — daily scans, immediate alerts on what matters." },
          ].map(({ icon: Icon, label, desc }) => (
            <div key={label} className="flex items-start gap-4 rounded-md p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <div className="rounded-md p-2 shrink-0" style={{ background: "rgba(255,178,36,.1)" }}>
                <Icon className="w-4 h-4" style={{ color: "#FFB224" }} />
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
          <p className="label-caps mb-3" style={{ color: "var(--accent)" }}>Pricing</p>
          <h2 className="text-3xl font-bold mb-3" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
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
              className="rounded-md p-6 flex flex-col relative"
              style={{
                background: highlight ? "rgba(255,178,36,.05)" : "var(--bg-card)",
                border: `1px solid ${highlight ? "rgba(255,178,36,.3)" : "var(--border)"}`,
              }}
            >
              {highlight && (
                <div
                  className="absolute -top-3 left-1/2 -translate-x-1/2 text-xs font-bold uppercase tracking-wide px-3 py-1 rounded-full"
                  style={{ background: "#FFB224", color: "var(--ink)" }}
                >
                  Most popular
                </div>
              )}
              <h3 className="font-bold text-lg mb-1" style={{ color: "var(--text)" }}>{name}</h3>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-3xl font-bold" style={{ color: highlight ? "#FFB224" : "var(--text)" }}>{price}</span>
                <span className="text-sm" style={{ color: "var(--muted)" }}>{sub}</span>
              </div>
              {annualNote && (
                <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>{annualNote}</p>
              )}
              {!annualNote && <div className="mb-5" />}
              <ul className="space-y-2.5 mb-6 flex-1">
                {features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm" style={{ color: "var(--muted)" }}>
                    <Check className="w-4 h-4 shrink-0" style={{ color: highlight ? "#FFB224" : "var(--muted)" }} />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href={href}
                className="block text-center font-semibold py-3 rounded-md transition-all hover:brightness-110"
                style={highlight
                  ? { background: "#FFB224", color: "var(--ink)" }
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
        <h2 className="text-3xl font-bold mb-10 text-center" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
          Common questions
        </h2>
        <FaqAccordion />
      </div>

      {/* ── Final CTA ───────────────────────────────────────────────────────── */}
      <div className="max-w-3xl mx-auto px-6 pb-28 text-center">
        <div
          className="rounded-3xl p-12"
          style={{ background: "rgba(255,178,36,.05)", border: "1px solid rgba(255,178,36,.2)" }}
        >
          <div>
            <h2 className="text-3xl md:text-4xl font-bold mb-4" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
              Your competitors are already moving.<br />
              <span style={{ color: "#FFB224" }}>Now you will be too.</span>
            </h2>
            <p className="mb-8 text-lg" style={{ color: "var(--muted)" }}>
              Free forever. No credit card. First scan ready in under 60 seconds.
            </p>
            <Link
              href="/auth/signup"
              className="inline-flex items-center gap-2 font-bold px-8 py-4 rounded-md text-lg transition-all hover:opacity-90"
              style={{ background: "#FFB224", color: "var(--ink)" }}
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
              <Zap className="w-3.5 h-3.5" style={{ color: "var(--ink)" }} />
            </div>
            <span className="font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="#how-it-works" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>How it works</Link>
            <Link href="#pricing" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>Pricing</Link>
            <Link href="#faq" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>FAQ</Link>
            <Link href="/privacy" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>Privacy</Link>
            <Link href="/terms" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>Terms</Link>
            <Link href="/auth/login" className="text-sm hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>Sign in</Link>
          </div>
          <p className="text-xs" style={{ color: "var(--muted)" }}>© 2026 StoreScout</p>
        </div>
      </footer>

    </div>
  );
}
