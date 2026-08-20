import { useState } from "react";
import type { CatalogEpisode, LanguageCode } from "../types/catalog";
import { SafeImage } from "./SafeImage";

function formatDuration(seconds: number | null): string {
  if (!seconds) return "";
  const mins = Math.round(seconds / 60);
  return `${mins} min`;
}

export function EpisodeRow({ episode }: { episode: CatalogEpisode }) {
  const [lang, setLang] = useState<LanguageCode>(episode.languages[0]);
  const title = episode.titles_by_language[lang] ?? episode.title;
  const hasMultipleLanguages = episode.languages.length > 1;

  return (
    <div className="episode-row">
      <SafeImage
        src={episode.artwork.thumbnail?.url}
        alt={title}
        aspectRatio="16 / 9"
        className="episode-row__art"
      />
      <div className="episode-row__body">
        <div className="episode-row__top">
          <span className="episode-row__number">
            {episode.episode_number != null ? `E${episode.episode_number}` : ""}
          </span>
          <h3 className="episode-row__title">{title}</h3>
          {episode.duration_seconds != null && (
            <span className="episode-row__duration">{formatDuration(episode.duration_seconds)}</span>
          )}
        </div>
        <p className="episode-row__synopsis">{episode.synopsis}</p>

        {hasMultipleLanguages && (
          <div className="lang-switcher" role="tablist" aria-label="Language">
            {episode.languages.map((code) => (
              <button
                key={code}
                role="tab"
                aria-selected={lang === code}
                className={`lang-switcher__tab ${lang === code ? "lang-switcher__tab--active" : ""}`}
                onClick={() => setLang(code)}
              >
                {code.toUpperCase()}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
