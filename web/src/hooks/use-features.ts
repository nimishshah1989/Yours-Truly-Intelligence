"use client";

import useSWR from "swr";
import { api } from "@/lib/api";

const fetcher = <T>(path: string) => api.get<T>(path);

interface FeaturesResponse {
  channels: boolean;
  tally: boolean;
  vendor_watch: boolean;
  portion_drift: boolean;
  stock: boolean;
  intelligence: boolean;
  purchases: boolean;
}

export function useFeatures() {
  return useSWR<FeaturesResponse>("/api/features", fetcher<FeaturesResponse>, {
    revalidateOnFocus: false,
    dedupingInterval: 60000,
  });
}
