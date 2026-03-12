"use client";

import useSWR from "swr";
import { api } from "@/lib/api";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useHomeSummary() {
  return useSWR("/api/home/summary", fetcher);
}
