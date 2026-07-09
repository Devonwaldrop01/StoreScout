"use client";

/**
 * Shared shell for every /admin page. Renders one persistent nav bar so the
 * operator can always move between Home / Index / Leads (and sign out) without
 * hand-editing the URL — the fix for the old "I can't get back to the main
 * admin page" trap where each page owned its own disconnected navigation.
 *
 * The bar only appears once an admin token is stored, so the token-gate
 * screens stay clean. Pages dispatch `ss-admin-auth` after login/logout so the
 * bar appears/disappears immediately, same-tab.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sunrise, Database, Crosshair, LogOut } from "lucide-react";

const TOKEN_KEY = "ss_admin_token";

const NAV = [
  { href: "/admin", label: "Brief", icon: Sunrise, exact: true },
  { href: "/admin/store-index", label: "Index", icon: Database, exact: false },
  { href: "/admin/leads", label: "Leads", icon: Crosshair, exact: false },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    const check = () => {
      try { setHasToken(!!localStorage.getItem(TOKEN_KEY)); } catch { setHasToken(false); }
    };
    check();
    window.addEventListener("ss-admin-auth", check);
    window.addEventListener("storage", check);
    return () => {
      window.removeEventListener("ss-admin-auth", check);
      window.removeEventListener("storage", check);
    };
  }, [pathname]);

  function signOut() {
    try { localStorage.removeItem(TOKEN_KEY); } catch { /* ignore */ }
    window.dispatchEvent(new Event("ss-admin-auth"));
    // Pages read the same key on mount / focus, so a hard reload guarantees
    // every page drops back to its token gate.
    window.location.href = "/admin";
  }

  return (
    <div style={{ background: "var(--bg)", minHeight: "100vh" }}>
      {hasToken && (
        <nav
          className="sticky top-0 z-40 flex items-center gap-1 px-4 sm:px-6 h-12 backdrop-blur"
          style={{ background: "color-mix(in srgb, var(--bg) 88%, transparent)", borderBottom: "1px solid var(--border)" }}
        >
          <span className="text-[11px] font-bold tracking-tight mr-3 hidden sm:block" style={{ color: "var(--text)" }}>
            StoreScout <span style={{ color: "var(--muted)" }}>OS</span>
          </span>
          {NAV.map((n) => {
            const active = n.exact ? pathname === n.href : pathname.startsWith(n.href);
            const Icon = n.icon;
            return (
              <Link
                key={n.href}
                href={n.href}
                className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-all"
                style={{
                  background: active ? "var(--bg-card)" : "transparent",
                  border: `1px solid ${active ? "var(--border)" : "transparent"}`,
                  color: active ? "var(--text)" : "var(--muted)",
                }}
              >
                <Icon className="w-3.5 h-3.5" style={active ? { color: "var(--accent)" } : undefined} />
                {n.label}
              </Link>
            );
          })}
          <button
            onClick={signOut}
            className="ml-auto flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-all hover:bg-white/[0.06]"
            style={{ color: "var(--muted)" }}
          >
            <LogOut className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Sign out</span>
          </button>
        </nav>
      )}
      {children}
    </div>
  );
}
