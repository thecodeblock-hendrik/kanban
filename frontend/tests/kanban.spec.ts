import { expect, test, type Page } from "@playwright/test";
import { initialData } from "../src/lib/kanban";

test.beforeEach(async ({ request }) => {
  const response = await request.put("/api/board?user=user", {
    data: initialData,
  });
  expect(response.ok()).toBeTruthy();
});

const signIn = async (page: Page, firstColumnTitle = "Backlog") => {
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('input[aria-label="Column title"]').first()).toHaveValue(firstColumnTitle);
};

test("loads the kanban board", async ({ page }) => {
  await page.goto("/");
  await signIn(page);
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await page.goto("/");
  await signIn(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await page.goto("/");
  await signIn(page);
  const card = page.getByTestId("card-card-1");
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + 120,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
});

test("keeps a column rename after refresh", async ({ page }) => {
  await page.goto("/");
  await signIn(page);

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByLabel("Column title").fill("Persisted Backlog");
  await expect(firstColumn.getByLabel("Column title")).toHaveValue("Persisted Backlog");

  await page.reload();
  await signIn(page, "Persisted Backlog");
  await expect(page.locator('input[aria-label="Column title"]').first()).toHaveValue("Persisted Backlog");
});
