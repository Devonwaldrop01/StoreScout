"use client";

/**
 * Save to Playbook — the universal action affordance. Any recommendation in
 * the app (signal, gap, winning product, pricing observation, brief move,
 * Pro-analysis opportunity) becomes a persisted task with its evidence and a
 * link back to its source. Saves are idempotent server-side.
 */

import { useState } from "react";
import { BookmarkPlus, Check, Loader2 } from "lucide-react";
import { playbookItems, type SavePlaybookItemInput } from "@/lib/api";

export function SaveToPlaybook({
  item, size = "sm", onSaved,
}: {
  item: SavePlaybookItemInput;
  size?: "sm" | "xs";
  onSaved?: () => void;
}) {
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");

  async function save(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (state === "saving" || state === "saved") return;
    setState("saving");
    try {
      await playbookItems.create(item);
      setState("saved");
      onSaved?.();
    } catch {
      setState("error");
      setTimeout(() => setState("idle"), 2500);
    }
  }

  const pad = size === "xs" ? "px-2 py-1" : "px-2.5 py-1.5";
  const icon = size === "xs" ? "w-3 h-3" : "w-3.5 h-3.5";

  if (state === "saved") {
    return (
      <span
        className={`inline-flex items-center gap-1 text-[11px] font-semibold rounded ${pad} shrink-0`}
        style={{ background: "rgba(76,195,138,.1)", color: "var(--emerald)", border: "1px solid rgba(76,195,138,.2)" }}
      >
        <Check className={icon} /> In Playbook
      </span>
    );
  }

  return (
    <button
      onClick={save}
      disabled={state === "saving"}
      title="Save this move to your Playbook with its evidence"
      className={`inline-flex items-center gap-1 text-[11px] font-semibold rounded transition-all hover:bg-white/[.06] disabled:opacity-50 ${pad} shrink-0`}
      style={{
        color: state === "error" ? "#F2555A" : "var(--text-2)",
        border: "1px solid var(--border)",
        background: "var(--bg3)",
      }}
    >
      {state === "saving" ? <Loader2 className={`${icon} animate-spin`} /> : <BookmarkPlus className={icon} />}
      {state === "error" ? "Retry" : "Save to Playbook"}
    </button>
  );
}
