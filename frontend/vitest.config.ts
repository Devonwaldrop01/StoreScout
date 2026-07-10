import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

// Unit tests for pure library logic (no DOM, no Next runtime). The `@/` alias
// mirrors tsconfig so test imports match app imports.
export default defineConfig({
  resolve: {
    alias: { "@": resolve(__dirname, ".") },
  },
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"],
  },
});
