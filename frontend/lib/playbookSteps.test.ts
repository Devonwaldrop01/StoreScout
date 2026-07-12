import { describe, it, expect } from "vitest";
import { countDoneSteps } from "@/lib/playbookSteps";

describe("countDoneSteps — never exceeds current step count", () => {
  it("counts checks within the step range", () => {
    expect(countDoneSteps([true, false, true], 3)).toBe(2);
  });

  it("a stale, longer persisted array can never produce '8/3'", () => {
    // 8 checks stored, play now has 3 steps → at most 3.
    const stale = [true, true, true, true, true, true, true, true];
    expect(countDoneSteps(stale, 3)).toBe(3);
  });

  it("only in-range checks count when the array is longer", () => {
    expect(countDoneSteps([false, true, false, true, true], 2)).toBe(1);
  });

  it("handles empty / missing input", () => {
    expect(countDoneSteps([], 3)).toBe(0);
    expect(countDoneSteps(undefined, 3)).toBe(0);
    expect(countDoneSteps([true, true], 0)).toBe(0);
  });
});
