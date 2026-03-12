"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { usePeriod } from "./use-period";
import type {
  CancellationHeatmapResponse,
  VoidAnomaliesResponse,
  InventoryShrinkageRow,
  DiscountAbuseResponse,
  PlatformCommissionRow,
  PeakHourLeakageResponse,
} from "@/lib/types";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useCancellationHeatmap() {
  const { periodParams } = usePeriod();
  return useSWR<CancellationHeatmapResponse>(
    `/api/leakage/cancellation-heatmap?${periodParams}`,
    fetcher<CancellationHeatmapResponse>,
  );
}

export function useVoidAnomalies() {
  const { periodParams } = usePeriod();
  return useSWR<VoidAnomaliesResponse>(
    `/api/leakage/void-anomalies?${periodParams}`,
    fetcher<VoidAnomaliesResponse>,
  );
}

export function useInventoryShrinkage() {
  const { periodParams } = usePeriod();
  return useSWR<InventoryShrinkageRow[]>(
    `/api/leakage/inventory-shrinkage?${periodParams}`,
    fetcher<InventoryShrinkageRow[]>,
  );
}

export function useDiscountAbuse() {
  const { periodParams } = usePeriod();
  return useSWR<DiscountAbuseResponse>(
    `/api/leakage/discount-abuse?${periodParams}`,
    fetcher<DiscountAbuseResponse>,
  );
}

export function usePlatformCommissionImpact() {
  const { periodParams } = usePeriod();
  return useSWR<PlatformCommissionRow[]>(
    `/api/leakage/platform-commission-impact?${periodParams}`,
    fetcher<PlatformCommissionRow[]>,
  );
}

export function usePeakHourLeakage() {
  const { periodParams } = usePeriod();
  return useSWR<PeakHourLeakageResponse>(
    `/api/leakage/peak-hour-leakage?${periodParams}`,
    fetcher<PeakHourLeakageResponse>,
  );
}
