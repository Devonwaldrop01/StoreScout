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
