import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Home from "@/app/page";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

type BoardSummary = { id: number; name: string };

let users: Record<string, string>;
let boardsByUser: Record<string, BoardSummary[]>;
let boardStates: Record<number, BoardData>;
let nextBoardId: number;

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const ensureDefaultBoard = (user: string): BoardSummary[] => {
  if (!boardsByUser[user]) {
    boardsByUser[user] = [];
  }
  if (boardsByUser[user].length === 0) {
    const id = nextBoardId++;
    boardsByUser[user] = [{ id, name: "Project Board" }];
    boardStates[id] = structuredClone(initialData);
  }
  return boardsByUser[user];
};

const defaultFetchMock = async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = new URL(String(input), "http://localhost");
  const method = init?.method ?? "GET";
  const body = init?.body ? JSON.parse(String(init.body)) : undefined;

  if (url.pathname === "/api/auth/login" && method === "POST") {
    const { username, password } = body as { username: string; password: string };
    if (users[username] === password) {
      return jsonResponse({ user: { id: 1, username } });
    }
    return jsonResponse({ detail: "Invalid username or password." }, 401);
  }

  if (url.pathname === "/api/auth/register" && method === "POST") {
    const { username, password } = body as { username: string; password: string };
    if (users[username] !== undefined) {
      return jsonResponse({ detail: "Username already exists." }, 400);
    }
    users[username] = password;
    return jsonResponse({ user: { id: 2, username } });
  }

  if (url.pathname === "/api/boards" && method === "GET") {
    const user = url.searchParams.get("user") ?? "user";
    return jsonResponse({ boards: ensureDefaultBoard(user) });
  }

  if (url.pathname === "/api/boards" && method === "POST") {
    const user = url.searchParams.get("user") ?? "user";
    const { name } = body as { name: string };
    const id = nextBoardId++;
    const board = { id, name };
    boardsByUser[user] = [...ensureDefaultBoard(user), board];
    boardStates[id] = structuredClone(initialData);
    return jsonResponse({ board });
  }

  const boardIdMatch = url.pathname.match(/^\/api\/boards\/(\d+)$/);
  if (boardIdMatch && method === "PATCH") {
    const user = url.searchParams.get("user") ?? "user";
    const id = Number(boardIdMatch[1]);
    const { name } = body as { name: string };
    boardsByUser[user] = boardsByUser[user].map((board) =>
      board.id === id ? { ...board, name } : board
    );
    return jsonResponse({ board: { id, name } });
  }
  if (boardIdMatch && method === "DELETE") {
    const user = url.searchParams.get("user") ?? "user";
    const id = Number(boardIdMatch[1]);
    boardsByUser[user] = boardsByUser[user].filter((board) => board.id !== id);
    delete boardStates[id];
    return jsonResponse({ ok: true });
  }

  if (url.pathname === "/api/board" && method === "GET") {
    const boardId = Number(url.searchParams.get("boardId"));
    return jsonResponse({ user: "user", boardId, board: structuredClone(boardStates[boardId]) });
  }

  if (url.pathname === "/api/board" && method === "PUT") {
    const boardId = Number(url.searchParams.get("boardId"));
    boardStates[boardId] = body as BoardData;
    return jsonResponse({ user: "user", boardId, board: structuredClone(boardStates[boardId]) });
  }

  return jsonResponse({ user: "user", board: structuredClone(initialData) });
};

beforeEach(() => {
  users = { user: "password" };
  boardsByUser = {};
  boardStates = {};
  nextBoardId = 1;
  window.localStorage.clear();
  vi.spyOn(globalThis, "fetch").mockImplementation(defaultFetchMock);
});

afterEach(() => {
  vi.restoreAllMocks();
});

const noop = () => {};

const kanbanBoardProps = (overrides: Partial<Parameters<typeof KanbanBoard>[0]> = {}) => ({
  username: "user",
  boardId: 1,
  boards: [{ id: 1, name: "Project Board" }],
  onSelectBoard: noop,
  onCreateBoard: noop,
  onRenameBoard: noop,
  onDeleteBoard: noop,
  ...overrides,
});

