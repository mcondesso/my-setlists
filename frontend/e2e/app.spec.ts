import { expect, test } from "@playwright/test";

function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
}

test("register, create a setlist, log out, and log back in to find it", async ({
  page,
}) => {
  const email = uniqueEmail();
  const password = "e2e-password-123";
  const setlistName = `E2E Setlist ${Date.now()}`;

  await page.goto("/");

  await page.getByRole("link", { name: "Register" }).click();
  await page.getByLabel("Display name").fill("E2E Tester");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();

  // Register auto-logs in (completeLogin) and lands on the setlists screen.
  await expect(page.getByRole("heading", { name: "Setlists" })).toBeVisible();
  await expect(page.getByText("E2E Tester")).toBeVisible();

  await page.getByLabel("Name", { exact: true }).fill(setlistName);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: setlistName })).toBeVisible();

  await page.getByRole("heading", { name: setlistName }).click();
  await expect(
    page.getByRole("heading", { name: setlistName, level: 1 }),
  ).toBeVisible();
  await expect(page.getByText("No songs yet")).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();

  await expect(page.getByRole("heading", { name: "Setlists" })).toBeVisible();
  await expect(page.getByRole("heading", { name: setlistName })).toBeVisible();
});
