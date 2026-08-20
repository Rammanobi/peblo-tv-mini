import type { CatalogShow } from "../types/catalog";
import { ShowCard } from "./ShowCard";

export function ShowRow({
  title,
  shows,
}: {
  title: string;
  shows: CatalogShow[];
}) {
  if (shows.length === 0) return null;
  return (
    <section className="show-row">
      <h2 className="show-row__title">{title}</h2>
      <div className="show-row__scroller">
        {shows.map((show) => (
          <ShowCard key={show.id} show={show} />
        ))}
      </div>
    </section>
  );
}
