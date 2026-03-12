"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { SavedDashboard } from "@/lib/types";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useDashboards() {
  return useSWR<SavedDashboard[]>("/api/dashboards", fetcher<SavedDashboard[]>);
}

export function usePinnedDashboards() {
  const { data, ...rest } = useSWR<SavedDashboard[]>("/api/dashboards", fetcher<SavedDashboard[]>);
  return { data: data?.filter((d) => d.is_pinned) ?? [], ...rest };
}

export function useDashboard(id: number | null) {
  return useSWR<SavedDashboard>(
    id != null ? `/api/dashboards/${id}` : null,
    fetcher<SavedDashboard>,
  );
}
