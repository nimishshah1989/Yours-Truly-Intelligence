"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/widgets/stat-card";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRestaurant } from "@/hooks/use-restaurant";
import { useHomeSummary } from "@/hooks/use-home";
import type { StatCardData } from "@/lib/types";

export default function HomePage() {
  const { current } = useRestaurant();

  return (
    <Suspense fallback={<HomePageSkeleton />}>
      <PageHeader
        title={current?.name ?? "Dashboard"}
        description="Executive summary — key metrics at a glance"
      />

      <HomeStats />

      {/* Pinned dashboards placeholder */}
      <div className="mt-8">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          Pinned Dashboards
        </h2>
        <Card className="rounded-xl border-dashed border-slate-300">
          <CardContent className="flex h-48 items-center justify-center p-6">
            <p className="text-sm text-muted-foreground">
              No pinned dashboards yet. Pin dashboards from the AI chat or
              dashboard library.
            </p>
          </CardContent>
        </Card>
      </div>
    </Suspense>
  );
}

interface HomeSummaryResponse {
  stats: Array<{
    label: string;
    value: string;
    change?: number | null;
    change_label?: string | null;
    sparkline?: number[] | null;
    prefix?: string | null;
    suffix?: string | null;
  }>;
  last_updated: string;
}

function HomeStats() {
  const { data, isLoading } = useHomeSummary() as {
    data: HomeSummaryResponse | undefined;
    isLoading: boolean;
  };

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {data.stats.map((stat) => {
        const cardData: StatCardData = {
          label: stat.label,
          value: stat.value,
          change: stat.change ?? undefined,
          changeLabel: stat.change_label ?? undefined,
          sparkline: stat.sparkline ?? undefined,
          prefix: stat.prefix ?? undefined,
          suffix: stat.suffix ?? undefined,
        };
        return <StatCard key={stat.label} data={cardData} />;
      })}
    </div>
  );
}

function HomePageSkeleton() {
  return (
    <div>
      <div className="flex justify-between pb-6">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-9 w-40" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    </div>
  );
}
