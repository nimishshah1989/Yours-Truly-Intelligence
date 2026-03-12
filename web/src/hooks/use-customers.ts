"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { usePeriod } from "./use-period";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useCustomerOverview() {
  const { periodParams } = usePeriod();
  return useSWR(`/api/customers/overview?${periodParams}`, fetcher);
}

export function useRfmSegments() {
  const { periodParams } = usePeriod();
  return useSWR(`/api/customers/rfm?${periodParams}`, fetcher);
}

export function useCohorts() {
  return useSWR("/api/customers/cohorts", fetcher);
}

export function useChurnRisk() {
  return useSWR("/api/customers/churn-risk", fetcher);
}

export function useLtvDistribution() {
  return useSWR("/api/customers/ltv-distribution", fetcher);
}

export function useCustomerConcentration() {
  const { periodParams } = usePeriod();
  return useSWR(`/api/customers/concentration?${periodParams}`, fetcher);
}
