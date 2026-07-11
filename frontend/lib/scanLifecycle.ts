/**
 * Shared scan-lifecycle logic used by every Rescan surface (competitor card,
 * dossier, dashboard Rescan-All, onboarding first scan) so they behave
 * identically. Pure functions here are unit-tested; the useScanLifecycle hook
 * (client component) composes them with real polling + cleanup.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { competitors as api, type ScanLifecycle as BackendState } from "@/lib/api";

export type ScanUiState =
  | "idle"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "timed_out"
  | "already_in_progress"
  | "rate_limited"
  | "unavailable";

/** Map the rescan POST outcome (HTTP status) to a UI state. */
export function mapRescanStart(httpStatus: number): ScanUiState {
  switch (httpStatus) {
    case 200: return "queued";
    case 409: return "already_in_progress";
    case 429: return "rate_limited";
    case 503: return "unavailable";
    default:  return "unavailable";
  }
}

/** Map a scan-status poll (backend lifecycle) to a UI state — 1:1. */
export function mapScanPoll(state: BackendState): ScanUiState {
  return state as ScanUiState;
}

/** States where a scan is genuinely in flight → disable the button + keep polling. */
export function isBusy(s: ScanUiState): boolean {
  return s === "queued" || s === "running" || s === "already_in_progress";
}

/** Whether to keep polling scan-status. Terminal + non-job states stop. */
export function shouldPoll(s: ScanUiState): boolean {
  return isBusy(s);
}

/** Terminal states that resolve the lifecycle (success or a finished failure). */
export function isTerminal(s: ScanUiState): boolean {
  return s === "completed" || s === "failed" || s === "timed_out";
}

/** Human label per state (kept here so every surface reads the same). */
export function scanLabel(s: ScanUiState): string {
  switch (s) {
    case "queued": return "Queued…";
    case "running": return "Scanning…";
    case "already_in_progress": return "Scan in progress…";
    case "completed": return "Scan complete";
    case "failed": return "Scan failed";
    case "timed_out": return "Scan timed out";
    case "rate_limited": return "Cooldown — try again shortly";
    case "unavailable": return "Scan queue unavailable";
    default: return "";
  }
}

// ── Aggregate (Rescan All) ──────────────────────────────────────────────────
// Rescan All creates one job PER competitor (no single aggregate job), so the UI
// must show truthful per-store counts — never one fake percentage.

export interface ScanCounts {
  total: number;
  queued: number;
  running: number;
  completed: number;
  failed: number;      // failed + timed_out + unavailable (all terminal failures)
  active: number;      // queued + running (still in flight)
}

export function aggregateScanStates(states: ScanUiState[]): { counts: ScanCounts; allTerminal: boolean } {
  const counts: ScanCounts = { total: states.length, queued: 0, running: 0, completed: 0, failed: 0, active: 0 };
  for (const s of states) {
    if (s === "queued") counts.queued += 1;
    else if (s === "running" || s === "already_in_progress") counts.running += 1;
    else if (s === "completed") counts.completed += 1;
    else if (s === "failed" || s === "timed_out" || s === "unavailable" || s === "rate_limited") counts.failed += 1;
  }
  counts.active = counts.queued + counts.running;
  return { counts, allTerminal: counts.active === 0 && states.length > 0 };
}

export function aggregateLabel(counts: ScanCounts): string {
  if (counts.total === 0) return "Rescan all";
  if (counts.active > 0) {
    const parts: string[] = [];
    if (counts.queued) parts.push(`${counts.queued} queued`);
    if (counts.running) parts.push(`${counts.running} running`);
    if (counts.completed) parts.push(`${counts.completed} done`);
    return parts.join(" · ") || "Starting…";
  }
  // all terminal — honest partial-success summary
  if (counts.failed) return `${counts.completed} done · ${counts.failed} failed`;
  return `${counts.completed} rescanned`;
}

interface Options {
  onCompleted?: (lastScannedAt: string | null) => void;
  pollMs?: number;
  maxPolls?: number;
}

/**
 * Drive one competitor's rescan lifecycle: immediate ack, real polling against
 * /scan-status, terminal + retry states, completion timestamp, no fake progress,
 * bounded polling (never infinite), and interval cleanup on unmount.
 */
