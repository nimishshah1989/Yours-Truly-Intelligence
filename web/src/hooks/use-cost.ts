"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { usePeriod } from "./use-period";
import type {
  CogsTrendResponse,
  VendorPriceCreepResponse,
  FoodCostGapResponse,
  PurchaseCalendarResponse,
  MarginWaterfallResponse,
  IngredientVolatilityResponse,
} from "@/lib/types";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useCogsTrend() {
  const { periodParams } = usePeriod();
  return useSWR<CogsTrendResponse>(
    `/api/cost/cogs-trend?${periodParams}`,
    fetcher<CogsTrendResponse>,
  );
}

export function useVendorPriceCreep() {
  const { periodParams } = usePeriod();
  return useSWR<VendorPriceCreepResponse>(
    `/api/cost/vendor-price-creep?${periodParams}`,
    fetcher<VendorPriceCreepResponse>,
  );
}

export function useFoodCostGap() {
  const { periodParams } = usePeriod();
  return useSWR<FoodCostGapResponse>(
    `/api/cost/food-cost-gap?${periodParams}`,
    fetcher<FoodCostGapResponse>,
  );
}

export function usePurchaseCalendar() {
  const { periodParams } = usePeriod();
  return useSWR<PurchaseCalendarResponse>(
    `/api/cost/purchase-calendar?${periodParams}`,
    fetcher<PurchaseCalendarResponse>,
  );
}

export function useMarginWaterfall() {
  const { periodParams } = usePeriod();
  return useSWR<MarginWaterfallResponse>(
    `/api/cost/margin-waterfall?${periodParams}`,
    fetcher<MarginWaterfallResponse>,
  );
}

export function useIngredientVolatility() {
  const { periodParams } = usePeriod();
  return useSWR<IngredientVolatilityResponse>(
    `/api/cost/ingredient-volatility?${periodParams}`,
    fetcher<IngredientVolatilityResponse>,
  );
}

interface PortionDriftItem {
  ingredient: string;
  drift_pct: number;
  drift_cost: number;
  unit: string;
}

interface PortionDriftResponse {
  data: PortionDriftItem[];
}

export function usePortionDrift() {
  const { periodParams } = usePeriod();
  return useSWR<PortionDriftResponse>(
    `/api/cost/portion-drift?${periodParams}`,
    fetcher<PortionDriftResponse>,
  );
}
