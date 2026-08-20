import type { CatalogTrailer } from "../types/catalog";
import { SafeImage } from "./SafeImage";

function formatDuration(seconds: number | null): string {
  if (!seconds) return "";
  const mins = Math.round(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

export function TrailerRow({ trailer }: { trailer: CatalogTrailer }) {
  return (
    <div className="episode-row episode-row--trailer">
      <SafeImage
        src={trailer.artwork.thumbnail?.url}
        alt={trailer.title}
        aspectRatio="16 / 9"
        className="episode-row__art"
      />
      <div className="episode-row__body">
        <div className="episode-row__top">
          <h3 className="episode-row__title">{trailer.title}</h3>
          {trailer.duration_seconds != null && (
            <span className="episode-row__duration">{formatDuration(trailer.duration_seconds)}</span>
          )}
        </div>
        {trailer.languages.length > 1 && (
          <div className="lang-switcher lang-switcher--static">
            {trailer.languages.map((code) => (
              <span key={code} className="lang-switcher__tab">
                {code.toUpperCase()}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
