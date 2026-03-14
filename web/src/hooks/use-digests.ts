"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { Digest } from "@/lib/types";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useDigests() {
  return useSWR<Digest[]>("/api/digests/", fetcher<Digest[]>);
}
