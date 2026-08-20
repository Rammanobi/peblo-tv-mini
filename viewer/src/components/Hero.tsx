import { Link } from "react-router-dom";
import { useEffect } from "react";
import type { CatalogShow } from "../types/catalog";

export function Hero({ show }: { show: CatalogShow }) {
  const bannerUrl = show.artwork.banner?.url;

  // Preload the hero image since it's above the fold and should render
  // as fast as possible (no lazy loading, no skeleton flash).
  useEffect(() => {
    if (!bannerUrl) return;
    const link = document.createElement("link");
    link.rel = "preload";
    link.as = "image";
    link.href = bannerUrl;
    document.head.appendChild(link);
    return () => {
      document.head.removeChild(link);
    };
  }, [bannerUrl]);

  return (
    <section className="hero" style={{ aspectRatio: "16 / 9" }}>
      {bannerUrl ? (
        <img src={bannerUrl} alt={show.title} className="hero__img" loading="eager" fetchPriority="high" />
      ) : (
        <div className="hero__img hero__img--fallback" />
      )}
      <div className="hero__scrim" />
      <div className="hero__content">
        <span className="hero__badge">{show.category_label}</span>
        <h1 className="hero__title">{show.title}</h1>
        <p className="hero__description">{show.description}</p>
        <Link to={`/shows/${show.slug}`} className="hero__cta">
          View show
        </Link>
      </div>
    </section>
  );
}
