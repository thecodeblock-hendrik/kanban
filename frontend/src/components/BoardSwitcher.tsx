"use client";

import { useState } from "react";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";

export type BoardSummary = {
  id: number;
  name: string;
};

type BoardSwitcherProps = {
  boards: BoardSummary[];
  selectedBoardId: number | null;
  onSelect: (boardId: number) => void;
  onCreate: (name: string) => void;
  onRename: (boardId: number, name: string) => void;
  onDelete: (boardId: number) => void;
};

export const BoardSwitcher = ({
  boards,
  selectedBoardId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: BoardSwitcherProps) => {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [newBoardName, setNewBoardName] = useState("");

  const startEditing = (board: BoardSummary) => {
    setEditingId(board.id);
    setEditingName(board.name);
  };

  const commitEdit = () => {
    if (editingId !== null && editingName.trim()) {
      onRename(editingId, editingName.trim());
    }
    setEditingId(null);
    setEditingName("");
  };

  const commitCreate = () => {
    if (newBoardName.trim()) {
      onCreate(newBoardName.trim());
    }
    setNewBoardName("");
    setIsCreating(false);
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {boards.map((board) =>
        editingId === board.id ? (
          <div
            key={board.id}
            className="flex items-center gap-1 rounded-full border border-[var(--primary-blue)] bg-white px-2 py-1"
          >
            <input
              autoFocus
              value={editingName}
              onChange={(event) => setEditingName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") commitEdit();
                if (event.key === "Escape") setEditingId(null);
              }}
              className="w-28 bg-transparent text-xs font-semibold text-[var(--navy-dark)] outline-none"
            />
            <button type="button" onClick={commitEdit} aria-label="Save board name">
              <Check size={13} className="text-[var(--primary-blue)]" />
            </button>
            <button type="button" onClick={() => setEditingId(null)} aria-label="Cancel rename">
              <X size={13} className="text-[var(--gray-text)]" />
            </button>
          </div>
        ) : (
          <div
            key={board.id}
            className={`group flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
              board.id === selectedBoardId
                ? "border-[var(--primary-blue)] bg-[var(--primary-blue)] text-white"
                : "border-[var(--stroke)] bg-white text-[var(--navy-dark)] hover:border-[var(--primary-blue)]"
            }`}
          >
            <button type="button" onClick={() => onSelect(board.id)}>
              {board.name}
            </button>
            <button
              type="button"
              onClick={() => startEditing(board)}
              aria-label={`Rename ${board.name}`}
              className="opacity-60 hover:opacity-100"
            >
              <Pencil size={11} />
            </button>
            {boards.length > 1 ? (
              <button
                type="button"
                onClick={() => onDelete(board.id)}
                aria-label={`Delete ${board.name}`}
                className="opacity-60 hover:opacity-100"
              >
                <Trash2 size={11} />
              </button>
            ) : null}
          </div>
        )
      )}

      {isCreating ? (
        <div className="flex items-center gap-1 rounded-full border border-[var(--primary-blue)] bg-white px-2 py-1">
          <input
            autoFocus
            value={newBoardName}
            onChange={(event) => setNewBoardName(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") commitCreate();
              if (event.key === "Escape") setIsCreating(false);
            }}
            placeholder="Board name"
            className="w-28 bg-transparent text-xs font-semibold text-[var(--navy-dark)] outline-none"
          />
          <button type="button" onClick={commitCreate} aria-label="Create board">
            <Check size={13} className="text-[var(--primary-blue)]" />
          </button>
          <button type="button" onClick={() => setIsCreating(false)} aria-label="Cancel new board">
            <X size={13} className="text-[var(--gray-text)]" />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-1 rounded-full border border-dashed border-[var(--stroke)] px-3 py-1.5 text-xs font-semibold text-[var(--gray-text)] hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
        >
          <Plus size={12} />
          New board
        </button>
      )}
    </div>
  );
};
