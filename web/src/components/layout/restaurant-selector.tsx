"use client";

import { useRestaurant } from "@/hooks/use-restaurant";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

export function RestaurantSelector() {
  const { restaurants, current, isLoading, switchRestaurant } = useRestaurant();

  if (isLoading) {
    return <Skeleton className="h-9 w-full" />;
  }

  if (restaurants.length === 0) {
    return (
      <div className="px-3 py-2 text-sm text-muted-foreground">
        No restaurants
      </div>
    );
  }

  return (
    <Select
      value={current ? String(current.id) : undefined}
      onValueChange={(val) => switchRestaurant(Number(val))}
    >
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Select restaurant" />
      </SelectTrigger>
      <SelectContent>
        {restaurants.map((r) => (
          <SelectItem key={r.id} value={String(r.id)}>
            {r.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
