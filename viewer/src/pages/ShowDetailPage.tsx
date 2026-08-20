import { useParams, Link } from "react-router-dom";
import { useCatalog } from "../hooks/useCatalog";
import { CatalogSkeleton, CatalogError } from "../components/States";
import { SafeImage } from "../components/SafeImage";
import { EpisodeRow } from "../components/EpisodeRow";
import { TrailerRow } from "../components/TrailerRow";

export function ShowDetailPage() {
  const { slug } = useParams<{ slug: string }>();
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

  const show = data.sections.flatMap((s) => s.shows).find((s) => s.slug === slug);

  if (!show) {
    return (
      <div className="state-panel state-panel--empty">
        <span className="state-panel__icon">🤷</span>
        <h2>Show not found</h2>
        <p>We couldn't find that show in the published catalogue.</p>
        <Link to="/" className="button">
          Back home
        </Link>
      </div>
    );
  }

  return (
    <div className="show-detail">
      <div className="show-detail__hero" style={{ aspectRatio: "16 / 9" }}>
        {show.artwork.banner?.url ? (
          <img
            src={show.artwork.banner.url}
            alt={show.title}
            className="show-detail__hero-img"
            loading="eager"
          />
        ) : (
          <div className="show-detail__hero-img show-detail__hero-img--fallback" />
        )}
        <div className="hero__scrim" />
      </div>

      <div className="show-detail__body">
        <div className="show-detail__poster-col">
          <SafeImage
            src={show.artwork.poster?.url}
            alt={show.title}
            aspectRatio="2 / 3"
            className="show-detail__poster"
          />
        </div>
        <div className="show-detail__info">
          <span className="hero__badge">{show.category_label}</span>
          <h1 className="show-detail__title">{show.title}</h1>
          <p className="show-detail__synopsis">{show.description}</p>
          <div className="show-detail__languages">
            {show.languages.map((l) => (
              <span key={l} className="pill">
                {l.toUpperCase()}
              </span>
            ))}
          </div>
        </div>
      </div>

      {show.seasons.map((season) => (
        <section key={season.season_number} className="season-block">
          <h2 className="season-block__title">{season.title}</h2>
          <div className="season-block__episodes">
            {season.episodes.map((ep) => (
              <EpisodeRow key={ep.content_group} episode={ep} />
            ))}
          </div>
        </section>
      ))}

      {show.trailers.length > 0 && (
        <section className="season-block season-block--trailers">
          <h2 className="season-block__title">Trailers</h2>
          <div className="season-block__episodes">
            {show.trailers.map((t) => (
              <TrailerRow key={t.content_group} trailer={t} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