export function useScanLifecycle(competitorId: string, opts: Options = {}) {
  const { onCompleted, pollMs = 4000, maxPolls = 150 } = opts;
  const [state, setState] = useState<ScanUiState>("idle");
  const [completedAt, setCompletedAt] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countRef = useRef(0);
  const doneRef = useRef<Options["onCompleted"]>(onCompleted);
  doneRef.current = onCompleted;

  const clearPoll = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  // Cleanup on unmount / navigation — never leak a polling interval.
  useEffect(() => clearPoll, [clearPoll]);

  const startPolling = useCallback(() => {
    clearPoll();
    countRef.current = 0;
    pollRef.current = setInterval(async () => {
      countRef.current += 1;
      if (countRef.current > maxPolls) { clearPoll(); setState("timed_out"); return; } // bounded
      try {
        const r = await api.scanStatus(competitorId);
        const s = mapScanPoll(r.data.state);
        setState(s);
        if (s === "completed") {
          setCompletedAt(r.data.last_scanned_at ?? null);
          clearPoll();
          doneRef.current?.(r.data.last_scanned_at ?? null);
        } else if (isTerminal(s) || !shouldPoll(s)) {
          clearPoll();
        }
      } catch { /* transient — keep polling up to maxPolls */ }
    }, pollMs);
  }, [competitorId, clearPoll, maxPolls, pollMs]);

  const trigger = useCallback(async () => {
    if (isBusy(state)) return; // dedup: ignore while a scan is active
    setState("queued");        // immediate acknowledgement
    setCompletedAt(null);
    try {
      await api.rescan(competitorId);
      startPolling();
    } catch (e) {
      const status = (e as { status?: number })?.status ?? 0;
      const mapped = mapRescanStart(status);
      setState(mapped);
      if (mapped === "already_in_progress") startPolling(); // a scan IS running — watch it finish
    }
  }, [state, competitorId, startPolling]);

  return { state, completedAt, busy: isBusy(state), trigger, reset: () => setState("idle") };
}

/**
 * Rescan-all lifecycle across N competitors: fires one job each (truthful — no
 * single aggregate job exists), then polls every not-yet-terminal competitor and
 * reports honest counts (queued / running / completed / failed incl. partial
 * success). Bounded polling, cleanup on unmount, refresh callback when all
 * terminal.
 */
export function useRescanAll(ids: string[], opts: { onAllDone?: () => void; pollMs?: number; maxPolls?: number } = {}) {
  const { onAllDone, pollMs = 4000, maxPolls = 150 } = opts;
  const [active, setActive] = useState(false);
  const [counts, setCounts] = useState<ScanCounts>({ total: 0, queued: 0, running: 0, completed: 0, failed: 0, active: 0 });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countRef = useRef(0);
  const statesRef = useRef<Map<string, ScanUiState>>(new Map());
  const doneRef = useRef(opts.onAllDone);
  doneRef.current = onAllDone;

  const clearPoll = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);
  useEffect(() => clearPoll, [clearPoll]);

  const trigger = useCallback(async () => {
    if (active || ids.length === 0) return;
    setActive(true);
    countRef.current = 0;
    statesRef.current = new Map(ids.map((id) => [id, "queued" as ScanUiState]));
    setCounts(aggregateScanStates([...statesRef.current.values()]).counts);

    // Fire each rescan (staggered), recording its start outcome.
    for (const id of ids) {
      try {
        await api.rescan(id);
        statesRef.current.set(id, "queued");
      } catch (e) {
        statesRef.current.set(id, mapRescanStart((e as { status?: number })?.status ?? 0));
      }
      await new Promise<void>((r) => setTimeout(r, 150));
    }
    setCounts(aggregateScanStates([...statesRef.current.values()]).counts);

    clearPoll();
    pollRef.current = setInterval(async () => {
      countRef.current += 1;
      // Poll only the ones still in flight.
      const inflight = ids.filter((id) => isBusy(statesRef.current.get(id) ?? "idle"));
      await Promise.all(inflight.map(async (id) => {
        try {
          const r = await api.scanStatus(id);
          statesRef.current.set(id, mapScanPoll(r.data.state));
        } catch { /* keep prior state */ }
      }));
      const agg = aggregateScanStates([...statesRef.current.values()]);
      setCounts(agg.counts);
      if (agg.allTerminal || countRef.current > maxPolls) {
        // Any still-busy after the cap are shown as timed out (bounded, honest).
        if (countRef.current > maxPolls) {
          for (const id of ids) if (isBusy(statesRef.current.get(id) ?? "idle")) statesRef.current.set(id, "timed_out");
          setCounts(aggregateScanStates([...statesRef.current.values()]).counts);
        }
        clearPoll();
        setActive(false);
        doneRef.current?.();
      }
    }, pollMs);
  }, [active, ids, clearPoll, maxPolls, pollMs]);

  return { active, counts, trigger };
}
