import { describe, it, expect } from "vitest";
import { postAuthDestination } from "@/lib/api";

describe("postAuthDestination — route by account state", () => {
  it("new user (no competitors) → onboarding", () => {
    expect(postAuthDestination(false, null)).toBe("/onboarding");
  });

  it("completed user (has competitors) → dashboard", () => {
    expect(postAuthDestination(true, null)).toBe("/dashboard");
  });

  it("new user preserves a plan-carrying onboarding next", () => {
    expect(postAuthDestination(false, "/onboarding?plan=pro")).toBe("/onboarding?plan=pro");
  });

  it("completed user ignores a default /onboarding next → dashboard", () => {
    // a warm, completed user hitting the signup CTA must NOT be dropped into onboarding
    expect(postAuthDestination(true, "/onboarding")).toBe("/dashboard");
  });

  it("completed user honors a specific in-app deep link", () => {
    expect(postAuthDestination(true, "/dashboard/abc123")).toBe("/dashboard/abc123");
  });

  it("never routes back to an /auth path (loop guard)", () => {
    expect(postAuthDestination(false, "/auth/login")).toBe("/onboarding");
    expect(postAuthDestination(true, "/auth/signup")).toBe("/dashboard");
  });

  it("ignores unsafe/external next values", () => {
    expect(postAuthDestination(true, "https://evil.example.com")).toBe("/dashboard");
    expect(postAuthDestination(false, "javascript:alert(1)")).toBe("/onboarding");
  });
});
