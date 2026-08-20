import { apiDelete, apiGet, apiPatch, apiPost, http } from './client';
import type {
  Episode,
  LoginResponse,
  Paginated,
  PublishRun,
  Season,
  Show,
  User,
  ValidationReport,
  Artwork,
} from '../types/api';

// --- Auth ---
export const login = (email: string, password: string) =>
  apiPost<LoginResponse>('/auth/login', { email, password });

export const getMe = () => apiGet<User>('/auth/me');

// --- Shows ---
export interface ShowFilters {
  status?: string;
  section?: string;
  category?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export const listShows = (filters: ShowFilters) =>
  apiGet<Paginated<Show>>('/shows', { params: filters });

export const getShow = (id: number) => apiGet<Show>(`/shows/${id}`);

export const createShow = (payload: Partial<Show>) => apiPost<Show>('/shows', payload);

export const updateShow = (id: number, payload: Partial<Show>) =>
  apiPatch<Show>(`/shows/${id}`, payload);

export const deleteShow = (id: number) => apiDelete<void>(`/shows/${id}`);

// --- Seasons ---
export const listSeasons = (showId: number, includeTrailers = true) =>
  apiGet<Paginated<Season>>(`/shows/${showId}/seasons`, {
    params: { include_trailers: includeTrailers },
  });

export const createSeason = (showId: number, payload: { season_number: number; title: string }) =>
  apiPost<Season>(`/shows/${showId}/seasons`, payload);

export const updateSeason = (id: number, payload: { title: string }) =>
  apiPatch<Season>(`/seasons/${id}`, payload);

export const deleteSeason = (id: number) => apiDelete<void>(`/seasons/${id}`);

// --- Episodes ---
export interface EpisodeFilters {
  language?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export const listEpisodes = (seasonId: number, filters: EpisodeFilters = {}) =>
  apiGet<Paginated<Episode>>(`/seasons/${seasonId}/episodes`, { params: filters });

export const getEpisode = (id: number) => apiGet<Episode>(`/episodes/${id}`);

export const createEpisode = (seasonId: number, payload: Partial<Episode>) =>
  apiPost<Episode>(`/seasons/${seasonId}/episodes`, payload);

export const updateEpisode = (id: number, payload: Partial<Episode>) =>
  apiPatch<Episode>(`/episodes/${id}`, payload);

export const deleteEpisode = (id: number) => apiDelete<void>(`/episodes/${id}`);

// --- Artwork ---
export const listEpisodeArtwork = (episodeId: number) =>
  apiGet<{ items: Artwork[]; missing_kinds: string[] }>(`/episodes/${episodeId}/artwork`);

export const uploadEpisodeArtwork = async (
  episodeId: number,
  kind: string,
  file: File,
  altText?: string
) => {
  const form = new FormData();
  form.append('kind', kind);
  form.append('file', file);
  if (altText) form.append('alt_text', altText);
  const res = await http.post<Artwork>(`/episodes/${episodeId}/artwork`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const listShowArtwork = (showId: number) =>
  apiGet<{ items: Artwork[]; missing_kinds: string[] }>(`/shows/${showId}/artwork`);

export const uploadShowArtwork = async (
  showId: number,
  kind: string,
  file: File,
  altText?: string
) => {
  const form = new FormData();
  form.append('kind', kind);
  form.append('file', file);
  if (altText) form.append('alt_text', altText);
  const res = await http.post<Artwork>(`/shows/${showId}/artwork`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const deleteArtwork = (artworkId: number) => apiDelete<void>(`/artwork/${artworkId}`);

// --- Publishing ---
export const getValidationReport = (params?: { show_id?: number; severity?: string }) =>
  apiGet<ValidationReport>('/admin/validation-report', { params });

export const publishCatalog = (payload?: { dry_run?: boolean; note?: string }) =>
  apiPost<Record<string, unknown>>('/admin/catalog/publish', payload ?? {});

export const getPublishRuns = (limit = 50, offset = 0) =>
  apiGet<Paginated<PublishRun>>('/admin/catalog/publish-runs', { params: { limit, offset } });
