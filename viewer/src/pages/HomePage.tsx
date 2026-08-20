import { useCatalog } from "../hooks/useCatalog";
import { Hero } from "../components/Hero";
import { ShowRow } from "../components/ShowRow";
import { CatalogSkeleton, CatalogError } from "../components/States";

export function HomePage() {
  const { data, isLoading, isError, error, refetch } = useCatalog();

  if (isLoading) return <CatalogSkeleton />;

  if (isError) {
    return (
      <CatalogError
        message={error instanceof Error ? error.message : "Unknown error."}
        onRetry={() => refetch()}
      />
    );
  }

  if (!data) return null;

  const sections = [...data.sections].sort((a, b) => a.sort_order - b.sort_order);
  const allShows = sections.flatMap((s) => s.shows);

  // Featured hero: the first show of the highest-priority section that has
  // artwork. A real product would likely have an editorial "featured" flag;
  // the catalogue contract doesn't expose one, so we fall back to "first
  // show in nav order" as a reasonable, deterministic default.
  const featured = allShows.find((s) => s.artwork.banner) ?? allShows[0];

  return (
    <div className="home-page">
      {featured && <Hero show={featured} />}
      <div className="home-page__rows">
        {sections.map((section) => (
          <ShowRow key={section.key} title={section.label} shows={section.shows} />
        ))}
      </div>
    </div>
  );
}
