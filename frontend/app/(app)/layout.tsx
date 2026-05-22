"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, Bell, Settings, LogOut, Plus, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";
import { alerts } from "@/lib/api";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    alerts.unreadCount().then((r) => setUnread(r.count)).catch(() => {});
  }, [pathname]);

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/");
  }

  const nav = [
    { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { href: "/alerts", icon: Bell, label: "Alerts", badge: unread },
    { href: "/settings", icon: Settings, label: "Settings" },
  ];

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className="hidden md:flex flex-col w-56 shrink-0 border-r"
        style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-2 px-5 py-5">
          <Zap className="w-5 h-5" style={{ color: "var(--green)" }} />
          <span className="font-bold text-lg tracking-tight" style={{ color: "var(--text)" }}>
            StoreScout
          </span>
        </div>

        <nav className="flex-1 px-3 space-y-1">
          {nav.map(({ href, icon: Icon, label, badge }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                pathname.startsWith(href)
                  ? "text-white"
                  : "hover:bg-white/5"
              )}
              style={
                pathname.startsWith(href)
                  ? { background: "rgba(163,240,0,.12)", color: "var(--green)" }
                  : { color: "var(--muted)" }
              }
            >
              <Icon className="w-4 h-4" />
              {label}
              {badge != null && badge > 0 && (
                <span
                  className="ml-auto text-xs font-bold px-1.5 py-0.5 rounded-full"
                  style={{ background: "var(--green)", color: "#060d18" }}
                >
                  {badge}
                </span>
              )}
            </Link>
          ))}
        </nav>

        <div className="p-3 border-t" style={{ borderColor: "var(--border)" }}>
          <button
            onClick={handleSignOut}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm font-medium transition-colors hover:bg-white/5"
            style={{ color: "var(--muted)" }}
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto" style={{ background: "var(--bg)" }}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">{children}</div>
      </main>

      {/* Mobile bottom nav */}
      <nav
        className="fixed bottom-0 left-0 right-0 md:hidden flex border-t z-50"
        style={{ background: "var(--bg2)", borderColor: "var(--border)" }}
      >
        {nav.map(({ href, icon: Icon, label, badge }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex-1 flex flex-col items-center gap-1 py-3 text-xs font-medium relative",
              pathname.startsWith(href) ? "" : ""
            )}
            style={{ color: pathname.startsWith(href) ? "var(--green)" : "var(--muted)" }}
          >
            <Icon className="w-5 h-5" />
            {label}
            {badge != null && badge > 0 && (
              <span
                className="absolute top-2 right-1/4 translate-x-1/2 text-xs font-bold w-4 h-4 flex items-center justify-center rounded-full text-[10px]"
                style={{ background: "var(--green)", color: "#060d18" }}
              >
                {badge > 9 ? "9+" : badge}
              </span>
            )}
          </Link>
        ))}
      </nav>
    </div>
  );
}
