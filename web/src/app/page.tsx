"use client";

import Link from "next/link";
import { Suspense } from "react";
import { Pin } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/widgets/stat-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRestaurant } from "@/hooks/use-restaurant";
import { useHomeSummary } from "@/hooks/use-home";
import { usePinnedDashboards } from "@/hooks/use-dashboards";
import { formatDate } from "@/lib/utils";
import type { StatCardData, SavedDashboard } from "@/lib/types";

export default function HomePage() {
  const { current } = useRestaurant();

  return (
    <Suspense fallback={<HomePageSkeleton />}>
      <PageHeader
        title={current?.name ?? "Dashboard"}
        description="Executive summary — key metrics at a glance"
      />

      <HomeStats />

      <PinnedDashboards />
    </Suspense>
  );
}

// ---------------------------------------------------------------------------
// Home stat cards
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Pinned dashboards
// ---------------------------------------------------------------------------

function PinnedDashboardCard({ dashboard }: { dashboard: SavedDashboard }) {
  return (
    <Link href={`/dashboards/${dashboard.id}`}>
      <Card className="cursor-pointer rounded-xl border-slate-200 transition-all hover:border-teal-300 hover:shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="line-clamp-1 text-sm font-semibold text-slate-800">
              {dashboard.title}
            </CardTitle>
            <Badge variant="secondary" className="shrink-0 gap-1 bg-teal-50 text-xs text-teal-700">
              <Pin className="h-3 w-3" />
              Pinned
            </Badge>
          </div>
          {dashboard.description && (
            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
              {dashboard.description}
            </p>
          )}
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">{formatDate(dashboard.created_at)}</p>
        </CardContent>
      </Card>
    </Link>
  );
}

function PinnedDashboards() {
  const { data: pinned, isLoading } = usePinnedDashboards();

  return (
    <div className="mt-8">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Pinned Dashboards</h2>
        <Link href="/dashboards" className="text-xs text-teal-600 hover:underline">
          View all
        </Link>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      ) : pinned.length === 0 ? (
        <Card className="rounded-xl border-dashed border-slate-300">
          <CardContent className="flex h-36 items-center justify-center p-6">
            <p className="text-sm text-muted-foreground">
              No pinned dashboards yet.{" "}
              <Link href="/chat" className="text-teal-600 hover:underline">
                Ask the AI
              </Link>{" "}
              to generate insights and pin them here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {pinned.map((d) => (
            <PinnedDashboardCard key={d.id} dashboard={d} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton for SSR fallback
// ---------------------------------------------------------------------------

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
