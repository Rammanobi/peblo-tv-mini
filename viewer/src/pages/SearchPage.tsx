import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useCatalog } from "../hooks/useCatalog";
import { CatalogSkeleton, CatalogError, EmptySearchState } from "../components/States";
import { SafeImage } from "../components/SafeImage";
import referenceData from "../reference.json";
import type { CategoryKey, LanguageCode, Reference } from "../types/catalog";

const reference = referenceData as Reference;

interface FlatResult {
  key: string;
  type: "show" | "episode";
  title: string;
  synopsis: string;
  showTitle: string;
  showSlug: string;
  category: CategoryKey;
  languages: LanguageCode[];
  thumbUrl?: string;
}

export function SearchPage() {
  const { data, isLoading, isError, error, refetch } = useCatalog();
  const [q, setQ] = useState("");
  const [category, setCategory] = useState<string>("");
  const [language, setLanguage] = useState<string>("");

  // The full catalogue is a small, static, already-fetched payload (it only
  // changes on publish). Filtering it client-side avoids a network
  // round-trip per keystroke, which is the right tradeoff at this scale.
  // GET /catalog/search exists and would be the better choice once the
  // catalogue is large enough that shipping it all to the client stops
  // being cheap (see src/api/client.ts:fetchCatalogSearch).
  const flatItems: FlatResult[] = useMemo(() => {
    if (!data) return [];
    const items: FlatResult[] = [];
    for (const section of data.sections) {
      for (const show of section.shows) {
        items.push({
          key: `show-${show.id}`,
          type: "show",
          title: show.title,
          synopsis: show.description,
          showTitle: show.title,
          showSlug: show.slug,
          category: show.category,
          languages: show.languages,
          thumbUrl: show.artwork.poster?.url,
        });
        for (const season of show.seasons) {
          for (const ep of season.episodes) {
            items.push({
              key: `ep-${ep.content_group}`,
              type: "episode",
              title: ep.title,
              synopsis: ep.synopsis,
              showTitle: show.title,
              showSlug: show.slug,
              category: show.category,
              languages: ep.languages,
              thumbUrl: ep.artwork.thumbnail?.url,
            });
          }
        }
      }
    }
    return items;
  }, [data]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return flatItems.filter((item) => {
      if (category && item.category !== category) return false;
      if (language && !item.languages.includes(language as LanguageCode)) return false;
      if (needle) {
        const haystack = `${item.title} ${item.synopsis} ${item.showTitle}`.toLowerCase();
        if (!haystack.includes(needle)) return false;
      }
      return true;
    });
  }, [flatItems, q, category, language]);

  if (isLoading) return <CatalogSkeleton />;
  if (isError) {
    return (
      <CatalogError
        message={error instanceof Error ? error.message : "Unknown error."}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="search-page">
      <div className="search-page__controls">
        <input
          type="search"
          className="search-page__input"
          placeholder="Search shows and episodes..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search"
        />
        <select
          className="search-page__select"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label="Filter by category"
        >
          <option value="">All categories</option>
          {reference.categories.map((c) => (
            <option key={c.key} value={c.key}>
              {c.label}
            </option>
          ))}
        </select>
        <select
          className="search-page__select"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          aria-label="Filter by language"
        >
          <option value="">All languages</option>
          {reference.languages.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptySearchState query={q} />
      ) : (
        <div className="search-page__grid">
          {filtered.map((item) => (
            <Link key={item.key} to={`/shows/${item.showSlug}`} className="search-result">
              <SafeImage
                src={item.thumbUrl}
                alt={item.title}
                aspectRatio={item.type === "show" ? "2 / 3" : "16 / 9"}
                className="search-result__art"
              />
              <div className="search-result__meta">
                <div className="search-result__title">{item.title}</div>
                {item.type === "episode" && (
                  <div className="search-result__show">{item.showTitle}</div>
                )}
                <div className="search-result__badge">{item.type === "show" ? "Show" : "Episode"}</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
