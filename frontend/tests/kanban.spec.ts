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

test("moves a card into an empty column", async ({ page, request }) => {
  const emptyBoard = structuredClone(initialData);
  emptyBoard.columns = [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-discovery", title: "Discovery", cardIds: ["card-3"] },
    { id: "col-progress", title: "In Progress", cardIds: ["card-4", "card-5"] },
    { id: "col-review", title: "Review", cardIds: [] },
    { id: "col-done", title: "Done", cardIds: ["card-6", "card-7", "card-8"] },
  ];

  const response = await request.put("/api/board?user=user", {
    data: emptyBoard,
  });
  expect(response.ok()).toBeTruthy();

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

test("can register a new account and see an isolated board", async ({ page }) => {
  const username = `pw-user-${Date.now()}`;

  await page.goto("/");
  await page.getByRole("button", { name: /need an account\? register/i }).click();
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill("hunter22");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByText(/account created/i)).toBeVisible();

  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill("hunter22");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('input[aria-label="Column title"]').first()).toHaveValue("Backlog");
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("creates, renames, switches, and deletes a second board", async ({ page }) => {
  const boardName = `Marketing ${Date.now()}`;

  await page.goto("/");
  await signIn(page);

  await page.getByRole("button", { name: /new board/i }).click();
  await page.getByPlaceholder("Board name").fill(boardName);
  await page.getByPlaceholder("Board name").press("Enter");

  const marketingTab = page.getByRole("button", { name: boardName, exact: true });
  await expect(marketingTab).toBeVisible();
  await marketingTab.click();

  await expect(page.locator('input[aria-label="Column title"]').first()).toHaveValue("Backlog");

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByLabel("Column title").fill("Campaigns");
  await expect(firstColumn.getByLabel("Column title")).toHaveValue("Campaigns");

  await page.getByRole("button", { name: "Project Board", exact: true }).click();
  await expect(page.locator('input[aria-label="Column title"]').first()).toHaveValue("Backlog");

  await page.getByLabel(`Delete ${boardName}`).click();
  await expect(page.getByRole("button", { name: boardName, exact: true })).toHaveCount(0);
});

test("sets a card's due date and priority, then filters the board", async ({ page }) => {
  await page.goto("/");
  await signIn(page);

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Overdue task");
  await firstColumn.getByLabel(/due date/i).fill("2020-01-01");
  await firstColumn.getByLabel(/priority/i).selectOption("high");
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  const newCard = firstColumn.getByTestId(/^card-card-/).filter({ hasText: "Overdue task" });
  await expect(newCard.getByText("high", { exact: true })).toBeVisible();
  await expect(newCard.getByText("(overdue)")).toBeVisible();

  await page.getByLabel(/search cards/i).fill("Overdue task");
  await expect(page.getByText("Align roadmap themes")).not.toBeVisible();
  await expect(firstColumn.getByText("Overdue task")).toBeVisible();

  await page.getByRole("button", { name: /clear filters/i }).click();
  await expect(page.getByText("Align roadmap themes")).toBeVisible();

  await page.getByRole("checkbox", { name: /overdue only/i }).check();
  await expect(firstColumn.getByText("Overdue task")).toBeVisible();
  await expect(page.getByText("Align roadmap themes")).not.toBeVisible();
});
