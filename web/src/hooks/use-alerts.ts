"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { AlertRule, AlertHistoryEntry } from "@/lib/types";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useAlertRules() {
  return useSWR<AlertRule[]>("/api/alerts/rules", fetcher<AlertRule[]>);
}

export function useAlertHistory() {
  return useSWR<AlertHistoryEntry[]>(
    "/api/alerts/history?limit=50",
    fetcher<AlertHistoryEntry[]>,
  );
}
