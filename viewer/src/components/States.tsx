export function CatalogSkeleton() {
  return (
    <div className="skeleton-page" aria-busy="true" aria-label="Loading catalogue">
      <div className="skeleton hero-skeleton" style={{ aspectRatio: "16 / 9" }} />
      {[0, 1, 2].map((row) => (
        <div key={row} className="skeleton-row">
          <div className="skeleton skeleton-row__title" />
          <div className="skeleton-row__cards">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="skeleton skeleton-card" style={{ aspectRatio: "2 / 3" }} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function CatalogError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="state-panel state-panel--error">
      <span className="state-panel__icon">⚠️</span>
      <h2>We couldn't load the catalogue</h2>
      <p>{message}</p>
      <button className="button" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}

export function EmptySearchState({ query }: { query: string }) {
  return (
    <div className="state-panel state-panel--empty">
      <span className="state-panel__icon">🔍</span>
      <h2>No matches{query ? ` for "${query}"` : ""}</h2>
      <p>Try a different search term, or clear the category/language filters.</p>
    </div>
  );
}
