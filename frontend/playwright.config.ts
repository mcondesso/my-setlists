import { defineConfig, devices } from "@playwright/test";

const BASE_URL = "http://localhost:5173";

// Runs against the real backend + a production frontend build — the one
// thing the Vitest suite can't prove, since there everything on the other
// side of fetch() is mocked. See e2e/README.md for what this needs to run.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "html",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // reuseExistingServer means a local `npm run test:e2e` will happily use
  // your own already-running `python main.py` / `npm run dev`; CI always
  // starts fresh ones.
  webServer: [
    {
      command: "python main.py",
      cwd: "../backend",
      url: "http://localhost:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: "npm run preview -- --port 5173 --strictPort",
      url: BASE_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
});
