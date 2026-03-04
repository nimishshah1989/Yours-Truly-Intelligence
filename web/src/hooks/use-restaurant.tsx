"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import useSWR, { mutate as globalMutate } from "swr";
import { api, setCurrentRestaurantId } from "@/lib/api";
import type { Restaurant, RestaurantListResponse } from "@/lib/types";

interface RestaurantContextValue {
  restaurants: Restaurant[];
  current: Restaurant | null;
  isLoading: boolean;
  switchRestaurant: (id: number) => void;
}

const RestaurantContext = createContext<RestaurantContextValue>({
  restaurants: [],
  current: null,
  isLoading: true,
  switchRestaurant: () => {},
});

const fetcher = () => api.get<RestaurantListResponse>("/api/restaurants");

export function RestaurantProvider({ children }: { children: ReactNode }) {
  const { data, isLoading } = useSWR("restaurants", fetcher);
  const [currentId, setCurrentId] = useState<number | null>(null);

  const restaurants = data?.restaurants ?? [];
  const current = restaurants.find((r) => r.id === currentId) ?? null;

  // Auto-select first restaurant on load
  useEffect(() => {
    if (restaurants.length > 0 && currentId === null) {
      setCurrentId(restaurants[0].id);
      setCurrentRestaurantId(restaurants[0].id);
    }
  }, [restaurants, currentId]);

  const switchRestaurant = useCallback((id: number) => {
    setCurrentId(id);
    setCurrentRestaurantId(id);
    // Clear all SWR caches when switching restaurant
    globalMutate(() => true, undefined, { revalidate: true });
  }, []);

  return (
    <RestaurantContext.Provider
      value={{ restaurants, current, isLoading, switchRestaurant }}
    >
      {children}
    </RestaurantContext.Provider>
  );
}

export function useRestaurant() {
  return useContext(RestaurantContext);
}
