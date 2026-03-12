"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { usePeriod } from "./use-period";
import type {
  RevenueOverview,
  TrendPoint,
  RevenueHeatmapResponse,
  ConcentrationItem,
  PaymentModesResponse,
  PlatformRow,
  DiscountAnalysisResponse,
} from "@/lib/types";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useRevenueOverview() {
  const { periodParams } = usePeriod();
  return useSWR<RevenueOverview>(
    `/api/revenue/overview?${periodParams}`,
    fetcher<RevenueOverview>,
  );
}

export function useRevenueTrend() {
  const { periodParams } = usePeriod();
  return useSWR<TrendPoint[]>(
    `/api/revenue/trend?${periodParams}`,
    fetcher<TrendPoint[]>,
  );
}

export function useRevenueHeatmap() {
  const { periodParams } = usePeriod();
  return useSWR<RevenueHeatmapResponse>(
    `/api/revenue/heatmap?${periodParams}`,
    fetcher<RevenueHeatmapResponse>,
  );
}

export function useRevenueConcentration() {
  const { periodParams } = usePeriod();
  return useSWR<ConcentrationItem[]>(
    `/api/revenue/concentration?${periodParams}`,
    fetcher<ConcentrationItem[]>,
  );
}

export function usePaymentModes() {
  const { periodParams } = usePeriod();
  return useSWR<PaymentModesResponse>(
    `/api/revenue/payment-modes?${periodParams}`,
    fetcher<PaymentModesResponse>,
  );
}

export function usePlatformProfitability() {
  const { periodParams } = usePeriod();
  return useSWR<PlatformRow[]>(
    `/api/revenue/platform-profitability?${periodParams}`,
    fetcher<PlatformRow[]>,
  );
}

export function useDiscountAnalysis() {
  const { periodParams } = usePeriod();
  return useSWR<DiscountAnalysisResponse>(
    `/api/revenue/discount-analysis?${periodParams}`,
    fetcher<DiscountAnalysisResponse>,
  );
}
