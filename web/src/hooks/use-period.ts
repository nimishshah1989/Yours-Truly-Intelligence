"use client";

import { useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import type { PeriodKey, PeriodRange } from "@/lib/types";

const DEFAULT_PERIOD: PeriodKey = "7d";

export function usePeriod() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const key = (searchParams.get("period") as PeriodKey) || DEFAULT_PERIOD;
  const start = searchParams.get("start") ?? undefined;
  const end = searchParams.get("end") ?? undefined;

  const period: PeriodRange = { key, start, end };

  const setPeriod = useCallback(
    (newPeriod: PeriodRange) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("period", newPeriod.key);

      if (newPeriod.key === "custom" && newPeriod.start && newPeriod.end) {
        params.set("start", newPeriod.start);
        params.set("end", newPeriod.end);
      } else {
        params.delete("start");
        params.delete("end");
      }

      router.replace(`${pathname}?${params.toString()}`);
    },
    [searchParams, router, pathname]
  );

  // Build query string params for API calls
  const periodParams = key === "custom" && start && end
    ? `period=${key}&start=${start}&end=${end}`
    : `period=${key}`;

  return { period, setPeriod, periodParams };
}
