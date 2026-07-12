import { describe, it, expect } from "vitest";
import { scanCadenceLabel, historyLabel, subscriptionNotice } from "@/lib/entitlements";

describe("scanCadenceLabel — truthful cadence, never 'Manual'", () => {
  it("free (168h) reads as Weekly, not Manual", () => {
    expect(scanCadenceLabel(168)).toBe("Weekly");
  });
  it("pro (24h) → Daily", () => {
    expect(scanCadenceLabel(24)).toBe("Daily");
  });
  it("agency (12h) → Every 12h", () => {
    expect(scanCadenceLabel(12)).toBe("Every 12h");
  });
  it("48h → Every 2d", () => {
    expect(scanCadenceLabel(48)).toBe("Every 2d");
  });
  it("defaults to Weekly on missing/invalid input (never blank, never 'Manual')", () => {
    expect(scanCadenceLabel(undefined)).toBe("Weekly");
    expect(scanCadenceLabel(0)).toBe("Weekly");
    expect(scanCadenceLabel(-5)).toBe("Weekly");
  });
});

describe("historyLabel", () => {
  it("free (0) → Current only", () => {
    expect(historyLabel(0)).toBe("Current only");
    expect(historyLabel(undefined)).toBe("Current only");
  });
  it("pro (90) → 90d", () => {
    expect(historyLabel(90)).toBe("90d");
  });
  it("agency (3650) → Full history", () => {
    expect(historyLabel(3650)).toBe("Full history");
  });
});

describe("subscriptionNotice — surfaces only actionable states", () => {
  it("warns on past_due", () => {
    const n = subscriptionNotice("past_due");
    expect(n?.tone).toBe("warn");
    expect(n?.text).toMatch(/past due/i);
  });
  it("informs on canceled (access until period end)", () => {
    const n = subscriptionNotice("canceled");
    expect(n?.tone).toBe("info");
    expect(n?.text).toMatch(/until the end/i);
  });
  it("says nothing for active / trialing / free / missing", () => {
    for (const s of ["active", "trialing", "none", "inactive", undefined, null]) {
      expect(subscriptionNotice(s)).toBeNull();
    }
  });
});
