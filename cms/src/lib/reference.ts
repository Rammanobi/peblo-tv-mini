import referenceJson from '../reference.json';

export interface ReferenceData {
  sections: { key: string; label: string; show_in_nav: boolean; sort_order: number }[];
  categories: { key: string; label: string }[];
  languages: { code: string; label: string; is_default: boolean }[];
  statuses: { key: string; label: string; publishable: boolean }[];
  artwork: {
    max_file_size_bytes: number;
    max_file_size_human: string;
    allowed_mime_types: string[];
    aspect_ratio_tolerance: number;
    required_kinds_per_episode: string[];
    required_kinds_per_show: string[];
    specs: {
      kind: string;
      aspect_ratio: string;
      aspect_ratio_value: number;
      width: number;
      height: number;
      max_bytes: number;
      usage: string;
    }[];
  };
}

export const reference = referenceJson as ReferenceData;

export const artworkSpecByKind = Object.fromEntries(
  reference.artwork.specs.map((s) => [s.kind, s])
) as Record<string, ReferenceData['artwork']['specs'][number]>;

export function labelFor(list: { key?: string; code?: string; label: string }[], key: string | null | undefined) {
  if (!key) return '—';
  const found = list.find((item) => (item.key ?? item.code) === key);
  return found?.label ?? key;
}
