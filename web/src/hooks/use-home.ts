"use client";

import useSWR from "swr";
import { api } from "@/lib/api";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useHomeSummary() {
  return useSWR("/api/home/summary", fetcher);
}

interface MoneyFoundItem {
  title: string;
  rupee_impact: number;
  category: string;
  severity: string;
}

interface MoneyFoundResponse {
  total_impact_paisa: number;
  finding_count: number;
  top_findings: MoneyFoundItem[];
}

export function useMoneyFound() {
  return useSWR<MoneyFoundResponse>("/api/home/money-found", fetcher<MoneyFoundResponse>);
}
