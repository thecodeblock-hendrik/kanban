import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import { Calendar, Trash2 } from "lucide-react";
import { isOverdue, type Card, type Priority } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
};

const PRIORITY_STYLES: Record<Priority, string> = {
  low: "bg-[var(--surface)] text-[var(--gray-text)]",
  medium: "bg-[var(--primary-blue)]/10 text-[var(--primary-blue)]",
  high: "bg-[var(--accent-yellow)]/20 text-[#946200]",
};

export const KanbanCard = ({ card, onDelete }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const priority = card.priority ?? "medium";
  const overdue = isOverdue(card);

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "group rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3.5 shadow-[0_8px_18px_rgba(3,33,71,0.06)]",
        "transition-all duration-150 hover:-translate-y-0.5 hover:border-[var(--primary-blue)]/30 hover:shadow-[0_14px_28px_rgba(3,33,71,0.12)]",
        "cursor-grab active:cursor-grabbing",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="font-display text-[15px] font-semibold leading-tight text-[var(--navy-dark)]">
          {card.title}
        </h4>
        <button
          type="button"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={() => onDelete(card.id)}
          className="-mr-1 -mt-1 shrink-0 rounded-full p-1.5 text-[var(--gray-text)] opacity-0 transition hover:bg-red-50 hover:text-red-600 focus-visible:opacity-100 group-hover:opacity-100"
          aria-label={`Delete ${card.title}`}
          title="Delete card"
        >
          <Trash2 size={14} strokeWidth={2} />
        </button>
      </div>
      {card.details ? (
        <p className="mt-1.5 line-clamp-3 text-sm leading-6 text-[var(--gray-text)]">
          {card.details}
        </p>
      ) : null}
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        <span
          className={clsx(
            "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
            PRIORITY_STYLES[priority]
          )}
        >
          {priority}
        </span>
        {card.dueDate ? (
          <span
            className={clsx(
              "flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold",
              overdue ? "bg-red-50 text-red-600" : "bg-[var(--surface)] text-[var(--gray-text)]"
            )}
          >
            <Calendar size={10} strokeWidth={2.5} />
            {card.dueDate}
            {overdue ? " (overdue)" : ""}
          </span>
        ) : null}
      </div>
    </article>
  );
};
