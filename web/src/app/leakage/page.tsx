"use client";

import { Suspense } from "react";
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
  useCancellationHeatmap, useVoidAnomalies, useInventoryShrinkage,
  useDiscountAbuse, usePlatformCommissionImpact, usePeakHourLeakage,
} from "@/hooks/use-leakage";
import type { StatCardData } from "@/lib/types";
import { AlertCircle } from "lucide-react";

/* Skeleton helpers */
function ChartSkeleton({ h }: { h?: string }) {
  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader><Skeleton className="h-5 w-40 bg-slate-100" /></CardHeader>
      <CardContent><Skeleton className={`w-full bg-slate-100 ${h ?? "h-[300px]"}`} /></CardContent>
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

/* NA placeholder for sections with no data */
function NotAvailable({ reason }: { reason: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
      <AlertCircle className="h-8 w-8 text-slate-300" />
      <p className="text-sm font-medium text-slate-500">Data Not Available</p>
      <p className="text-xs text-slate-400 max-w-xs">{reason}</p>
    </div>
  );
}

/* Row 1 -- Stat cards */
function LeakageStatCards() {
  const { data: hmData, isLoading: hmL } = useCancellationHeatmap();
  const { data: shData, isLoading: shL } = useInventoryShrinkage();
  const { data: cmData, isLoading: cmL } = usePlatformCommissionImpact();

  if (hmL || shL || cmL || !hmData || !shData || !cmData) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => <StatCardSkeleton key={i} />)}
      </div>
    );
  }
  const hm = hmData as { cancellation_rate: number };
  const shrinkRows = (Array.isArray(shData) ? shData : []) as { shrinkage: number }[];
  const commRows = (Array.isArray(cmData) ? cmData : []) as { commission: number }[];
  const cards: StatCardData[] = [
    { label: "Cancellation Rate", value: `${(hm.cancellation_rate ?? 0).toFixed(1)}%`, changeLabel: "of total orders" },
    { label: "Total Shrinkage Value", value: shrinkRows.length > 0 ? formatPrice(shrinkRows.reduce((s, r) => s + r.shrinkage, 0)) : "N/A", changeLabel: "inventory data not available" },
    { label: "Commission Leakage", value: formatPrice(commRows.reduce((s, r) => s + r.commission, 0)), changeLabel: "platform commissions paid" },
  ];
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {cards.map((c) => <StatCard key={c.label} data={c} />)}
    </div>
  );
}

/* Row 2a -- Cancellation Heatmap */
function CancellationHeatmap() {
  const { data, isLoading } = useCancellationHeatmap();
  if (isLoading || !data) return <ChartSkeleton h="h-[340px]" />;
  const heatmap = data as { cells: { x: string | number; y: string | number; value: number }[]; max_value: number };

  const hasCells = (heatmap.cells ?? []).length > 0;
  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader><CardTitle className="text-base text-slate-800">Cancellation Heatmap (Time × Reason)</CardTitle></CardHeader>
      <CardContent>
        {hasCells ? (
          <HeatmapWidget data={heatmap as unknown as Record<string, unknown>} config={{ colorScale: CHART_COLOR.rose }} />
        ) : (
          <NotAvailable reason="Only 3 cancelled orders detected in the database. Insufficient data to build a meaningful heatmap." />
        )}
      </CardContent>
    </Card>
  );
}

/* Row 2b -- Platform Commission Impact */
function PlatformCommissionChart() {
  const { data, isLoading } = usePlatformCommissionImpact();
  if (isLoading || !data) return <ChartSkeleton />;
  const platforms = (data as { platform: string; gross: number; net: number }[]).map((p) => ({
    platform: PLATFORM_LABELS[p.platform] ?? p.platform, gross: p.gross, net: p.net,
  }));

  if (platforms.length === 0) {
    return (
      <Card className="rounded-xl border-slate-200">
        <CardHeader><CardTitle className="text-base text-slate-800">Platform Commission Impact</CardTitle></CardHeader>
        <CardContent><NotAvailable reason="No platform commission data. YoursTruly operates direct orders only — no aggregator commissions to report." /></CardContent>
      </Card>
    );
  }

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader><CardTitle className="text-base text-slate-800">Platform Commission Impact</CardTitle></CardHeader>
      <CardContent>
        <BarChartWidget
          data={platforms as unknown as Record<string, unknown>[]}
          config={{
            xKey: "platform", currency: true,
            bars: [
              { key: "gross", name: "Gross", color: CHART_COLOR.teal },
              { key: "net", name: "Net", color: CHART_COLOR.blue },
            ],
          }}
        />
      </CardContent>
    </Card>
  );
}

