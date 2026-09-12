import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { LayoutGrid } from "lucide-react";
import type { Card, Column } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
};

export const KanbanColumn = ({
  column,
  cards,
  onRename,
  onAddCard,
  onDeleteCard,
}: KanbanColumnProps) => {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
    data: { type: "column", columnId: column.id },
  });

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[420px] w-full min-w-0 flex-col rounded-2xl border border-[var(--stroke)] bg-[var(--surface-strong)] p-3.5 shadow-[var(--shadow)] transition",
        isOver && "ring-2 ring-[var(--accent-yellow)]"
      )}
      data-testid={`column-${column.id}`}
    >
      <div className="flex items-center gap-2 px-0.5">
        <input
          value={column.title}
          onChange={(event) => onRename(column.id, event.target.value)}
          className="w-full min-w-0 truncate bg-transparent font-display text-[15px] font-semibold text-[var(--navy-dark)] outline-none"
          aria-label="Column title"
        />
        <span className="flex shrink-0 items-center gap-1 rounded-full bg-[var(--surface)] px-2 py-0.5 text-[11px] font-semibold text-[var(--gray-text)]">
          <LayoutGrid size={11} strokeWidth={2.5} />
          {cards.length}
        </span>
      </div>
      <div className="mt-3 flex flex-1 flex-col gap-2 overflow-y-auto">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-[var(--stroke)] px-3 py-6 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Drop a card here
          </div>
        )}
      </div>
      <NewCardForm
        onAdd={(title, details) => onAddCard(column.id, title, details)}
      />
    </section>
  );
};
