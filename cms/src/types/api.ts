// Types mirroring docs/API_CONTRACT.md

export type Role = 'editor' | 'admin';
export type ShowStatus = 'draft' | 'published' | 'archived';
export type ArtworkKind = 'poster' | 'banner' | 'thumbnail';

export interface ApiErrorDetail {
  code: string;
  field?: string;
  message: string;
  hint?: string;
  resource?: { type: string; id: number | null; title?: string };
  related?: { type: string; id: number; title?: string }[];
}

export interface ApiErrorBody {
  error: {
    type:
      | 'validation_error'
      | 'not_found'
      | 'conflict'
      | 'unauthorized'
      | 'forbidden'
      | 'payload_too_large'
      | 'internal_error';
    message: string;
    request_id: string;
    details: ApiErrorDetail[];
  };
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Artwork {
  id: number;
  episode_id?: number;
  show_id?: number;
  kind: ArtworkKind;
  url: string;
  width: number;
  height: number;
  aspect_ratio?: string;
  file_size_bytes: number;
  mime_type: string;
  alt_text?: string | null;
  created_at?: string;
}

export interface Show {
  id: number;
  slug: string;
  title: string;
  description: string;
  category: string;
  section: string | null;
  status: ShowStatus;
  artwork: Artwork[];
  season_count: number;
  episode_count: number;
  trailer_count: number;
  created_at: string;
  updated_at: string;
  seasons?: Season[];
}

export interface Season {
  id: number;
  show_id: number;
  season_number: number;
  title: string;
  is_trailer_season: boolean;
  episode_count: number;
}

export interface Episode {
  id: number;
  season_id: number;
  show_id: number;
  season_number: number;
  episode_number: number | null;
  title: string;
  synopsis: string;
  content_group: string;
  language: string;
  duration_seconds: number | null;
  status: ShowStatus;
  is_trailer: boolean;
  artwork: Artwork[];
  missing_artwork_kinds: ArtworkKind[];
  created_at: string;
  updated_at: string;
  variants?: { id: number; language: string; title: string; status: ShowStatus }[];
}

export interface User {
  id: number;
  email: string;
  name: string;
  role: Role;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface ValidationIssue {
  code: string;
  severity: 'blocking' | 'warning';
  message: string;
  hint?: string;
  resource?: { type: string; id: number; title?: string; [k: string]: unknown };
  related?: { type: string; id: number; title?: string }[];
  field?: string;
}

export interface ValidationReportByShow {
  show: { id: number; slug: string; title: string; status: ShowStatus; section: string | null };
  blocking_count: number;
  warning_count: number;
  issues: ValidationIssue[];
}

export interface ValidationReport {
  generated_at: string;
  publishable: boolean;
  summary: {
    blocking_issues: number;
    warnings: number;
    shows_affected: number;
    shows_total: number;
    by_type: Record<string, number>;
  };
  by_show: ValidationReportByShow[];
}

export interface PublishRun {
  run_id: string;
  status: 'success' | 'success_with_warnings' | 'blocked';
  version: number | null;
  published_at: string;
  published_by: { id: number; email: string };
  counts?: Record<string, unknown>;
  warning_count?: number;
  duration_ms?: number;
  note?: string | null;
}
