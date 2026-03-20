"use client";

import { Suspense, useMemo } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { StatCard } from "@/components/widgets/stat-card";
import { HeatmapWidget } from "@/components/widgets/heatmap";
import { BarChartWidget } from "@/components/widgets/bar-chart";
import { TableWidget } from "@/components/widgets/table-widget";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPrice } from "@/lib/utils";
import { CHART_COLOR, PLATFORM_LABELS } from "@/lib/constants";
import {
  useSeatHourRevenue,
  useFulfillmentTime,
  useStaffEfficiency,
  usePlatformSla,
  useDaypartProfitability,
} from "@/hooks/use-operations";
import type { StatCardData } from "@/lib/types";

// --- Skeleton loaders ---

function ChartSkeleton({ className }: { className?: string }) {
  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader><Skeleton className="h-5 w-40 bg-slate-100" /></CardHeader>
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

// --- Stat cards row (derived from platformSla + staffEfficiency) ---

function OpsStatCards() {
  const { data: slaRaw, isLoading: slaLoading } = usePlatformSla();
  const { data: staffRaw, isLoading: staffLoading } = useStaffEfficiency();
  const isLoading = slaLoading || staffLoading;

  const cards = useMemo<StatCardData[] | null>(() => {
    if (!slaRaw || !staffRaw) return null;

    const slaData = slaRaw as { platform: string; on_time_pct: number; avg_prep_time: number }[];
    const staffData = staffRaw as { staff_name: string; revenue: number }[];

    const avgPrep = slaData.length > 0
      ? slaData.reduce((sum, p) => sum + p.avg_prep_time, 0) / slaData.length
      : 0;

    const bestSla = slaData.length > 0
      ? slaData.reduce((best, p) => (p.on_time_pct > best.on_time_pct ? p : best), slaData[0])
      : null;

    const topStaff = staffData.length > 0
      ? staffData.reduce((best, s) => (s.revenue > best.revenue ? s : best), staffData[0])
      : null;

    return [
      {
        label: "Avg Prep Time",
        value: avgPrep.toFixed(1),
        suffix: " min",
        changeLabel: "across all platforms",
      },
      {
        label: "Best SLA Platform",
        value: bestSla ? (PLATFORM_LABELS[bestSla.platform] ?? bestSla.platform) : "-",
        changeLabel: bestSla ? `${bestSla.on_time_pct.toFixed(1)}% on-time` : undefined,
      },
      {
        label: "Top Staff",
        value: topStaff?.staff_name ?? "-",
        changeLabel: topStaff ? `${formatPrice(topStaff.revenue)} revenue` : undefined,
      },
    ];
  }, [slaRaw, staffRaw]);

  if (isLoading || !cards) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => <StatCardSkeleton key={i} />)}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {cards.map((card) => <StatCard key={card.label} data={card} />)}
    </div>
  );
}

// --- Seat-Hour Revenue Heatmap ---

function SeatHourHeatmap() {
  const { data, isLoading } = useSeatHourRevenue();
  if (isLoading || !data) return <ChartSkeleton className="h-[340px]" />;

  const heatmap = data as { cells: { x: string | number; y: string | number; value: number }[]; maxValue: number };

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Seat-Hour Revenue</CardTitle>
        <p className="text-xs text-slate-500">Revenue per seat by hour and day of week</p>
      </CardHeader>
      <CardContent>
        <HeatmapWidget
          data={heatmap as unknown as Record<string, unknown>}
          config={{ currency: true, colorScale: CHART_COLOR.teal }}
        />
      </CardContent>
    </Card>
  );
}

// --- Fulfillment Time Distribution ---

function FulfillmentTimeChart() {
  const { data, isLoading } = useFulfillmentTime();
  if (isLoading || !data) return <ChartSkeleton />;

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Fulfillment Time Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <BarChartWidget
          data={data as unknown as Record<string, unknown>[]}
          config={{
            xKey: "bucket",
            bars: [{ key: "count", name: "Orders", color: CHART_COLOR.blue }],
          }}
        />
      </CardContent>
    </Card>
  );
}

// --- Staff Efficiency Table ---

function StaffEfficiencyTable() {
  const { data, isLoading } = useStaffEfficiency();
  if (isLoading || !data) return <ChartSkeleton className="h-[280px]" />;

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Staff Efficiency Ranking</CardTitle>
      </CardHeader>
      <CardContent>
        <TableWidget
          data={data as Record<string, unknown>[]}
          config={{
            sortable: true,
            columns: [
              { key: "staff_name", label: "Staff", format: "text" },
              { key: "orders", label: "Orders", format: "number" },
              { key: "revenue", label: "Revenue", format: "currency" },
              { key: "avg_ticket", label: "Avg Ticket", format: "currency" },
              { key: "void_count", label: "Voids", format: "number" },
              { key: "void_rate", label: "Void Rate", format: "percent" },
            ],
          }}
        />
      </CardContent>
    </Card>
  );
}

// --- Platform SLA Compliance ---

function PlatformSlaChart() {
  const { data, isLoading } = usePlatformSla();
  if (isLoading || !data) return <ChartSkeleton />;

  const platforms = (data as { platform: string; on_time_pct: number }[]).map((p) => ({
    ...p,
    platform: PLATFORM_LABELS[p.platform] ?? p.platform,
  }));

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Platform SLA Compliance</CardTitle>
      </CardHeader>
      <CardContent>
        <BarChartWidget
          data={platforms as unknown as Record<string, unknown>[]}
          config={{
            xKey: "platform",
            bars: [{ key: "on_time_pct", name: "On-Time %", color: CHART_COLOR.teal }],
          }}
        />
      </CardContent>
    </Card>
  );
}

// --- Daypart Profitability ---

function DaypartProfitabilityChart() {
  const { data, isLoading } = useDaypartProfitability();
  if (isLoading || !data) return <ChartSkeleton />;

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Daypart Profitability</CardTitle>
        <p className="text-xs text-slate-500">Revenue and cost breakdown by time of day</p>
      </CardHeader>
      <CardContent>
        <BarChartWidget
          data={data as unknown as Record<string, unknown>[]}
          config={{
            xKey: "daypart",
            currency: true,
            bars: [
              { key: "revenue", name: "Revenue", color: "#14b8a6" },
              { key: "cost", name: "Cost", color: "#f43f5e" },
            ],
          }}
        />
      </CardContent>
    </Card>
  );
}

// --- Page composition ---

export default function OperationsPage() {
  return (
    <Suspense>
      <PageHeader
        title="Operational Efficiency"
        description="Revenue per seat-hour, fulfillment times, staff efficiency, and SLA compliance"
      >
        <PeriodSelector />
      </PageHeader>

      {/* Row 1 -- Stat cards */}
      <OpsStatCards />

      {/* Row 2 -- Seat-hour heatmap + Fulfillment time */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SeatHourHeatmap />
        <FulfillmentTimeChart />
      </div>

      {/* Row 3 -- Staff efficiency table (full width) */}
      <div className="mt-6">
        <StaffEfficiencyTable />
      </div>

      {/* Row 4 -- Platform SLA + Daypart profitability */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PlatformSlaChart />
        <DaypartProfitabilityChart />
      </div>
    </Suspense>
  );
}
