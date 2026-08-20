import { Link } from "react-router-dom";
import type { CatalogShow } from "../types/catalog";
import { SafeImage } from "./SafeImage";

export function ShowCard({ show }: { show: CatalogShow }) {
  return (
    <Link to={`/shows/${show.slug}`} className="show-card">
      <SafeImage
        src={show.artwork.poster?.url}
        alt={show.title}
        aspectRatio="2 / 3"
        className="show-card__art"
      />
      <div className="show-card__title">{show.title}</div>
    </Link>
  );
}
