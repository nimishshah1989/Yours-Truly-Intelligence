"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { StatCard } from "@/components/widgets/stat-card";
import { LineChartWidget } from "@/components/widgets/line-chart";
import { PieChartWidget } from "@/components/widgets/pie-chart";
import { BarChartWidget } from "@/components/widgets/bar-chart";
import { HeatmapWidget } from "@/components/widgets/heatmap";
import { ParetoChartWidget } from "@/components/widgets/pareto-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPrice, formatNumber } from "@/lib/utils";
import { CHART_COLOR, PLATFORM_LABELS, PAYMENT_MODE_LABELS } from "@/lib/constants";
import {
  useRevenueOverview,
  useRevenueTrend,
  useRevenueHeatmap,
  useRevenueConcentration,
  usePaymentModes,
  usePlatformProfitability,
  useDiscountAnalysis,
} from "@/hooks/use-revenue";
import type { StatCardData } from "@/lib/types";

// ---------------------------------------------------------------------------
// Skeleton loader for chart cards
// ---------------------------------------------------------------------------

function ChartSkeleton({ className }: { className?: string }) {
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

function RevenueStatCards() {
  const { data, isLoading } = useRevenueOverview();

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
    today_revenue: number;
    today_orders: number;
    avg_ticket: number;
    wow_change: number | null;
    mom_change: number | null;
    sparkline: number[];
  };

  const cards: StatCardData[] = [
    {
      label: "Today's Revenue",
      value: formatPrice(overview.today_revenue),
      change: overview.wow_change ?? undefined,
      changeLabel: "vs last week",
    },
    {
      label: "Orders Today",
      value: formatNumber(overview.today_orders),
      changeLabel: "today",
    },
    {
      label: "Avg Ticket Size",
      value: formatPrice(overview.avg_ticket),
      changeLabel: "per order",
    },
    {
      label: "Month-on-Month",
      value: overview.mom_change != null
        ? `${overview.mom_change >= 0 ? "+" : ""}${overview.mom_change.toFixed(1)}%`
        : "N/A",
      change: overview.mom_change ?? undefined,
      changeLabel: "vs prior period",
    },
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
// Revenue trend (line chart)
// ---------------------------------------------------------------------------

function RevenueTrendChart() {
  const { data, isLoading } = useRevenueTrend();

  if (isLoading || !data) return <ChartSkeleton />;

  const trend = data as { date: string; revenue: number; net_revenue: number; orders: number }[];

  // Compute insight subtitle from the trend data (use second-to-last point = yesterday)
  const yesterdayIdx = trend.length >= 2 ? trend.length - 2 : trend.length - 1;
  const yesterdayData = trend[yesterdayIdx];
  const insightText = yesterdayData
    ? `Yesterday: ${formatPrice(yesterdayData.revenue)} gross, ${formatNumber(yesterdayData.orders)} orders`
    : undefined;

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Revenue Trend</CardTitle>
        {insightText && (
          <p className="text-xs text-slate-500">{insightText}</p>
        )}
      </CardHeader>
      <CardContent>
        <LineChartWidget
          data={trend as unknown as Record<string, unknown>[]}
          config={{
            xKey: "date",
            currency: true,
            lines: [
              { key: "revenue", name: "Gross Revenue", color: CHART_COLOR.teal },
              { key: "net_revenue", name: "Net Revenue", color: CHART_COLOR.blue },
            ],
          }}
        />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Payment mode pie chart
// ---------------------------------------------------------------------------

function PaymentModePie() {
  const { data, isLoading } = usePaymentModes();

  if (isLoading || !data) return <ChartSkeleton />;

  const modes = data as {
    breakdown: { mode: string; revenue: number; count: number }[];
    trend: Record<string, unknown>[];
  };

  const pieData = modes.breakdown.map((m) => ({
    name: PAYMENT_MODE_LABELS[m.mode] ?? m.mode,
    value: m.revenue,
  }));

  // Compute insight: top payment mode
  const topMode = pieData.length > 0
    ? pieData.reduce((a, b) => (a.value > b.value ? a : b))
    : null;
  const paymentInsight = topMode
    ? `${topMode.name} leads with ${formatPrice(topMode.value)}`
    : undefined;

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Payment Mode Split</CardTitle>
        {paymentInsight && (
          <p className="text-xs text-slate-500">{paymentInsight}</p>
        )}
      </CardHeader>
      <CardContent>
        <PieChartWidget
          data={pieData as unknown as Record<string, unknown>[]}
          config={{ nameKey: "name", valueKey: "value", currency: true }}
        />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Revenue heatmap (day x hour)
// ---------------------------------------------------------------------------

function RevenueHeatmap() {
  const { data, isLoading } = useRevenueHeatmap();

  if (isLoading || !data) return <ChartSkeleton className="h-[340px]" />;

  const heatmap = data as {
    cells: { x: string | number; y: string | number; value: number }[];
    max_value: number;
  };

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Revenue Heatmap (Day x Hour)</CardTitle>
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

// ---------------------------------------------------------------------------
// Revenue concentration (Pareto)
// ---------------------------------------------------------------------------

function RevenueConcentration() {
  const { data, isLoading } = useRevenueConcentration();

  if (isLoading || !data) return <ChartSkeleton className="h-[320px]" />;

  const allItems = data as { name: string; revenue: number; cumulative_pct: number }[];
  // Show top 30 items for readability — they typically cover 80%+ of revenue
  const items = allItems.slice(0, 30).map((item) => ({
    ...item,
    name: item.name.length > 16 ? item.name.slice(0, 14) + "…" : item.name,
  }));
  // Find the 80% crossing point
  const itemsAt80 = allItems.findIndex((i) => i.cumulative_pct >= 80) + 1;

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">
          Revenue Concentration (80/20)
          {itemsAt80 > 0 && (
            <span className="ml-2 text-xs font-normal text-slate-500">
              Top {itemsAt80} of {allItems.length} items = 80% of revenue
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ParetoChartWidget
          data={items as unknown as Record<string, unknown>[]}
          config={{ nameKey: "name", valueKey: "revenue", currency: true }}
        />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Platform profitability (grouped bar)
// ---------------------------------------------------------------------------

function PlatformProfitability() {
  const { data, isLoading } = usePlatformProfitability();

  if (isLoading || !data) return <ChartSkeleton />;

  const platforms = data as {
    platform: string;
    gross: number;
    net: number;
    commission: number;
    orders: number;
  }[];

  const barData = platforms.map((p) => ({
    name: PLATFORM_LABELS[p.platform] ?? p.platform,
    Gross: p.gross,
    Net: p.net,
    Commission: p.commission,
  }));

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Platform Profitability</CardTitle>
      </CardHeader>
      <CardContent>
        <BarChartWidget
          data={barData as unknown as Record<string, unknown>[]}
          config={{
            xKey: "name",
            currency: true,
            bars: [
              { key: "Gross", name: "Gross Revenue", color: CHART_COLOR.teal },
              { key: "Net", name: "Net Revenue", color: CHART_COLOR.blue },
              { key: "Commission", name: "Commission", color: CHART_COLOR.rose },
            ],
          }}
        />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Discount trend (bar chart)
// ---------------------------------------------------------------------------

function DiscountTrend() {
  const { data, isLoading } = useDiscountAnalysis();

  if (isLoading || !data) return <ChartSkeleton />;

  const discount = data as {
    total_discounts: number;
    discount_rate: number;
    avg_per_order: number;
    trend: { date: string; discounts: number; rate: number }[];
  };

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">
          Discount Trend
          <span className="ml-2 text-xs font-normal text-slate-500">
            Total: {formatPrice(discount.total_discounts)} ({discount.discount_rate.toFixed(1)}% of revenue)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <BarChartWidget
          data={discount.trend as unknown as Record<string, unknown>[]}
          config={{
            xKey: "date",
            currency: true,
            bars: [{ key: "discounts", name: "Discounts", color: CHART_COLOR.amber }],
          }}
        />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page composition
// ---------------------------------------------------------------------------

export default function RevenuePage() {
  return (
    <Suspense>
      <PageHeader
        title="Revenue Intelligence"
        description="Revenue trends, heatmaps, concentration analysis, and platform profitability"
      >
        <PeriodSelector />
      </PageHeader>

      {/* Row 1 -- Stat cards */}
      <RevenueStatCards />

      {/* Row 2 -- Revenue trend (2/3) + Payment mode (1/3) */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RevenueTrendChart />
        </div>
        <div>
          <PaymentModePie />
        </div>
      </div>

      {/* Row 3 -- Heatmap (1/2) + Pareto concentration (1/2) */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RevenueHeatmap />
        <RevenueConcentration />
      </div>

      {/* Row 4 -- Platform profitability (1/2) + Discount trend (1/2) */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PlatformProfitability />
        <DiscountTrend />
      </div>
    </Suspense>
  );
}
