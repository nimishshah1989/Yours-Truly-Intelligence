"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import { usePeriod } from "./use-period";
import type { ReconciliationSummary, ReconciliationCheck } from "@/lib/types";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useReconciliationSummary() {
  const { periodParams } = usePeriod();
  return useSWR<ReconciliationSummary>(
    `/api/reconciliation/summary?${periodParams}`,
    fetcher<ReconciliationSummary>,
  );
}

export function useReconciliationChecks() {
  const { periodParams } = usePeriod();
  return useSWR<ReconciliationCheck[]>(
    `/api/reconciliation/checks?${periodParams}`,
    fetcher<ReconciliationCheck[]>,
  );
}
