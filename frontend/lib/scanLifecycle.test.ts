import { describe, it, expect } from "vitest";
import {
  mapRescanStart, mapScanPoll, isBusy, shouldPoll, isTerminal, scanLabel,
  aggregateScanStates, aggregateLabel,
  type ScanUiState,
} from "@/lib/scanLifecycle";

describe("mapRescanStart — POST outcome → UI state", () => {
  it("200 acknowledges as queued", () => expect(mapRescanStart(200)).toBe("queued"));
  it("409 → already_in_progress", () => expect(mapRescanStart(409)).toBe("already_in_progress"));
  it("429 → rate_limited", () => expect(mapRescanStart(429)).toBe("rate_limited"));
  it("503 → unavailable", () => expect(mapRescanStart(503)).toBe("unavailable"));
  it("any other error → unavailable", () => expect(mapRescanStart(500)).toBe("unavailable"));
});

describe("mapScanPoll — backend lifecycle → UI state", () => {
  it("maps each backend state 1:1", () => {
    expect(mapScanPoll("running")).toBe("running");
    expect(mapScanPoll("completed")).toBe("completed");
    expect(mapScanPoll("failed")).toBe("failed");
    expect(mapScanPoll("timed_out")).toBe("timed_out");
    expect(mapScanPoll("queued")).toBe("queued");
    expect(mapScanPoll("idle")).toBe("idle");
  });
});

describe("busy / polling / terminal predicates", () => {
  const busy: ScanUiState[] = ["queued", "running", "already_in_progress"];
  const terminal: ScanUiState[] = ["completed", "failed", "timed_out"];
  const stopNoJob: ScanUiState[] = ["rate_limited", "unavailable", "idle"];

  it("busy states disable the button and keep polling", () => {
    for (const s of busy) { expect(isBusy(s)).toBe(true); expect(shouldPoll(s)).toBe(true); }
  });
  it("terminal states stop polling and are not busy", () => {
    for (const s of terminal) { expect(isBusy(s)).toBe(false); expect(shouldPoll(s)).toBe(false); expect(isTerminal(s)).toBe(true); }
  });
  it("rate_limited / unavailable / idle do not poll and are not terminal", () => {
    for (const s of stopNoJob) { expect(shouldPoll(s)).toBe(false); expect(isTerminal(s)).toBe(false); expect(isBusy(s)).toBe(false); }
  });
});

describe("aggregateScanStates — Rescan All truthful counts", () => {
  it("counts queued / running / completed / failed and active", () => {
    const { counts, allTerminal } = aggregateScanStates(["queued", "running", "completed", "failed", "already_in_progress"]);
    expect(counts.total).toBe(5);
    expect(counts.queued).toBe(1);
    expect(counts.running).toBe(2);       // running + already_in_progress
    expect(counts.completed).toBe(1);
    expect(counts.failed).toBe(1);
    expect(counts.active).toBe(3);
    expect(allTerminal).toBe(false);      // still active
  });

  it("reports allTerminal only when nothing is active", () => {
    expect(aggregateScanStates(["completed", "completed"]).allTerminal).toBe(true);
    expect(aggregateScanStates(["completed", "running"]).allTerminal).toBe(false);
    expect(aggregateScanStates([]).allTerminal).toBe(false); // no jobs
  });

  it("partial success — completed + failed is reported honestly", () => {
    const { counts, allTerminal } = aggregateScanStates(["completed", "completed", "failed", "timed_out", "unavailable"]);
    expect(allTerminal).toBe(true);
    expect(counts.completed).toBe(2);
    expect(counts.failed).toBe(3);        // failed + timed_out + unavailable
    expect(aggregateLabel(counts)).toContain("failed");
  });

  it("aggregateLabel shows live counts while active and a summary when done", () => {
    expect(aggregateLabel({ total: 3, queued: 1, running: 1, completed: 1, failed: 0, active: 2 })).toMatch(/queued|running|done/);
    expect(aggregateLabel({ total: 2, queued: 0, running: 0, completed: 2, failed: 0, active: 0 })).toContain("rescanned");
  });
});

describe("scanLabel — every state has a human label", () => {
  it("covers all non-idle states", () => {
    for (const s of ["queued", "running", "already_in_progress", "completed", "failed", "timed_out", "rate_limited", "unavailable"] as ScanUiState[]) {
      expect(scanLabel(s).length).toBeGreaterThan(0);
    }
  });
});
