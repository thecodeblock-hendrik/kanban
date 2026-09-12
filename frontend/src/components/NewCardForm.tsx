import { useState, type FormEvent } from "react";
import { Plus, X } from "lucide-react";
import type { Priority } from "@/lib/kanban";

const initialFormState = { title: "", details: "", dueDate: "", priority: "medium" as Priority };

type NewCardFormProps = {
  onAdd: (title: string, details: string, priority: Priority, dueDate: string | null) => void;
};

export const NewCardForm = ({ onAdd }: NewCardFormProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [formState, setFormState] = useState(initialFormState);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.title.trim()) {
      return;
    }
    onAdd(
      formState.title.trim(),
      formState.details.trim(),
      formState.priority,
      formState.dueDate || null
    );
    setFormState(initialFormState);
    setIsOpen(false);
  };

  return (
    <div className="mt-3">
      {isOpen ? (
        <form onSubmit={handleSubmit} className="space-y-2 rounded-xl border border-[var(--stroke)] bg-white p-3">
          <input
            value={formState.title}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, title: event.target.value }))
            }
            placeholder="Card title"
            autoFocus
            className="w-full rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
            required
          />
          <textarea
            value={formState.details}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, details: event.target.value }))
            }
            placeholder="Details (optional)"
            rows={2}
            className="w-full resize-none rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--gray-text)] outline-none transition focus:border-[var(--primary-blue)]"
          />
          <div className="flex items-center gap-2">
            <label className="flex-1 text-xs font-medium text-[var(--gray-text)]">
              Due date
              <input
                type="date"
                value={formState.dueDate}
                onChange={(event) =>
                  setFormState((prev) => ({ ...prev, dueDate: event.target.value }))
                }
                className="mt-1 w-full rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-2 py-1.5 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              />
            </label>
            <label className="flex-1 text-xs font-medium text-[var(--gray-text)]">
              Priority
              <select
                value={formState.priority}
                onChange={(event) =>
                  setFormState((prev) => ({ ...prev, priority: event.target.value as Priority }))
                }
                className="mt-1 w-full rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-2 py-1.5 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
          </div>
          <div className="flex items-center gap-2 pt-0.5">
            <button
              type="submit"
              className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--secondary-purple)] px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-110"
            >
              <Plus size={14} strokeWidth={2.5} />
              Add card
            </button>
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                setFormState(initialFormState);
              }}
              aria-label="Cancel"
              title="Cancel"
              className="inline-flex items-center justify-center rounded-lg border border-[var(--stroke)] p-1.5 text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
            >
              <X size={14} strokeWidth={2.5} />
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)] hover:bg-[var(--primary-blue)]/5"
        >
          <Plus size={14} strokeWidth={2.5} />
          Add a card
        </button>
      )}
    </div>
  );
};
