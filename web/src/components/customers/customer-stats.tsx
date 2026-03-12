"use client";

import { StatCard } from "@/components/widgets/stat-card";
import { BarChartWidget } from "@/components/widgets/bar-chart";
import { LineChartWidget } from "@/components/widgets/line-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPrice, formatNumber } from "@/lib/utils";
import { CHART_COLOR } from "@/lib/constants";
import { useCustomerOverview, useRfmSegments } from "@/hooks/use-customers";
import type { StatCardData } from "@/lib/types";

// ---------------------------------------------------------------------------
// Shared skeletons
// ---------------------------------------------------------------------------

export function ChartSkeleton({ className }: { className?: string }) {
  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <Skeleton className="h-5 w-40 bg-slate-100" />
      </CardHeader>
      <CardContent>
        <Skeleton className={`w-full bg-slate-100 ${className ?? "h-[300px]"}`} />
      </CardContent>
    </Card>
  );
}

function StatCardSkeleton() {
  return (
    <Card className="rounded-xl border-slate-200">
      <CardContent className="p-5">
        <Skeleton className="h-4 w-24 bg-slate-100" />
        <Skeleton className="mt-3 h-7 w-32 bg-slate-100" />
        <Skeleton className="mt-2 h-3 w-20 bg-slate-100" />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Stat cards row
// ---------------------------------------------------------------------------

export function CustomerStatCards() {
  const { data, isLoading } = useCustomerOverview();

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  const overview = data as {
    total: number;
    new_in_period: number;
    returning: number;
    avg_ltv: number;
    churn_rate: number;
  };

  const cards: StatCardData[] = [
    { label: "Total Customers", value: formatNumber(overview.total) },
    { label: "New This Period", value: formatNumber(overview.new_in_period) },
    { label: "Avg LTV", value: formatPrice(overview.avg_ltv) },
    { label: "Churn Rate", value: overview.churn_rate.toFixed(1), suffix: "%" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {cards.map((card) => (
        <StatCard key={card.label} data={card} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// RFM Segments bar chart
// ---------------------------------------------------------------------------

export function RfmSegmentsChart() {
  const { data, isLoading } = useRfmSegments();

  if (isLoading || !data) return <ChartSkeleton />;

  const rfm = data as {
    segments: { name: string; count: number; avg_spend: number; avg_visits: number }[];
  };

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">RFM Segments</CardTitle>
      </CardHeader>
      <CardContent>
        <BarChartWidget
          data={rfm.segments as unknown as Record<string, unknown>[]}
          config={{
            xKey: "name",
            bars: [{ key: "count", name: "Customers", color: CHART_COLOR.teal }],
          }}
        />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// New vs Returning trend line chart
// ---------------------------------------------------------------------------

export function NewVsReturningTrend() {
  const { data, isLoading } = useCustomerOverview();

  if (isLoading || !data) return <ChartSkeleton />;

  const overview = data as {
    trend: { date: string; new: number; returning: number }[];
  };

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">New vs Returning</CardTitle>
      </CardHeader>
      <CardContent>
        <LineChartWidget
          data={overview.trend as unknown as Record<string, unknown>[]}
          config={{
            xKey: "date",
            lines: [
              { key: "new", name: "New", color: CHART_COLOR.teal },
              { key: "returning", name: "Returning", color: CHART_COLOR.blue },
            ],
          }}
        />
      </CardContent>
    </Card>
  );
}
