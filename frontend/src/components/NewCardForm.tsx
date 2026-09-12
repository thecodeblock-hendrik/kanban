import { useState, type FormEvent } from "react";
import { Plus, X } from "lucide-react";

const initialFormState = { title: "", details: "" };

type NewCardFormProps = {
  onAdd: (title: string, details: string) => void;
};

export const NewCardForm = ({ onAdd }: NewCardFormProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [formState, setFormState] = useState(initialFormState);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.title.trim()) {
      return;
    }
    onAdd(formState.title.trim(), formState.details.trim());
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
