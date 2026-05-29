"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Zap, Eye, EyeOff, AlertCircle, CheckCircle2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export default function ResetPasswordPage() {
  const router = useRouter();
  const supabase = createClient();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [focusedField, setFocusedField] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords don't match");
      return;
    }
    setLoading(true);
    setError("");
    const { error: err } = await supabase.auth.updateUser({ password });
    if (err) {
      setError(err.message);
      setLoading(false);
    } else {
      setDone(true);
      setTimeout(() => router.push("/dashboard"), 2000);
    }
  }

  const inputStyle = (field: string) => ({
    background: "var(--bg3)",
    border: `1px solid ${focusedField === field ? "rgba(59,130,246,.4)" : "var(--border)"}`,
    color: "var(--text)",
    boxShadow: focusedField === field ? "0 0 0 3px rgba(59,130,246,.08)" : "none",
    outline: "none",
    transition: "border-color 0.15s, box-shadow 0.15s",
  });

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4" style={{ background: "var(--bg)" }}>
      {/* Ambient glows */}
      <div className="fixed pointer-events-none" style={{ top: "-80px", left: "-80px", width: "400px", height: "400px", borderRadius: "50%", background: "rgba(59,130,246,.06)", filter: "blur(80px)", zIndex: 0 }} />
      <div className="fixed pointer-events-none" style={{ top: "-60px", right: "-60px", width: "300px", height: "300px", borderRadius: "50%", background: "rgba(96,165,250,.04)", filter: "blur(80px)", zIndex: 0 }} />
      <div className="fixed pointer-events-none" style={{ bottom: "-80px", left: "50%", transform: "translateX(-50%)", width: "350px", height: "350px", borderRadius: "50%", background: "rgba(59,130,246,.04)", filter: "blur(80px)", zIndex: 0 }} />

      <div className="relative w-full max-w-sm" style={{ zIndex: 1 }}>
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div style={{ width: "32px", height: "32px", borderRadius: "12px", background: "var(--accent)", boxShadow: "0 0 20px rgba(59,130,246,.4)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <Zap style={{ width: "16px", height: "16px", color: "#ffffff" }} />
          </div>
          <span className="text-xl font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
        </div>

        {done ? (
          <div
            className="rounded-2xl p-10 text-center"
            style={{ background: "var(--bg2)", border: "1px solid var(--border)", boxShadow: "0 24px 80px rgba(0,0,0,.5)" }}
          >
            <div className="mx-auto mb-5 flex items-center justify-center" style={{ width: "56px", height: "56px", borderRadius: "50%", background: "rgba(59,130,246,.1)" }}>
              <CheckCircle2 style={{ width: "28px", height: "28px", color: "var(--accent)" }} />
            </div>
            <h2 className="text-xl font-bold mb-2" style={{ color: "var(--text)" }}>Password updated</h2>
            <p className="text-sm" style={{ color: "var(--muted)" }}>Taking you to your dashboard…</p>
          </div>
        ) : (
          <div className="rounded-2xl p-7" style={{ background: "var(--bg2)", border: "1px solid var(--border)", boxShadow: "0 24px 80px rgba(0,0,0,.5)" }}>
            <h1 className="text-xl font-bold mb-1 text-center" style={{ color: "var(--text)" }}>Set new password</h1>
            <p className="text-sm text-center mb-6" style={{ color: "var(--muted)" }}>Choose a strong password for your account.</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--muted)" }}>New password</label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                    autoFocus
                    placeholder="Min. 8 characters"
                    className="w-full px-4 py-3 pr-11 rounded-xl text-sm"
                    style={inputStyle("password")}
                    onFocus={() => setFocusedField("password")}
                    onBlur={() => setFocusedField(null)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded"
                    style={{ color: "var(--muted)" }}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1.5" style={{ color: "var(--muted)" }}>Confirm password</label>
                <div className="relative">
                  <input
                    type={showConfirm ? "text" : "password"}
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    required
                    minLength={8}
                    placeholder="Repeat password"
                    className="w-full px-4 py-3 pr-11 rounded-xl text-sm"
                    style={inputStyle("confirm")}
                    onFocus={() => setFocusedField("confirm")}
                    onBlur={() => setFocusedField(null)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded"
                    style={{ color: "var(--muted)" }}
                    tabIndex={-1}
                  >
                    {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm" style={{ background: "rgba(239,68,68,.1)", border: "1px solid rgba(239,68,68,.2)", color: "#f87171" }}>
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full font-semibold py-3 rounded-xl transition-all hover:brightness-110 disabled:opacity-50"
                style={{ background: "var(--accent)", color: "#ffffff" }}
              >
                {loading ? "Saving…" : "Set new password"}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
