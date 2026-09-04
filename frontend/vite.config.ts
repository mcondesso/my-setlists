import { svelteTesting } from "@testing-library/svelte/vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vitest/config";

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte(), ...(process.env.VITEST ? [svelteTesting()] : [])],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest-setup.ts"],
    // Playwright specs live in e2e/ and run via `npm run test:e2e`, not
    // Vitest — exclude them explicitly since Vitest's default include glob
    // would otherwise pick up e2e/*.spec.ts too.
    include: ["src/**/*.{test,spec}.ts"],
  },
});
