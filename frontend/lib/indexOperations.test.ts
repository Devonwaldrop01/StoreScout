import { describe, it, expect } from "vitest";
import { workerStatusLabel } from "./indexOperations";

describe("index worker status", () => {
  it("never converts an enabled flag or historical verification into liveness", () => {
    expect(workerStatusLabel({enabled: true, last_activity: "2026-09-11"})).toBe("Worker status unavailable");
  });
  it("distinguishes held, paused, stale and recent evidence", () => {
    expect(workerStatusLabel({enabled:true,state:"deployment_hold"})).toContain("hold enabled");
    expect(workerStatusLabel({enabled:false,state:"disabled"})).toContain("paused");
    expect(workerStatusLabel({enabled:true,state:"inactive_or_unknown"})).toContain("inert");
    expect(workerStatusLabel({enabled:true,state:"recent_activity"})).toContain("unconfirmed");
  });
});