/* Row 3a -- Void Anomalies table */
function VoidAnomaliesTable() {
  const { data, isLoading } = useVoidAnomalies();
  if (isLoading || !data) return <ChartSkeleton h="h-[260px]" />;
  const staffList = (data as { staff: { staff_name: string; total_items: number; void_items: number; void_rate: number; is_anomaly: boolean }[] }).staff ?? [];
  const hasData = staffList.length > 0 && staffList.some((r) => r.staff_name && r.staff_name !== "Unknown");

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader><CardTitle className="text-base text-slate-800">Void / Modify Anomalies</CardTitle></CardHeader>
      <CardContent>
        {hasData ? (
          <TableWidget
            data={staffList.map((r) => ({ ...r, _rowClass: r.is_anomaly ? "bg-red-50 text-red-700 font-medium" : "" })) as unknown as Record<string, unknown>[]}
            config={{ columns: [
              { key: "staff_name", label: "Staff", format: "text" },
              { key: "total_items", label: "Total Items", format: "number" },
              { key: "void_items", label: "Void Items", format: "number" },
              { key: "void_rate", label: "Void Rate", format: "percent" },
            ] }}
          />
        ) : (
          <NotAvailable reason="Staff names are not captured from the PetPooja orders API. Void/modify analysis by staff is unavailable until staff assignment data is configured in PetPooja." />
        )}
      </CardContent>
    </Card>
  );
}

/* Row 3b -- Discount Abuse table */
function DiscountAbuseTable() {
  const { data, isLoading } = useDiscountAbuse();
  if (isLoading || !data) return <ChartSkeleton h="h-[260px]" />;
  const staffList = (data as { staff: { staff_name: string; discount_count: number; frequency: number; avg_discount: number; is_anomaly: boolean }[] }).staff ?? [];
  const hasData = staffList.length > 0 && staffList.some((r) => r.staff_name && r.staff_name !== "Unknown");

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader><CardTitle className="text-base text-slate-800">Discount Abuse Radar</CardTitle></CardHeader>
      <CardContent>
        {hasData ? (
          <TableWidget
            data={staffList.map((r) => ({ ...r, _rowClass: r.is_anomaly ? "bg-red-50 text-red-700 font-medium" : "" })) as unknown as Record<string, unknown>[]}
            config={{ columns: [
              { key: "staff_name", label: "Staff", format: "text" },
              { key: "discount_count", label: "Discounts", format: "number" },
              { key: "frequency", label: "Frequency", format: "percent" },
              { key: "avg_discount", label: "Avg Discount", format: "currency" },
            ] }}
          />
        ) : (
          <NotAvailable reason="Staff names are not captured from the PetPooja orders API. Discount abuse analysis by staff is unavailable until staff assignment data is configured." />
        )}
      </CardContent>
    </Card>
  );
}

/* Row 4a -- Peak Hour Leakage */
function PeakHourLeakageChart() {
  const { data, isLoading } = usePeakHourLeakage();
  if (isLoading || !data) return <ChartSkeleton />;
  const hoursList = (data as { hours: { hour: number; actual_revenue: number; potential_revenue: number }[] }).hours ?? [];
  const barData = hoursList.map((h) => ({
    hour: `${String(h.hour).padStart(2, "0")}:00`,
    actual_revenue: h.actual_revenue, potential_revenue: h.potential_revenue,
  }));
  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader><CardTitle className="text-base text-slate-800">Peak Hour Revenue Leakage</CardTitle></CardHeader>
      <CardContent>
        {barData.length > 0 ? (
          <BarChartWidget
            data={barData as unknown as Record<string, unknown>[]}
            config={{
              xKey: "hour", currency: true,
              bars: [
                { key: "actual_revenue", name: "Actual", color: CHART_COLOR.teal },
                { key: "potential_revenue", name: "Potential", color: CHART_COLOR.amber },
              ],
            }}
          />
        ) : (
          <NotAvailable reason="No hourly revenue data available for this period." />
        )}
      </CardContent>
    </Card>
  );
}

/* Row 4b -- Inventory Shrinkage table */
function InventoryShrinkageTable() {
  const { data, isLoading } = useInventoryShrinkage();
  if (isLoading || !data) return <ChartSkeleton h="h-[260px]" />;
  const rows = Array.isArray(data) ? data : [];

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader><CardTitle className="text-base text-slate-800">Inventory Shrinkage</CardTitle></CardHeader>
      <CardContent>
        {rows.length > 0 ? (
          <TableWidget
            data={data as unknown as Record<string, unknown>[]}
            config={{ columns: [
              { key: "item_name", label: "Item", format: "text" },
              { key: "theoretical", label: "Theoretical", format: "number" },
              { key: "actual", label: "Actual", format: "number" },
              { key: "shrinkage", label: "Shrinkage", format: "number" },
              { key: "shrinkage_pct", label: "Shrinkage %", format: "percent" },
            ] }}
          />
        ) : (
          <NotAvailable reason="Inventory snapshot data is not available. PetPooja inventory API endpoint needs to be configured. Contact PetPooja support for the raw material stock API." />
        )}
      </CardContent>
    </Card>
  );
}

/* Page composition */
export default function LeakagePage() {
  return (
    <Suspense>
      <PageHeader
        title="Leakage & Loss Detection"
        description="Cancellation patterns, void anomalies, inventory shrinkage, and discount abuse detection"
      >
        <PeriodSelector />
      </PageHeader>

      <LeakageStatCards />

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CancellationHeatmap />
        <PlatformCommissionChart />
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <VoidAnomaliesTable />
        <DiscountAbuseTable />
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PeakHourLeakageChart />
        <InventoryShrinkageTable />
      </div>
    </Suspense>
  );
}
