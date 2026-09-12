import {
  cardMatchesFilter,
  defaultFilter,
  isFilterActive,
  isOverdue,
  moveCard,
  type BoardFilter,
  type Card,
  type Column,
} from "@/lib/kanban";

describe("moveCard", () => {
  const baseColumns: Column[] = [
    { id: "col-a", title: "A", cardIds: ["card-1", "card-2"] },
    { id: "col-b", title: "B", cardIds: ["card-3"] },
  ];

  it("reorders cards in the same column", () => {
    const result = moveCard(baseColumns, "card-2", "card-1");
    expect(result[0].cardIds).toEqual(["card-2", "card-1"]);
  });

  it("moves cards to another column", () => {
    const result = moveCard(baseColumns, "card-2", "card-3");
    expect(result[0].cardIds).toEqual(["card-1"]);
    expect(result[1].cardIds).toEqual(["card-2", "card-3"]);
  });

  it("drops cards to the end of a column", () => {
    const result = moveCard(baseColumns, "card-1", "col-b");
    expect(result[0].cardIds).toEqual(["card-2"]);
    expect(result[1].cardIds).toEqual(["card-3", "card-1"]);
  });

  it("moves a card into an empty target column", () => {
    const columns: Column[] = [
      { id: "col-a", title: "A", cardIds: ["card-1"] },
      { id: "col-b", title: "B", cardIds: [] },
    ];

    const result = moveCard(columns, "card-1", "col-b");
    expect(result[0].cardIds).toEqual([]);
    expect(result[1].cardIds).toEqual(["card-1"]);
  });
});

describe("isOverdue", () => {
  const today = new Date("2026-06-15T09:00:00");

  it("is false when there is no due date", () => {
    const card: Card = { id: "c1", title: "T", details: "" };
    expect(isOverdue(card, today)).toBe(false);
  });

  it("is true when the due date is in the past", () => {
    const card: Card = { id: "c1", title: "T", details: "", dueDate: "2026-06-01" };
    expect(isOverdue(card, today)).toBe(true);
  });

  it("is false when the due date is today or in the future", () => {
    const todayCard: Card = { id: "c1", title: "T", details: "", dueDate: "2026-06-15" };
    const futureCard: Card = { id: "c2", title: "T", details: "", dueDate: "2026-07-01" };
    expect(isOverdue(todayCard, today)).toBe(false);
    expect(isOverdue(futureCard, today)).toBe(false);
  });
});

describe("cardMatchesFilter", () => {
  const today = new Date("2026-06-15T09:00:00");
  const card: Card = {
    id: "c1",
    title: "Refine status language",
    details: "Standardize column labels and tone.",
    priority: "high",
    dueDate: "2026-06-01",
  };

  it("matches everything with the default filter", () => {
    expect(cardMatchesFilter(card, defaultFilter, today)).toBe(true);
  });

  it("matches on title/details text, case-insensitively", () => {
    const filter: BoardFilter = { ...defaultFilter, text: "STATUS" };
    expect(cardMatchesFilter(card, filter, today)).toBe(true);
    expect(cardMatchesFilter(card, { ...defaultFilter, text: "nope" }, today)).toBe(false);
  });

  it("matches on priority", () => {
    expect(cardMatchesFilter(card, { ...defaultFilter, priority: "high" }, today)).toBe(true);
    expect(cardMatchesFilter(card, { ...defaultFilter, priority: "low" }, today)).toBe(false);
  });

  it("treats a card with no priority as medium", () => {
    const mediumCard: Card = { id: "c2", title: "T", details: "" };
    expect(cardMatchesFilter(mediumCard, { ...defaultFilter, priority: "medium" }, today)).toBe(true);
  });

  it("matches on overdue-only", () => {
    expect(cardMatchesFilter(card, { ...defaultFilter, overdueOnly: true }, today)).toBe(true);
    const notOverdue: Card = { ...card, dueDate: "2026-07-01" };
    expect(cardMatchesFilter(notOverdue, { ...defaultFilter, overdueOnly: true }, today)).toBe(false);
  });

  it("combines all filter criteria", () => {
    const filter: BoardFilter = { text: "refine", priority: "high", overdueOnly: true };
    expect(cardMatchesFilter(card, filter, today)).toBe(true);
    expect(cardMatchesFilter(card, { ...filter, priority: "low" }, today)).toBe(false);
  });
});

describe("isFilterActive", () => {
  it("is false for the default filter", () => {
    expect(isFilterActive(defaultFilter)).toBe(false);
  });

  it("is true when any criterion is set", () => {
    expect(isFilterActive({ ...defaultFilter, text: "x" })).toBe(true);
    expect(isFilterActive({ ...defaultFilter, priority: "high" })).toBe(true);
    expect(isFilterActive({ ...defaultFilter, overdueOnly: true })).toBe(true);
  });
});
