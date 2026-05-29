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

// ── Brand Logo ────────────────────────────────────────────────────────────

function StoreLogo({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M30 35L30 80C30 85 32 88 37 88L63 88C68 88 70 85 70 80L70 35" stroke="#2463EB" strokeWidth="6" strokeLinecap="round" fill="none"/>
      <path d="M25 35L75 35L72 42L28 42Z" fill="#2463EB"/>
      <path d="M38 35L38 28C38 22 42 18 50 18C58 18 62 22 62 28L62 35" stroke="#2463EB" strokeWidth="6" strokeLinecap="round" fill="none"/>
      <circle cx="65" cy="55" r="18" fill="#1E40AF" opacity="0.9"/>
      <circle cx="65" cy="55" r="12" fill="white" opacity="0.25"/>
      <path d="M78 68L88 78" stroke="#1E40AF" strokeWidth="5" strokeLinecap="round"/>
    </svg>
  );
}

// ── Layout ────────────────────────────────────────────────────────────────

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

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/");
  }

  const nav = [
    { href: "/dashboard",   icon: LayoutDashboard, label: "Dashboard"   },
    { href: "/competitors", icon: Target,          label: "Competitors" },
    { href: "/playbook",    icon: BookOpen,        label: "Playbook"    },
    { href: "/alerts",      icon: Bell,            label: "Alerts",     badge: unread },
  ];

  const isFree = tier === "free" || tier === null;

  function isActive(href: string) {
    if (href === "/dashboard")   return pathname === "/dashboard" || pathname.startsWith("/dashboard/");
    if (href === "/competitors") return pathname === "/competitors";
    if (href === "/playbook")    return pathname === "/playbook";
    return pathname.startsWith(href);
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg)" }}>

      {/* ── Sidebar (desktop) ─────────────────────────────────────────────── */}
      <aside
        className="hidden md:flex flex-col w-[212px] shrink-0 border-r"
        style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
      >

        {/* ── Logo ── */}
        <div className="px-4 pt-5 pb-4">
          <Link href="/dashboard" className="flex items-center gap-2.5 group">
            <StoreLogo size={20} />
            <span
              className="font-bold text-[15px] tracking-tight transition-colors"
              style={{ color: "var(--text)" }}
            >
              StoreScout
            </span>
          </Link>
        </div>

        {/* ── Nav ── */}
        <nav className="flex-1 px-2 space-y-0.5 overflow-y-auto">
          {nav.map(({ href, icon: Icon, label, badge }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                className="relative flex items-center gap-2.5 px-3 py-[9px] rounded-md text-sm font-medium transition-colors"
                style={{
                  color: active ? "var(--text)" : "var(--muted)",
                  background: active ? "rgba(255,255,255,.05)" : "transparent",
                }}
                onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "rgba(255,255,255,.03)"; }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
              >
                {active && (
                  <span
                    className="absolute left-0 inset-y-2 w-[2px] rounded-full"
                    style={{ background: "var(--accent)" }}
                  />
                )}
                <Icon className="w-[15px] h-[15px] shrink-0" />
                <span className="flex-1">{label}</span>
                {badge != null && badge > 0 && (
                  <span
                    className="text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center tabular-nums"
                    style={{ background: "rgba(59,130,246,.18)", color: "var(--accent)" }}
                  >
                    {badge > 9 ? "9+" : badge}
                  </span>
                )}
              </Link>
            );
          })}

          {/* Divider */}
          <div className="pt-3 pb-1">
            <div className="h-px mx-2" style={{ background: "var(--border)" }} />
          </div>

          {/* Settings */}
          {(() => {
            const active = pathname === "/settings" || pathname.startsWith("/settings");
            return (
              <Link
                href="/settings"
                className="relative flex items-center gap-2.5 px-3 py-[9px] rounded-md text-sm font-medium transition-colors"
                style={{
                  color: active ? "var(--text)" : "var(--muted)",
                  background: active ? "rgba(255,255,255,.05)" : "transparent",
                }}
                onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "rgba(255,255,255,.03)"; }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
              >
                {active && (
                  <span
                    className="absolute left-0 inset-y-2 w-[2px] rounded-full"
                    style={{ background: "var(--accent)" }}
                  />
                )}
                <Settings className="w-[15px] h-[15px] shrink-0" />
                Settings
              </Link>
            );
          })()}
        </nav>

        {/* ── Bottom ── */}
        <div className="p-3 space-y-1.5" style={{ borderTop: "1px solid var(--border)" }}>
          {/* Upgrade CTA — free users only */}
          {isFree && (
            <Link
              href="/settings?upgrade=1"
              className="flex items-center gap-2 w-full px-3 py-2 rounded-md text-xs font-semibold transition-colors"
              style={{
                background: "rgba(59,130,246,.1)",
                color: "var(--accent)",
                border: "1px solid rgba(59,130,246,.18)",
              }}
            >
              <Zap className="w-3.5 h-3.5 shrink-0" />
              <span className="flex-1">Upgrade to Pro</span>
              <ChevronRight className="w-3 h-3 opacity-50" />
            </Link>
          )}

          <button
            onClick={handleSignOut}
            className="flex items-center gap-2.5 w-full px-3 py-2 rounded-md text-sm font-medium transition-colors"
            style={{ color: "var(--muted)" }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(255,255,255,.03)"; e.currentTarget.style.color = "var(--text-2)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--muted)"; }}
          >
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
          background: "rgba(10,10,15,0.96)",
          borderColor: "var(--border)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
        }}
      >
        {[...nav, { href: "/settings", icon: Settings, label: "Settings", badge: undefined }].map(({ href, icon: Icon, label, badge }) => {
          const active = isActive(href);
          return (
            <Link
              key={href + label}
              href={href}
              className="flex-1 flex flex-col items-center gap-1 py-3 transition-colors"
              style={{ color: active ? "var(--accent)" : "var(--muted)" }}
            >
              <Icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{label}</span>
              {badge != null && badge > 0 && (
                <span
                  className="absolute top-2 translate-x-2 text-[9px] font-bold w-3.5 h-3.5 flex items-center justify-center rounded-full"
                  style={{ background: "var(--accent)", color: "#fff" }}
                >
                  {badge > 9 ? "9+" : badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
