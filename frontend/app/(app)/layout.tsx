"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, Bell, Settings, LogOut, BookOpen, Target, Zap, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";
import { alerts, user as userApi } from "@/lib/api";
import { FeedbackWidget } from "@/components/FeedbackWidget";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { requestFeedbackOnce } from "@/lib/feedbackPrompt";

// ── Brand mark — scope lens on charcoal, signal-amber ─────────────────────

function StoreLogo({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M30 35L30 80C30 85 32 88 37 88L63 88C68 88 70 85 70 80L70 35" stroke="#A8AC9E" strokeWidth="6" strokeLinecap="round" fill="none"/>
      <path d="M25 35L75 35L72 42L28 42Z" fill="#A8AC9E"/>
      <path d="M38 35L38 28C38 22 42 18 50 18C58 18 62 22 62 28L62 35" stroke="#A8AC9E" strokeWidth="6" strokeLinecap="round" fill="none"/>
      <circle cx="65" cy="55" r="18" fill="#FFB224" opacity="0.92"/>
      <circle cx="65" cy="55" r="12" fill="#0B0C0A" opacity="0.35"/>
      <path d="M78 68L88 78" stroke="#FFB224" strokeWidth="5" strokeLinecap="round"/>
    </svg>
  );
}

// ── Layout ────────────────────────────────────────────────────────────────

type NavItem = { href: string; icon: React.ElementType; label: string };

