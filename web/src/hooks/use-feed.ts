"use client";

import { useCallback } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { InsightCard, BriefingResponse } from "@/lib/types";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useFeed(limit: number = 20) {
  const { data, error, isLoading, mutate } = useSWR<InsightCard[]>(
    `/api/feed?limit=${limit}`,
    fetcher,
    { refreshInterval: 60_000 }, // Refresh every minute
  );

  const dismissCard = useCallback(
    async (cardId: number) => {
      await api.patch(`/api/feed/${cardId}`, { is_dismissed: true });
      await mutate();
    },
    [mutate],
  );

  const markRead = useCallback(
    async (cardId: number) => {
      await api.patch(`/api/feed/${cardId}`, { is_read: true });
    },
    [],
  );

  return {
    cards: data ?? [],
    isLoading,
    error,
    dismissCard,
    markRead,
    refresh: mutate,
  };
}

export function useBriefing() {
  const { data, error, isLoading } = useSWR<BriefingResponse>(
    "/api/feed/briefing",
    fetcher,
    { refreshInterval: 300_000 }, // Refresh every 5 minutes
  );

  return {
    briefing: data ?? null,
    isLoading,
    error,
  };
}
