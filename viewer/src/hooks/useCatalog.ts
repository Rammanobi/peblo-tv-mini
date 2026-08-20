import { useQuery } from "@tanstack/react-query";
import { fetchCatalog } from "../api/client";

// The published catalogue is a static artifact (it only changes when an
// admin publishes). We fetch it once and cache it aggressively — there is
// no reason to refetch per navigation or per keystroke.
const STALE_TIME_MS = 5 * 60 * 1000; // 5 minutes
const GC_TIME_MS = 30 * 60 * 1000; // 30 minutes

export function useCatalog() {
  return useQuery({
    queryKey: ["catalog"],
    queryFn: fetchCatalog,
    staleTime: STALE_TIME_MS,
    gcTime: GC_TIME_MS,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
