"use client";

/**
 * Runtime engine controls for the admin consoles — flip the daily workers on
 * and set their limits without a redeploy. Writes to /admin/config; the
 * workers pick changes up within ~15s. Env vars remain the defaults.
 */

import { useCallback, useEffect, useState } from "react";
import { Check, Loader2, Power } from "lucide-react";

export interface Knob {
  key: string;
  label: string;
  type: "toggle" | "number";
  help?: string;
  min?: number;
  max?: number;
}

async function cfgFetch<T>(token: string, init?: RequestInit): Promise<T> {
  const res = await fetch("/api/v1/admin/config", {
    ...init,
    headers: { "Content-Type": "application/json", "X-Admin-Token": token, ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export function EngineControls({ token, title, knobs }: { token: string; title: string; knobs: Knob[] }) {
  const [values, setValues] = useState<Record<string, number | boolean>>({});
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await cfgFetch<{ data: Record<string, number | boolean> }>(token);
      setValues(r.data);
      setLoaded(true);
    } catch { /* token/endpoint issue — panel stays hidden */ }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function save() {
    if (saving) return;
    setSaving(true);
    setSaved(false);
    try {
      const payload = Object.fromEntries(knobs.map((k) => [k.key, values[k.key]]));
      const r = await cfgFetch<{ data: Record<string, number | boolean> }>(token, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      setValues(r.data);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch { /* surfaced by staying un-saved */ } finally {
      setSaving(false);
    }
  }

  if (!loaded) return null;

  const enabledKey = knobs.find((k) => k.type === "toggle")?.key;
  const isOn = enabledKey ? !!values[enabledKey] : false;

  return (
    <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <Power className="w-3.5 h-3.5" style={{ color: enabledKey && isOn ? "#4CC38A" : "var(--muted)" }} />
          <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>{title}</p>
        </div>
        <button
          onClick={save}
          disabled={saving}
          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-md transition-all hover:brightness-110 disabled:opacity-40"
          style={{ background: saved ? "rgba(76,195,138,.12)" : "var(--accent)", color: saved ? "var(--emerald)" : "var(--ink)" }}
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : saved ? <Check className="w-3.5 h-3.5" /> : null}
          {saved ? "Saved" : "Save"}
        </button>
      </div>

      <div className="space-y-3">
        {knobs.map((k) => (
          <div key={k.key} className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-xs font-medium" style={{ color: "var(--text-2)" }}>{k.label}</p>
              {k.help && <p className="text-[11px] mt-0.5" style={{ color: "var(--muted)" }}>{k.help}</p>}
            </div>
            {k.type === "toggle" ? (
              <button
                onClick={() => setValues((v) => ({ ...v, [k.key]: !v[k.key] }))}
                className="relative w-10 h-5 rounded-full shrink-0 transition-colors"
                style={{ background: values[k.key] ? "#4CC38A" : "var(--bg3)", border: "1px solid var(--border)" }}
                aria-pressed={!!values[k.key]}
              >
                <span
                  className="absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all"
                  style={{ left: values[k.key] ? "22px" : "3px", background: values[k.key] ? "var(--ink)" : "var(--muted)" }}
                />
              </button>
            ) : (
              <input
                type="number"
                value={String(values[k.key] ?? "")}
                min={k.min}
                max={k.max}
                onChange={(e) => setValues((v) => ({ ...v, [k.key]: Number(e.target.value) }))}
                className="num text-sm rounded-md px-2.5 py-1.5 w-24 text-right outline-none shrink-0"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
            )}
          </div>
        ))}
      </div>
      <p className="text-[11px] mt-3" style={{ color: "var(--muted)" }}>
        Applies within ~15s — no redeploy. Env vars are the defaults for a fresh deploy.
      </p>
    </div>
  );
}
