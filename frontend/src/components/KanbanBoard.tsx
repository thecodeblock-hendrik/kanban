"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  pointerWithin,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, initialData, moveCard, type BoardData } from "@/lib/kanban";

type KanbanBoardProps = {
  username?: string;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export const KanbanBoard = ({ username = "user" }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData>(initialData);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState("");
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const saveSequenceRef = useRef(0);
  const [aiInput, setAiInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: "Hi! Ask me to rename a column, create a card, or update the board." },
  ]);
  const [isAiLoading, setIsAiLoading] = useState(false);

  useEffect(() => {
    let isCurrent = true;

    const loadBoard = async () => {
      try {
        const response = await fetch(`/api/board?user=${encodeURIComponent(username)}`);
        if (!response.ok) {
          throw new Error("Unable to load the board.");
        }

        const data = (await response.json()) as { board: BoardData };
        if (isCurrent) {
          setBoard(data.board);
          setIsLoaded(true);
          setError("");
        }
      } catch {
        if (isCurrent) {
          setIsLoaded(true);
          setError("Unable to load the board from the server.");
        }
      }
    };

    setIsLoaded(false);
    void loadBoard();

    return () => {
      isCurrent = false;
    };
  }, [username]);

  useEffect(() => {
    if (!isLoaded) {
      return;
    }

    const saveId = ++saveSequenceRef.current;
    const saveBoard = async () => {
      try {
        const response = await fetch(`/api/board?user=${encodeURIComponent(username)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(board),
          keepalive: true,
        });

        if (saveId !== saveSequenceRef.current) {
          return;
        }

        if (!response.ok) {
          throw new Error("Unable to save the board.");
        }

        setError("");
      } catch {
        if (saveId === saveSequenceRef.current) {
          setError("Unable to save the board to the server.");
        }
      }
    };

    void saveBoard();
  }, [board, isLoaded, username]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board.cards, [board.cards]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over) {
      return;
    }

    const rawOverId = typeof over.data?.current?.columnId === "string"
      ? over.data.current.columnId
      : String(over.id);
    const overColumnId = rawOverId.replace(/-empty$/, "");

    if (active.id === overColumnId) {
      return;
    }

    setBoard((prev) => ({
      ...prev,
      columns: moveCard(prev.columns, String(active.id), overColumnId),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    setBoard((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    setBoard((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    setBoard((prev) => {
      return {
        ...prev,
        cards: Object.fromEntries(
          Object.entries(prev.cards).filter(([id]) => id !== cardId)
        ),
        columns: prev.columns.map((column) =>
          column.id === columnId
            ? {
                ...column,
                cardIds: column.cardIds.filter((id) => id !== cardId),
              }
            : column
        ),
      };
    });
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  const handleAiSubmit = async () => {
    const trimmedPrompt = aiInput.trim();
    if (!trimmedPrompt || isAiLoading) {
      return;
    }

    const nextMessages: ChatMessage[] = [
      ...chatMessages,
      { role: "user", content: trimmedPrompt },
    ];
    setChatMessages(nextMessages);
    setAiInput("");
    setIsAiLoading(true);

    try {
      const response = await fetch(`/api/ai/board?user=${encodeURIComponent(username)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: trimmedPrompt,
          history: nextMessages.map(({ role, content }) => ({ role, content })),
        }),
      });

      if (!response.ok) {
        throw new Error("Unable to contact the AI assistant.");
      }

      const data = (await response.json()) as { response: string; board?: BoardData };
      const assistantMessage = data.response || "I updated the board.";
      setChatMessages((prev) => [...prev, { role: "assistant", content: assistantMessage }]);

      if (data.board) {
        setBoard(data.board);
      }
    } catch {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: "I couldn’t process that request. Please try again." },
      ]);
    } finally {
      setIsAiLoading(false);
    }
  };

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>
          {error ? <p className="text-sm font-medium text-red-600">{error}</p> : null}
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <DndContext
            sensors={sensors}
            collisionDetection={pointerWithin}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-6 lg:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>

          <aside className="rounded-[28px] border border-[var(--stroke)] bg-white/80 p-5 shadow-[var(--shadow)] backdrop-blur">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-display text-2xl font-semibold text-[var(--navy-dark)]">
                AI assistant
              </h2>
              <span className="rounded-full bg-[var(--surface)] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Live
              </span>
            </div>

            <div className="flex max-h-[540px] flex-col gap-3 overflow-y-auto pr-1">
              {chatMessages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`max-w-[90%] rounded-2xl px-3 py-2 text-sm leading-6 ${
                    message.role === "user"
                      ? "ml-auto bg-[var(--primary-blue)] text-white"
                      : "bg-[var(--surface)] text-[var(--navy-dark)]"
                  }`}
                >
                  {message.content}
                </div>
              ))}
              {isAiLoading ? (
                <div className="max-w-[90%] rounded-2xl bg-[var(--surface)] px-3 py-2 text-sm text-[var(--gray-text)]">
                  Thinking...
                </div>
              ) : null}
            </div>

            <div className="mt-5 space-y-3">
              <label htmlFor="ai-prompt" className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Ask the AI
              </label>
              <textarea
                id="ai-prompt"
                value={aiInput}
                onChange={(event) => setAiInput(event.target.value)}
                rows={4}
                placeholder="Ask the AI to rename a column or update the board..."
                className="w-full resize-none rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              />
              <button
                type="button"
                onClick={handleAiSubmit}
                disabled={isAiLoading || !aiInput.trim()}
                className="w-full rounded-xl bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold text-white transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Send
              </button>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
};
