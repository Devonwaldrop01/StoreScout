import Link from "next/link";
import { Zap, TrendingUp, Bell, Cpu, ArrowRight } from "lucide-react";

export default function LandingPage() {
  const features = [
    {
      icon: TrendingUp,
      title: "Live competitor tracking",
      desc: "See exactly what any Shopify store is selling, how they price it, and when they launch new products.",
    },
    {
      icon: Bell,
      title: "Instant change alerts",
      desc: "Get emailed the moment a competitor changes prices, starts a sale, or launches new products.",
    },
    {
      icon: Cpu,
      title: "AI weekly digest",
      desc: "Every Monday, Claude analyzes your competitor data and sends you a strategic summary of what changed.",
    },
  ];

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 md:px-12 py-5 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5" style={{ color: "#a3f000" }} />
          <span className="font-bold text-lg" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/auth/login" className="text-sm font-medium hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>
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
      <div className="max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
        <div
          className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-8"
          style={{ background: "rgba(163,240,0,.1)", color: "#a3f000", border: "1px solid rgba(163,240,0,.2)" }}
        >
          <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
          Live competitor intelligence
        </div>
        <h1
          className="text-4xl md:text-6xl font-black tracking-tight mb-6"
          style={{ color: "var(--text)", letterSpacing: "-0.04em" }}
        >
          Always know what your<br />
          <span style={{ color: "#a3f000" }}>Shopify competitors</span><br />
          are doing.
        </h1>
        <p className="text-lg md:text-xl mb-10 max-w-2xl mx-auto" style={{ color: "var(--muted)" }}>
          Track prices, launches, and discounts across any Shopify store. Get alerted the moment they make a move — automatically.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/auth/signup"
            className="flex items-center gap-2 font-bold px-8 py-4 rounded-2xl text-lg transition-all hover:brightness-110"
            style={{ background: "#a3f000", color: "#060d18" }}
          >
            Start tracking free
            <ArrowRight className="w-5 h-5" />
          </Link>
          <p className="text-sm" style={{ color: "var(--muted)" }}>No credit card · Free forever</p>
        </div>
      </div>

      {/* Features */}
      <div className="max-w-5xl mx-auto px-6 pb-24">
        <div className="grid md:grid-cols-3 gap-6">
          {features.map(({ icon: Icon, title, desc }) => (
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

        {/* Pricing */}
        <div className="mt-16 text-center">
          <h2 className="text-3xl font-black mb-2" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            Simple pricing
          </h2>
          <p className="mb-10" style={{ color: "var(--muted)" }}>Start free. Upgrade when you need more.</p>
          <div className="grid md:grid-cols-3 gap-6 max-w-3xl mx-auto">
            {[
              { name: "Free", price: "$0", desc: "1 competitor, weekly manual scan", cta: "Start free", href: "/auth/signup", highlight: false },
              { name: "Pro", price: "$29/mo", desc: "10 competitors, daily auto-scan, alerts, AI digest", cta: "Start Pro", href: "/auth/signup?plan=pro", highlight: true },
              { name: "Agency", price: "$79/mo", desc: "50 competitors, shareable reports, unlimited history", cta: "Start Agency", href: "/auth/signup?plan=agency", highlight: false },
            ].map(({ name, price, desc, cta, href, highlight }) => (
              <div
                key={name}
                className="rounded-2xl p-6 flex flex-col"
                style={{
                  background: highlight ? "rgba(163,240,0,.06)" : "var(--bg-card)",
                  border: `1px solid ${highlight ? "rgba(163,240,0,.3)" : "var(--border)"}`,
                }}
              >
                <h3 className="font-bold text-lg mb-1" style={{ color: "var(--text)" }}>{name}</h3>
                <p className="text-2xl font-black mb-3" style={{ color: highlight ? "#a3f000" : "var(--text)" }}>{price}</p>
                <p className="text-sm mb-5 flex-1" style={{ color: "var(--muted)" }}>{desc}</p>
                <Link
                  href={href}
                  className="block text-center font-semibold py-2.5 rounded-xl transition-all hover:brightness-110"
                  style={highlight ? { background: "#a3f000", color: "#060d18" } : { border: "1px solid var(--border)", color: "var(--text)" }}
                >
                  {cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
