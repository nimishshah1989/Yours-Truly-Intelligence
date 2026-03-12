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
  const { periodParams } = usePeriod();
  return useSWR(`/api/customers/cohorts?${periodParams}`, fetcher);
}

export function useChurnRisk() {
  const { periodParams } = usePeriod();
  return useSWR(`/api/customers/churn-risk?${periodParams}`, fetcher);
}

export function useLtvDistribution() {
  const { periodParams } = usePeriod();
  return useSWR(`/api/customers/ltv-distribution?${periodParams}`, fetcher);
}

export function useCustomerConcentration() {
  const { periodParams } = usePeriod();
  return useSWR(`/api/customers/concentration?${periodParams}`, fetcher);
}
