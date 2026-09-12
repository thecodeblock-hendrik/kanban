import type { Card } from "@/lib/kanban";

type KanbanCardPreviewProps = {
  card: Card;
};

export const KanbanCardPreview = ({ card }: KanbanCardPreviewProps) => (
  <article className="rotate-[1.5deg] rounded-2xl border border-[var(--primary-blue)]/30 bg-white px-4 py-3.5 shadow-[0_18px_32px_rgba(3,33,71,0.18)]">
    <h4 className="font-display text-[15px] font-semibold leading-tight text-[var(--navy-dark)]">
      {card.title}
    </h4>
    {card.details ? (
      <p className="mt-1.5 line-clamp-3 text-sm leading-6 text-[var(--gray-text)]">
        {card.details}
      </p>
    ) : null}
  </article>
);
