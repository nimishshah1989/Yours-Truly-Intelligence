"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { usePeriod } from "./use-period";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useSeatHourRevenue() {
  const { periodParams } = usePeriod();
  return useSWR(`/api/operations/seat-hour-revenue?${periodParams}`, fetcher);
}

export function useFulfillmentTime() {
  const { periodParams } = usePeriod();
  return useSWR(`/api/operations/fulfillment-time?${periodParams}`, fetcher);
}

export function useStaffEfficiency() {
  const { periodParams } = usePeriod();
  return useSWR(`/api/operations/staff-efficiency?${periodParams}`, fetcher);
}

export function usePlatformSla() {
  const { periodParams } = usePeriod();
  return useSWR(`/api/operations/platform-sla?${periodParams}`, fetcher);
}

export function useDaypartProfitability() {
  const { periodParams } = usePeriod();
  return useSWR(`/api/operations/daypart-profitability?${periodParams}`, fetcher);
}
