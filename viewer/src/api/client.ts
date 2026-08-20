import type { Catalog, SearchResponse } from "../types/catalog";

// Only the public catalogue endpoints are ever called from this app:
//   GET /catalog
//   GET /catalog/search
// Never any /admin/* or write endpoint — this is a read-only public Viewer.

const API_BASE =
  (import.meta.env.VITE_CATALOGUE_URL as string | undefined) ??
  (import.meta.env.VITE_API_URL as string | undefined) ??
  "http://localhost:4000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function parseErrorEnvelope(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (body?.error?.message) return body.error.message as string;
  } catch {
    // fall through to generic message
  }
  return `Request failed with status ${res.status}`;
}

export async function fetchCatalog(): Promise<Catalog> {
  const res = await fetch(`${API_BASE}/catalog`);
  if (!res.ok) {
    throw new ApiError(await parseErrorEnvelope(res), res.status);
  }
  return res.json() as Promise<Catalog>;
}

export interface SearchParams {
  q?: string;
  category?: string;
  language?: string;
  section?: string;
  limit?: number;
  offset?: number;
}

// Optional server-side search. The Home/Search page in this app performs
// client-side filtering over the already-fetched catalogue instead (see
// src/pages/SearchPage.tsx for the rationale), but this helper is provided
// for completeness / future use against larger catalogues.
export async function fetchCatalogSearch(
  params: SearchParams
): Promise<SearchResponse> {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.category) query.set("category", params.category);
  if (params.language) query.set("language", params.language);
  if (params.section) query.set("section", params.section);
  if (params.limit) query.set("limit", String(params.limit));
  if (params.offset) query.set("offset", String(params.offset));

  const res = await fetch(`${API_BASE}/catalog/search?${query.toString()}`);
  if (!res.ok) {
    throw new ApiError(await parseErrorEnvelope(res), res.status);
  }
  return res.json() as Promise<SearchResponse>;
}
