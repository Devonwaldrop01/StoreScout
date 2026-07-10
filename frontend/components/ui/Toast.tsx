"use client";

/**
 * Global toast system. Mounted once at the root; call `useToast()` anywhere to
 * fire success / error / info toasts. Keeps actions feeling responsive and
 * premium instead of silent or inline-only.
 */

import { createContext, useCallback, useContext, useState } from "react";
import { Check, X, Info, AlertTriangle } from "lucide-react";

type ToastType = "success" | "error" | "info";
interface Toast { id: number; type: ToastType; message: string }

const ToastCtx = createContext<{ toast: (message: string, type?: ToastType) => void }>({ toast: () => {} });

export function useToast() { return useContext(ToastCtx); }

const META: Record<ToastType, { color: string; Icon: typeof Check }> = {
  success: { color: "#4CC38A", Icon: Check },
  error:   { color: "#F2555A", Icon: AlertTriangle },
  info:    { color: "#7DB8C9", Icon: Info },
};

let _id = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((message: string, type: ToastType = "info") => {
    const id = ++_id;
    setToasts((t) => [...t, { id, type, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);

  return (
    <ToastCtx.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-[calc(100vw-2rem)] sm:max-w-sm pointer-events-none">
        {toasts.map((t) => {
          const m = META[t.type];
          return (
            <div key={t.id}
              className="flex items-start gap-2.5 px-3.5 py-3 rounded-md shadow-lg pointer-events-auto toast-in"
              style={{ background: "var(--bg-card)", border: `1px solid ${m.color}55`, borderLeft: `3px solid ${m.color}` }}
              role="status">
              <m.Icon className="w-4 h-4 mt-0.5 shrink-0" style={{ color: m.color }} />
              <p className="text-[13px] leading-snug flex-1" style={{ color: "var(--text)" }}>{t.message}</p>
              <button onClick={() => setToasts((x) => x.filter((y) => y.id !== t.id))} className="shrink-0 -mr-1 -mt-0.5 p-0.5 rounded hover:bg-white/[.08]">
                <X className="w-3.5 h-3.5" style={{ color: "var(--muted)" }} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastCtx.Provider>
  );
}
