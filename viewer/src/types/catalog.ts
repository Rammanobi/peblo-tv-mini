// Types mirror docs/API_CONTRACT.md section 8 (Catalogue) exactly.
// The Viewer only ever talks to GET /catalog and GET /catalog/search.

export type LanguageCode = "en" | "hi" | "es";

export type CategoryKey =
  | "comedy"
  | "adventure"
  | "educational"
  | "music"
  | "fantasy"
  | "nature";

export type SectionKey = "kids" | "family" | "originals" | "learning";

export interface ArtworkImage {
  url: string;
  width: number;
  height: number;
}

export interface EpisodeArtwork {
  poster?: ArtworkImage;
  banner?: ArtworkImage;
  thumbnail?: ArtworkImage;
}

export interface ShowArtwork {
  poster?: ArtworkImage;
  banner?: ArtworkImage;
}

export interface CatalogEpisode {
  content_group: string;
  episode_number: number | null;
  title: string;
  synopsis: string;
  duration_seconds: number | null;
  languages: LanguageCode[]; // collapsed language variants, default first
  titles_by_language: Record<string, string>;
  artwork: EpisodeArtwork;
}

export interface CatalogTrailer {
  content_group: string;
  title: string;
  duration_seconds: number | null;
  languages: LanguageCode[];
  artwork: EpisodeArtwork;
}

export interface CatalogSeason {
  season_number: number; // always >= 1 in this array
  title: string;
  episode_count: number;
  episodes: CatalogEpisode[];
}

export interface CatalogShow {
  id: number;
  slug: string;
  title: string;
  description: string;
  category: CategoryKey;
  category_label: string;
  languages: LanguageCode[];
  artwork: ShowArtwork;
  seasons: CatalogSeason[]; // season 0 never appears here
  trailers: CatalogTrailer[]; // season 0 surfaces only here
}

export interface CatalogSection {
  key: SectionKey;
  label: string;
  sort_order: number;
  shows: CatalogShow[];
}

export interface Catalog {
  catalog_version: number;
  generated_at: string;
  reference_version: string;
  languages: LanguageCode[];
  sections: CatalogSection[];
}

// GET /catalog/search response shapes

export interface SearchResultShowRef {
  id: number;
  slug: string;
  title: string;
  section: SectionKey;
  category: CategoryKey;
}

export interface SearchResult {
  type: "show" | "episode";
  content_group?: string;
  title: string;
  synopsis?: string;
  duration_seconds?: number | null;
  languages: LanguageCode[];
  season_number?: number;
  episode_number?: number | null;
  show: SearchResultShowRef;
  artwork: EpisodeArtwork | ShowArtwork;
  matched_on: string[];
}

export interface SearchResponse {
  query: {
    q: string | null;
    category: CategoryKey | null;
    language: LanguageCode | null;
    section: SectionKey | null;
  };
  catalog_version: number;
  total: number;
  limit: number;
  offset: number;
  results: SearchResult[];
}

// data/reference.json shapes (used for filter option lists)

export interface ReferenceCategory {
  key: CategoryKey;
  label: string;
}

export interface ReferenceLanguage {
  code: LanguageCode;
  label: string;
  is_default: boolean;
}

export interface ReferenceSection {
  key: SectionKey | "trailers";
  label: string;
  description: string;
  show_in_nav: boolean;
  sort_order: number;
}

export interface Reference {
  reference_version: string;
  categories: ReferenceCategory[];
  languages: ReferenceLanguage[];
  sections: ReferenceSection[];
}