describe("KanbanBoard", () => {
  beforeEach(() => {
    boardsByUser.user = [{ id: 1, name: "Project Board" }];
    boardStates[1] = structuredClone(initialData);
  });

  it("loads the board from the API", async () => {
    boardStates[1].columns[0].title = "API Backlog";

    render(<KanbanBoard {...kanbanBoardProps()} />);

    expect(await screen.findByDisplayValue("API Backlog")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/api/board?user=user&boardId=1");
  });

  it("saves a board change through the API", async () => {
    render(<KanbanBoard {...kanbanBoardProps()} />);
    await screen.findByDisplayValue("Backlog");
    const input = within(getFirstColumn()).getByLabelText("Column title");

    await userEvent.clear(input);
    await userEvent.type(input, "Saved Backlog");

    await waitFor(() => {
      expect(boardStates[1].columns[0].title).toBe("Saved Backlog");
    });
  });

  it("keeps the latest value when saving rapid board updates", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock.mockClear();

    render(<KanbanBoard {...kanbanBoardProps()} />);
    await screen.findByDisplayValue("Backlog");

    const input = within(getFirstColumn()).getByLabelText("Column title");
    fireEvent.change(input, { target: { value: "Draft 1" } });
    fireEvent.change(input, { target: { value: "Draft 2" } });
    fireEvent.change(input, { target: { value: "Final draft" } });

    await waitFor(
      () => {
        const putCalls = fetchMock.mock.calls.filter(
          ([url, init]) => String(url).includes("/api/board") && init?.method === "PUT"
        );
        expect(putCalls.length).toBeGreaterThan(0);
        expect(boardStates[1].columns[0].title).toBe("Final draft");
      },
      { timeout: 2000 }
    );
  });

  it("renders five columns", async () => {
    render(<KanbanBoard {...kanbanBoardProps()} />);
    await screen.findByDisplayValue("Backlog");
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard {...kanbanBoardProps()} />);
    await screen.findByDisplayValue("Backlog");
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard {...kanbanBoardProps()} />);
    await screen.findByDisplayValue("Backlog");
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("sets a due date and priority when adding a card, and shows them on the card", async () => {
    render(<KanbanBoard {...kanbanBoardProps()} />);
    await screen.findByDisplayValue("Backlog");
    const column = getFirstColumn();

    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText(/card title/i), "Ship report");
    await userEvent.type(within(column).getByLabelText(/due date/i), "2020-01-01");
    await userEvent.selectOptions(within(column).getByLabelText(/priority/i), "high");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    const card = within(column).getByText("Ship report").closest("article");
    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByText("high")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText(/2020-01-01/)).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText(/overdue/i)).toBeInTheDocument();
  });

  it("filters cards by search text and priority", async () => {
    render(<KanbanBoard {...kanbanBoardProps()} />);
    await screen.findByDisplayValue("Backlog");
    const column = getFirstColumn();

    expect(within(column).getByText("Align roadmap themes")).toBeInTheDocument();
    expect(within(column).getByText("Gather customer signals")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/search cards/i), "roadmap");

    expect(within(column).getByText("Align roadmap themes")).toBeInTheDocument();
    expect(within(column).queryByText("Gather customer signals")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /clear filters/i }));
    expect(within(column).getByText("Gather customer signals")).toBeInTheDocument();
  });

  it("sends a chat message to the AI and refreshes the board after a valid AI update", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes("/api/ai/board")) {
        return new Response(
          JSON.stringify({
            response: "Updated the board.",
            board: {
              columns: [
                { id: "col-backlog", title: "Launch Queue", cardIds: ["card-1", "card-2"] },
                { id: "col-discovery", title: "Discovery", cardIds: ["card-3"] },
                { id: "col-progress", title: "In Progress", cardIds: ["card-4", "card-5"] },
                { id: "col-review", title: "Review", cardIds: ["card-6"] },
                { id: "col-done", title: "Done", cardIds: ["card-7", "card-8"] },
              ],
              cards: boardStates[1].cards,
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }

      return defaultFetchMock(input, init);
    });

    render(<KanbanBoard {...kanbanBoardProps()} />);
    await screen.findByDisplayValue("Backlog");

    await userEvent.type(screen.getByLabelText(/ask the AI/i), "Rename the backlog to Launch Queue.");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText("Updated the board.")).toBeInTheDocument();
    expect(await screen.findByDisplayValue("Launch Queue")).toBeInTheDocument();
  });
});

describe("Auth flow", () => {
  it("requires login before showing the board", () => {
    render(<Home />);

    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.queryByText("Kanban Studio")).not.toBeInTheDocument();
  });

  it("accepts valid credentials and shows the board", async () => {
    render(<Home />);

    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Kanban Studio")).toBeInTheDocument();
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("rejects invalid credentials", async () => {
    render(<Home />);

    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/invalid username or password/i)).toBeInTheDocument();
    expect(screen.queryByText("Kanban Studio")).not.toBeInTheDocument();
  });

  it("logs the user out", async () => {
    render(<Home />);

    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await screen.findByText("Kanban Studio");

    await userEvent.click(screen.getByRole("button", { name: /log out/i }));

    expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.queryByText("Kanban Studio")).not.toBeInTheDocument();
  });

  it("keeps the board state after logout and login", async () => {
    render(<Home />);

    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await screen.findByDisplayValue("Backlog");

    const column = screen.getAllByTestId(/column-/i)[0];
    const addButton = within(column).getByRole("button", { name: /add a card/i });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "Persisted card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Saved state");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    await waitFor(
      () => {
        const boardId = boardsByUser.user[0].id;
        expect(
          Object.values(boardStates[boardId]?.cards ?? {}).some(
            (card) => card.title === "Persisted card"
          )
        ).toBe(true);
      },
      { timeout: 2000 }
    );
    await new Promise((resolve) => setTimeout(resolve, 500));

    await userEvent.click(screen.getByRole("button", { name: /log out/i }));
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Persisted card")).toBeInTheDocument();
  });

  it("can register a new account and then log in with it", async () => {
    render(<Home />);

    await userEvent.click(screen.getByRole("button", { name: /need an account\? register/i }));
    await userEvent.type(screen.getByLabelText(/username/i), "newuser");
    await userEvent.type(screen.getByLabelText(/password/i), "hunter22");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/account created/i)).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText(/username/i));
    await userEvent.clear(screen.getByLabelText(/password/i));
    await userEvent.type(screen.getByLabelText(/username/i), "newuser");
    await userEvent.type(screen.getByLabelText(/password/i), "hunter22");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Kanban Studio")).toBeInTheDocument();
  });
});
