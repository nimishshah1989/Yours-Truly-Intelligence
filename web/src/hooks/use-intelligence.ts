"use client";

import useSWR from "swr";
import { api } from "@/lib/api";

const fetcher = <T>(path: string) => api.get<T>(path);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface IntelligenceFinding {
  id: string;
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  detail: {
    what_to_do?: string;
    logic?: string;
    [key: string]: unknown;
  } | null;
  related_items: string[] | null;
  rupee_impact: number | null;
  is_actioned: boolean;
  finding_date: string;
  created_at: string;
}

export interface IntelligenceSummary {
  total_findings: number;
  total_impact_paisa: number;
  by_category: Record<string, { count: number; impact: number }>;
  top_findings: IntelligenceFinding[];
  stats: {
    revenue_yesterday: number;
    orders_yesterday: number;
    avg_ticket: number;
    cogs_pct: number | null;
  } | null;
}

export interface IntelligenceCategoryResponse {
  findings: IntelligenceFinding[];
  total_count: number;
  total_impact_paisa: number;
}

export interface HourlyDataPoint {
  hour: number;
  revenue: number;
  orders: number;
}

export interface OperationsIntelligence extends IntelligenceCategoryResponse {
  hourly_data?: HourlyDataPoint[];
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useIntelligenceSummary() {
  return useSWR<IntelligenceSummary>(
    "/api/intelligence/summary",
    fetcher<IntelligenceSummary>,
    { refreshInterval: 300_000 },
  );
}

export function useIntelligenceRevenue() {
  return useSWR<IntelligenceCategoryResponse>(
    "/api/intelligence/revenue",
    fetcher<IntelligenceCategoryResponse>,
    { refreshInterval: 300_000 },
  );
}

export function useIntelligenceCost() {
  return useSWR<IntelligenceCategoryResponse>(
    "/api/intelligence/cost",
    fetcher<IntelligenceCategoryResponse>,
    { refreshInterval: 300_000 },
  );
}

export function useIntelligenceMenu() {
  return useSWR<IntelligenceCategoryResponse>(
    "/api/intelligence/menu",
    fetcher<IntelligenceCategoryResponse>,
    { refreshInterval: 300_000 },
  );
}

export function useIntelligenceOperations() {
  return useSWR<OperationsIntelligence>(
    "/api/intelligence/operations",
    fetcher<OperationsIntelligence>,
    { refreshInterval: 300_000 },
  );
}

export interface InsightResponse {
  narrative: string | null;
  generated: boolean;
}

export function useIntelligenceInsight() {
  return useSWR<InsightResponse>(
    "/api/intelligence/insight",
    fetcher<InsightResponse>,
    { refreshInterval: 600_000 },
  );
}
