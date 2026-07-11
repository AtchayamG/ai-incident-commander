import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // The default forks pool crashes tinypool on Windows paths with spaces.
    pool: "threads",
  },
});