const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "Operate",
    items: [
      { href: "/dashboard",   icon: LayoutDashboard, label: "Dashboard" },
      { href: "/competitors", icon: Target,          label: "Competitors" },
    ],
  },
  {
    label: "Intel",
    items: [
      { href: "/playbook", icon: BookOpen, label: "Playbook" },
      { href: "/alerts",   icon: Bell,     label: "Signals" },
    ],
  },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();
  const [unread, setUnread] = useState(0);
  const [tier, setTier] = useState<string | null>(null);

  useEffect(() => {
    alerts.unreadCount().then((r) => setUnread(r.count)).catch(() => {});
    userApi.subscription().then((r) => setTier(r.data.tier)).catch(() => {});
  }, [pathname]);

  // Fallback feedback prompt: if a user keeps coming back but never finished the
  // checklist, ask once on their 3rd app session. Gated by requestFeedbackOnce.
  useEffect(() => {
    try {
      const n = parseInt(localStorage.getItem("ss_visits") || "0", 10) + 1;
      localStorage.setItem("ss_visits", String(n));
      if (n >= 3) requestFeedbackOnce();
    } catch { /* ignore */ }
  }, []);

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/");
  }

  const isFree = tier === "free" || tier === null;

  function isActive(href: string) {
    if (href === "/dashboard")   return pathname === "/dashboard" || pathname.startsWith("/dashboard/");
    if (href === "/competitors") return pathname === "/competitors";
    if (href === "/playbook")    return pathname === "/playbook";
    return pathname.startsWith(href);
  }

  const flatNav = NAV_GROUPS.flatMap((g) => g.items);

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg)" }}>

      {/* ── Instrument rail (desktop) ─────────────────────────────────────── */}
      <aside
        className="hidden md:flex flex-col w-[216px] shrink-0 border-r"
        style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
      >

        {/* Brand */}
        <div className="px-4 pt-5 pb-3">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <StoreLogo size={22} />
            <span className="font-bold text-[15px] tracking-tight" style={{ color: "var(--text)" }}>
              StoreScout
            </span>
          </Link>

          {/* Live status line — real signal state, not decoration */}
          <Link
            href="/alerts"
            className="mt-3 flex items-center gap-2 px-2 py-1.5 rounded"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <span className={cn("signal-dot", unread > 0 && "signal-dot--amber")} />
            <span className="label-caps" style={{ color: unread > 0 ? "var(--accent)" : "var(--muted)" }}>
              {unread > 0 ? `${unread > 9 ? "9+" : unread} new signal${unread === 1 ? "" : "s"}` : "monitoring"}
            </span>
          </Link>
        </div>

        {/* Nav groups */}
        <nav className="flex-1 px-2 overflow-y-auto">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="mb-4">
              <p className="label-caps px-3 pt-3 pb-1.5">{group.label}</p>
              <div className="space-y-0.5">
                {group.items.map(({ href, icon: Icon, label }) => {
                  const active = isActive(href);
                  const badge = href === "/alerts" ? unread : 0;
                  return (
                    <Link key={href} href={href} className={cn("rail-item", active && "rail-item--active")}>
                      <Icon className="w-[15px] h-[15px] shrink-0" />
                      <span className="flex-1">{label}</span>
                      {badge > 0 && (
                        <span
                          className="num text-[10px] font-bold px-1.5 py-0.5 rounded min-w-[18px] text-center"
                          style={{ background: "rgba(255,178,36,.14)", color: "var(--accent)" }}
                        >
                          {badge > 9 ? "9+" : badge}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}

          <hr className="rule mx-2 my-1" />

          <div className="pt-2">
            <Link
              href="/settings"
              className={cn("rail-item", (pathname === "/settings" || pathname.startsWith("/settings")) && "rail-item--active")}
            >
              <Settings className="w-[15px] h-[15px] shrink-0" />
              Settings
            </Link>
          </div>
        </nav>

        {/* Bottom: tier + upgrade + sign out */}
        <div className="p-3 space-y-1.5" style={{ borderTop: "1px solid var(--border)" }}>
          {tier && (
            <div className="flex items-center justify-between px-3 py-1">
              <span className="label-caps">Plan</span>
              <span
                className="label-caps"
                style={{ color: isFree ? "var(--muted)" : "var(--accent)" }}
              >
                {tier}
              </span>
            </div>
          )}

          {isFree && (
            <Link
              href="/settings?upgrade=1"
              className="flex items-center gap-2 w-full px-3 py-2 rounded text-xs font-semibold transition-colors"
              style={{
                background: "rgba(255,178,36,.10)",
                color: "var(--accent)",
                border: "1px solid rgba(255,178,36,.22)",
              }}
            >
              <Zap className="w-3.5 h-3.5 shrink-0" />
              <span className="flex-1">Upgrade to Pro</span>
              <ChevronRight className="w-3 h-3 opacity-50" />
            </Link>
          )}

          <button onClick={handleSignOut} className="rail-item w-full">
            <LogOut className="w-[15px] h-[15px] shrink-0" />
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden" style={{ background: "var(--bg)" }}>
        <div className="flex-1 overflow-y-auto pb-20 md:pb-0">
          <div className="max-w-7xl mx-auto px-5 sm:px-7 py-7">
            <ErrorBoundary>{children}</ErrorBoundary>
          </div>
        </div>
      </main>

      <FeedbackWidget />

      {/* ── Mobile bottom nav ─────────────────────────────────────────────── */}
      <nav
        className="fixed bottom-0 left-0 right-0 md:hidden flex border-t z-50"
        style={{
          background: "rgba(11,12,10,0.96)",
          borderColor: "var(--border)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
        }}
      >
        {[...flatNav, { href: "/settings", icon: Settings, label: "Settings" }].map(({ href, icon: Icon, label }) => {
          const active = isActive(href);
          const badge = href === "/alerts" ? unread : 0;
          return (
            <Link
              key={href + label}
              href={href}
              className="relative flex-1 flex flex-col items-center gap-1 py-3 transition-colors"
              style={{ color: active ? "var(--accent)" : "var(--muted)" }}
            >
              <Icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{label}</span>
              {badge > 0 && (
                <span
                  className="absolute top-2 translate-x-2 text-[9px] font-bold w-3.5 h-3.5 flex items-center justify-center rounded-full num"
                  style={{ background: "var(--accent)", color: "var(--ink)" }}
                >
                  {badge > 9 ? "9" : badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
