"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { usePeriod } from "./use-period";
import type {
  MenuTopItemsResponse,
  MenuBcgResponse,
  MenuAffinityResponse,
  MenuCannibalizationResponse,
  MenuCategoryMixResponse,
  MenuModifierResponse,
  MenuDeadSkusResponse,
} from "@/lib/types";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useTopItems() {
  const { periodParams } = usePeriod();
  return useSWR<MenuTopItemsResponse>(
    `/api/menu/top-items?${periodParams}`,
    fetcher<MenuTopItemsResponse>,
  );
}

export function useBcgMatrix() {
  const { periodParams } = usePeriod();
  return useSWR<MenuBcgResponse>(
    `/api/menu/bcg-matrix?${periodParams}`,
    fetcher<MenuBcgResponse>,
  );
}

export function useAffinity() {
  const { periodParams } = usePeriod();
  return useSWR<MenuAffinityResponse>(
    `/api/menu/affinity?${periodParams}`,
    fetcher<MenuAffinityResponse>,
  );
}

export function useCannibalization() {
  const { periodParams } = usePeriod();
  return useSWR<MenuCannibalizationResponse>(
    `/api/menu/cannibalization?${periodParams}`,
    fetcher<MenuCannibalizationResponse>,
  );
}

export function useCategoryMix() {
  const { periodParams } = usePeriod();
  return useSWR<MenuCategoryMixResponse>(
    `/api/menu/category-mix?${periodParams}`,
    fetcher<MenuCategoryMixResponse>,
  );
}

export function useModifierAnalysis() {
  const { periodParams } = usePeriod();
  return useSWR<MenuModifierResponse>(
    `/api/menu/modifier-analysis?${periodParams}`,
    fetcher<MenuModifierResponse>,
  );
}

export function useDeadSkus() {
  const { periodParams } = usePeriod();
  return useSWR<MenuDeadSkusResponse>(
    `/api/menu/dead-skus?${periodParams}`,
    fetcher<MenuDeadSkusResponse>,
  );
}
