"use client";

import { useEffect, useState } from "react";
import { LogOut } from "lucide-react";
import { KanbanBoard } from "@/components/KanbanBoard";
import type { BoardSummary } from "@/components/BoardSwitcher";

type AuthMode = "login" | "register";

export default function Home() {
  const [mode, setMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [currentUser, setCurrentUser] = useState<string | null>(null);
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [selectedBoardId, setSelectedBoardId] = useState<number | null>(null);

  const loadBoards = async (user: string) => {
    const response = await fetch(`/api/boards?user=${encodeURIComponent(user)}`);
    if (!response.ok) {
      throw new Error("Unable to load boards.");
    }
    const data = (await response.json()) as { boards: BoardSummary[] };
    setBoards(data.boards);
    setSelectedBoardId((current) =>
      data.boards.some((board) => board.id === current) ? current : (data.boards[0]?.id ?? null)
    );
  };

  useEffect(() => {
    if (currentUser) {
      void loadBoards(currentUser).catch(() => setError("Unable to load your boards."));
    }
  }, [currentUser]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = (await response.json()) as { user?: { username: string }; detail?: string };

      if (!response.ok) {
        setError(data.detail || "Something went wrong. Please try again.");
        return;
      }

      if (mode === "register") {
        setMode("login");
        setError("Account created. Please sign in.");
        setPassword("");
        return;
      }

      setCurrentUser(data.user?.username ?? username);
    } catch {
      setError("Unable to reach the server. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setUsername("");
    setPassword("");
    setError("");
    setBoards([]);
    setSelectedBoardId(null);
  };

  const handleCreateBoard = async (name: string) => {
    if (!currentUser) return;
    const response = await fetch(`/api/boards?user=${encodeURIComponent(currentUser)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (response.ok) {
      const data = (await response.json()) as { board: BoardSummary };
      setBoards((prev) => [...prev, data.board]);
      setSelectedBoardId(data.board.id);
    }
  };

  const handleRenameBoard = async (boardId: number, name: string) => {
    if (!currentUser) return;
    const response = await fetch(
      `/api/boards/${boardId}?user=${encodeURIComponent(currentUser)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      }
    );
    if (response.ok) {
      setBoards((prev) => prev.map((board) => (board.id === boardId ? { ...board, name } : board)));
    }
  };

  const handleDeleteBoard = async (boardId: number) => {
    if (!currentUser) return;
    const response = await fetch(
      `/api/boards/${boardId}?user=${encodeURIComponent(currentUser)}`,
      { method: "DELETE" }
    );
    if (response.ok) {
      const remaining = boards.filter((board) => board.id !== boardId);
      setBoards(remaining);
      setSelectedBoardId((current) => (current === boardId ? (remaining[0]?.id ?? null) : current));
    }
  };

  if (!currentUser) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-6 py-12">
        <div className="w-full max-w-md rounded-[28px] border border-[var(--stroke)] bg-white p-8 shadow-[var(--shadow)]">
          <div className="mb-8">
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-[var(--gray-text)]">
              Project Manager
            </p>
            <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
              {mode === "login" ? "Sign in" : "Create account"}
            </h1>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label htmlFor="username" className="text-sm font-medium text-[var(--navy-dark)]">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2.5 text-sm outline-none ring-0 transition focus:border-[var(--primary-blue)]"
                autoComplete="username"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-[var(--navy-dark)]">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2.5 text-sm outline-none ring-0 transition focus:border-[var(--primary-blue)]"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
            </div>

            {error ? (
              <p className="text-sm font-medium text-red-600">{error}</p>
            ) : null}

            <button
              type="submit"
              disabled={isSubmitting || !username.trim() || !password}
              className="w-full rounded-xl bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold text-white transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>

          <button
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
            }}
            className="mt-5 w-full text-center text-sm font-semibold text-[var(--primary-blue)] hover:underline"
          >
            {mode === "login" ? "Need an account? Register" : "Already have an account? Sign in"}
          </button>
        </div>
      </main>
    );
  }

  return (
    <div>
      <header className="flex items-center justify-between px-6 pt-6">
        <p className="text-sm font-semibold text-[var(--navy-dark)]">
          Signed in as <span className="text-[var(--primary-blue)]">{currentUser}</span>
        </p>
        <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-2 rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-sm font-semibold text-[var(--navy-dark)] shadow-sm transition hover:border-[var(--primary-blue)]"
        >
          <LogOut size={15} strokeWidth={2.5} />
          Log out
        </button>
      </header>
      {selectedBoardId !== null ? (
        <KanbanBoard
          username={currentUser}
          boardId={selectedBoardId}
          boards={boards}
          onSelectBoard={setSelectedBoardId}
          onCreateBoard={handleCreateBoard}
          onRenameBoard={handleRenameBoard}
          onDeleteBoard={handleDeleteBoard}
        />
      ) : null}
    </div>
  );
}
