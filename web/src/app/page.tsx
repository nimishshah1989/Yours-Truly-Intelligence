"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { StatCard } from "@/components/widgets/stat-card";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRestaurant } from "@/hooks/use-restaurant";

const PLACEHOLDER_STATS = [
  { label: "Today's Revenue", value: "—", changeLabel: "Loading..." },
  { label: "Orders Today", value: "—", changeLabel: "Loading..." },
  { label: "Avg Order Value", value: "—", changeLabel: "Loading..." },
  { label: "Active Customers", value: "—", changeLabel: "Loading..." },
];

export default function HomePage() {
  const { current, isLoading } = useRestaurant();

  return (
    <Suspense fallback={<HomePageSkeleton />}>
      <PageHeader
        title={current?.name ?? "Dashboard"}
        description="Executive summary — key metrics at a glance"
      >
        <PeriodSelector />
      </PageHeader>

      {/* Stat cards row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {PLACEHOLDER_STATS.map((stat) => (
          <StatCard key={stat.label} data={stat} />
        ))}
      </div>

      {/* Pinned dashboards placeholder */}
      <div className="mt-8">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          Pinned Dashboards
        </h2>
        <Card className="rounded-xl border-dashed border-slate-300">
          <CardContent className="flex h-48 items-center justify-center p-6">
            <p className="text-sm text-muted-foreground">
              {isLoading
                ? "Loading..."
                : "No pinned dashboards yet. Pin dashboards from the AI chat or dashboard library."}
            </p>
          </CardContent>
        </Card>
      </div>
    </Suspense>
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
