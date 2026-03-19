import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

// Shared query keys for consistent caching across components
export const queryKeys = {
  trends: (period?: string) => ["trends", period ?? "24h"] as const,
  stats: () => ["platform-stats"] as const,
  bars: () => ["all-bars"] as const,
  bar: (slug: string) => ["bar", slug] as const,
  barPosts: (slug: string, ...filters: unknown[]) =>
    ["bar-posts", slug, ...filters] as const,
  barMembers: (slug: string) => ["bar-members", slug] as const,
  search: (query: string, ...filters: unknown[]) =>
    ["search", query, ...filters] as const,
  suggest: (query: string, ...filters: unknown[]) =>
    ["suggest", query, ...filters] as const,
  configs: () => ["configs"] as const,
};

// Cache time presets (in milliseconds)
const CACHE = {
  SHORT: 30 * 1000, // 30 seconds - for fast-changing data (stats)
  MEDIUM: 2 * 60 * 1000, // 2 minutes - for moderately changing data
  LONG: 5 * 60 * 1000, // 5 minutes - for stable data (bar info, configs)
  VERY_LONG: 15 * 60 * 1000, // 15 minutes - for rarely changing data
};

export function useTrends(period = "24h") {
  return useQuery({
    queryKey: queryKeys.trends(period),
    queryFn: () =>
      api
        .get<any>(`/trends`, { params: { period } })
        .then((res) => res.data || {}),
    staleTime: CACHE.MEDIUM,
    gcTime: CACHE.LONG,
  });
}

export function usePlatformStats() {
  return useQuery({
    queryKey: queryKeys.stats(),
    queryFn: () => api.get<any>("/stats").then((res) => res.data || {}),
    staleTime: CACHE.SHORT,
    gcTime: CACHE.MEDIUM,
    refetchInterval: 30_000,
  });
}

export function useBars() {
  return useQuery({
    queryKey: queryKeys.bars(),
    queryFn: () => api.get<any[]>("/bars"),
    staleTime: CACHE.LONG,
    gcTime: CACHE.VERY_LONG,
  });
}

export function useBar(slug: string | undefined) {
  return useQuery({
    queryKey: queryKeys.bar(slug!),
    queryFn: () => api.get<any>(`/bars/${slug}`).then((res) => res.data || {}),
    enabled: !!slug,
    staleTime: CACHE.LONG,
    gcTime: CACHE.VERY_LONG,
  });
}

export function useBarMembers(slug: string | undefined) {
  return useQuery({
    queryKey: queryKeys.barMembers(slug!),
    queryFn: () =>
      api.get<any[]>(`/bars/${slug}/members`).then((res) => res.data || []),
    enabled: !!slug,
    staleTime: CACHE.MEDIUM,
    gcTime: CACHE.LONG,
  });
}

export function usePublicConfigs() {
  return useQuery({
    queryKey: queryKeys.configs(),
    queryFn: () => api.get<any>("/configs").then((res) => res.data || {}),
    staleTime: CACHE.VERY_LONG,
    gcTime: CACHE.VERY_LONG,
  });
}
