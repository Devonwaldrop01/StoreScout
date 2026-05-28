"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, Bell, Settings, LogOut, Plus, Zap, Store, ChevronRight, BookOpen, Target } from "lucide-react";
import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";
import { alerts, user as userApi } from "@/lib/api";
import { FeedbackWidget } from "@/components/FeedbackWidget";
import { ErrorBoundary } from "@/components/ErrorBoundary";

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
        className="hidden md:flex flex-col w-52 shrink-0 border-r"
        style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
      >
        {/* Logo */}
        <div className="px-5 py-5 mb-1">
          <Link href="/dashboard" className="flex items-center gap-2.5 group">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-all group-hover:scale-110"
              style={{ background: "var(--accent)", boxShadow: "0 0 12px rgba(59,130,246,.35)" }}
            >
              <Zap className="w-4 h-4" style={{ color: "#ffffff" }} />
            </div>
            <span className="font-extrabold text-base tracking-tight" style={{ color: "var(--text)" }}>
              StoreScout
            </span>
          </Link>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 space-y-0.5">
          {nav.map(({ href, icon: Icon, label, badge }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all",
                  active ? "" : "hover:bg-white/[0.04]"
                )}
                style={{
                  color: active ? "var(--accent)" : "var(--muted)",
                  background: active ? "rgba(59,130,246,.07)" : undefined,
                }}
              >
                {/* Active left border */}
                {active && (
                  <span
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full"
                    style={{ background: "var(--accent)" }}
                  />
                )}
                <Icon className="w-4 h-4 shrink-0" />
                {label}
                {badge != null && badge > 0 && (
                  <span
                    className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center"
                    style={{ background: "var(--accent)", color: "#ffffff" }}
                  >
                    {badge > 9 ? "9+" : badge}
                  </span>
                )}
              </Link>
            );
          })}

          {/* Divider */}
          <div className="pt-2 pb-1">
            <div className="h-px mx-1" style={{ background: "var(--border)" }} />
          </div>

          <Link
            href="/settings"
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all",
              pathname === "/settings" ? "" : "hover:bg-white/[0.04]"
            )}
            style={{
              color: pathname === "/settings" ? "var(--accent)" : "var(--muted)",
              background: pathname === "/settings" ? "rgba(59,130,246,.07)" : undefined,
            }}
          >
            {pathname === "/settings" && (
              <span
                className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full"
                style={{ background: "var(--accent)" }}
              />
            )}
            <Settings className="w-4 h-4 shrink-0" />
            Settings
          </Link>
        </nav>

        {/* Bottom section */}
        <div className="p-3 space-y-2" style={{ borderTop: `1px solid var(--border)` }}>
          {/* Upgrade CTA — free users only */}
          {isFree && (
            <Link
              href="/settings?upgrade=1"
              className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl text-sm font-semibold transition-all hover:brightness-110"
              style={{ background: "rgba(59,130,246,.12)", color: "var(--accent)", border: "1px solid rgba(59,130,246,.2)" }}
            >
              <Zap className="w-4 h-4 shrink-0" />
              <span className="flex-1">Upgrade to Pro</span>
              <ChevronRight className="w-3.5 h-3.5 opacity-60" />
            </Link>
          )}

          <button
            onClick={handleSignOut}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-xl text-sm font-medium transition-all hover:bg-white/[0.04]"
            style={{ color: "var(--muted)" }}
          >
            <LogOut className="w-4 h-4 shrink-0" />
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto pb-20 md:pb-0" style={{ background: "var(--bg)" }}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
          <ErrorBoundary>{children}</ErrorBoundary>
        </div>
      </main>

      <FeedbackWidget />

      {/* ── Mobile bottom nav ─────────────────────────────────────────────── */}
      <nav
        className="fixed bottom-0 left-0 right-0 md:hidden flex border-t z-50 safe-area-pb"
        style={{ background: "rgba(13,13,21,0.95)", borderColor: "var(--border)", backdropFilter: "blur(16px)" }}
      >
        {[...nav, { href: "/settings", icon: Settings, label: "Settings", badge: undefined }].map(({ href, icon: Icon, label, badge }) => {
          const active = isActive(href);
          return (
            <Link
              key={href + label}
              href={href}
              className="flex-1 flex flex-col items-center gap-1 py-3 text-xs font-medium relative transition-colors"
              style={{ color: active ? "var(--accent)" : "var(--muted)" }}
            >
              <Icon className="w-5 h-5" />
              {label}
              {badge != null && badge > 0 && (
                <span
                  className="absolute top-2 right-1/4 translate-x-1/2 text-[10px] font-bold w-4 h-4 flex items-center justify-center rounded-full"
                  style={{ background: "var(--accent)", color: "#ffffff" }}
                >
                  {badge > 9 ? "9+" : badge}
                </span>
              )}
            </Link>
          );
        })}
        <button
          onClick={handleSignOut}
          className="flex-1 flex flex-col items-center gap-1 py-3 text-xs font-medium transition-colors"
          style={{ color: "var(--muted)" }}
        >
          <LogOut className="w-5 h-5" />
          Sign out
        </button>
      </nav>
    </div>
  );
}
