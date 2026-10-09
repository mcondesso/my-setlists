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

  // Both the header nav and the login form's hint text link to #/register.
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Register" })
    .click();
  await page.getByLabel("Display name").fill("E2E Tester");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();

  // Register auto-logs in (completeLogin) and lands on the setlists screen.
  // Registering also creates the account's Library setlist, whose card also
  // shows the display name ("by E2E Tester") — match the header's span only.
  // exact: true so the page's <h1>Setlists</h1> doesn't also match the
  // <h2>My setlists</h2> section heading.
  await expect(
    page.getByRole("heading", { name: "Setlists", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("E2E Tester", { exact: true })).toBeVisible();

  await page.getByLabel("Name", { exact: true }).fill(setlistName);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: setlistName })).toBeVisible();

  await page.getByRole("heading", { name: setlistName }).click();
  await expect(
    page.getByRole("heading", { name: setlistName, level: 1 }),
  ).toBeVisible();
  await expect(page.getByText("No songs yet")).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  // Logging out lands on the public setlists page, not a login wall.
  await expect(
    page.getByRole("heading", { name: "Setlists", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Log in" })
    .click();
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();

  await expect(
    page.getByRole("heading", { name: "Setlists", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: setlistName })).toBeVisible();
});

test("a logged-out visitor can open a public setlist, then log in and land back on it", async ({
  browser,
  page,
}) => {
  const email = uniqueEmail();
  const password = "e2e-password-123";
  const setlistName = `Public E2E ${Date.now()}`;

  // An owner creates a public setlist in their own browser context.
  const ownerContext = await browser.newContext();
  const owner = await ownerContext.newPage();
  await owner.goto("/#/register");
  await owner.getByLabel("Display name").fill("Owner");
  await owner.getByLabel("Email").fill(email);
  await owner.getByLabel("Password").fill(password);
  await owner.getByRole("button", { name: "Create account" }).click();
  await owner.getByLabel("Name", { exact: true }).fill(setlistName);
  await owner.getByLabel("Public").check();
  await owner.getByRole("button", { name: "Create" }).click();
  await expect(owner.getByRole("heading", { name: setlistName })).toBeVisible();
  await ownerContext.close();

  // A visitor with no account sees it from the home page.
  await page.goto("/");
  await expect(
    page.getByText(
      "Browse the public setlists below, or log in to create your own.",
    ),
  ).toBeVisible();
  await page.getByRole("heading", { name: setlistName }).click();
  await expect(
    page.getByRole("heading", { name: setlistName, level: 1 }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Edit" })).toHaveCount(0);

  // Logging in from there returns to the same setlist, now as its owner.
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Log in" })
    .click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(
    page.getByRole("heading", { name: setlistName, level: 1 }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Edit" })).toBeVisible();
});
