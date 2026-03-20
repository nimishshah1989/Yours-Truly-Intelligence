"use client";

import { Suspense, useMemo } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { StatCard } from "@/components/widgets/stat-card";
import { LineChartWidget } from "@/components/widgets/line-chart";
import { BarChartWidget } from "@/components/widgets/bar-chart";
import { WaterfallChartWidget } from "@/components/widgets/waterfall-chart";
import { TableWidget } from "@/components/widgets/table-widget";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPrice } from "@/lib/utils";
import {
  useCogsTrend, useVendorPriceCreep, useFoodCostGap,
  usePurchaseCalendar, useMarginWaterfall, useIngredientVolatility,
  usePortionDrift,
} from "@/hooks/use-cost";
import type { StatCardData } from "@/lib/types";

// ---------------------------------------------------------------------------
// Local types
// ---------------------------------------------------------------------------

interface CogsDayRow { date: string; cogs: number; revenue: number; cogs_pct: number }
interface PurchaseCalRow { date: string; total_spend: number; vendor_count: number; orders: number }
interface VendorCreepData { items: string[]; data: Record<string, unknown>[] }

// ---------------------------------------------------------------------------
// Stats derived from loaded data
// ---------------------------------------------------------------------------

function deriveStats(cogs: CogsDayRow[] | undefined, purch: PurchaseCalRow[] | undefined): StatCardData[] {
  if (!cogs?.length) return [];
  const cogsTotal = cogs.reduce((s, r) => s + r.cogs, 0);
  const revTotal = cogs.reduce((s, r) => s + r.revenue, 0);
  const avgPct = cogs.reduce((s, r) => s + r.cogs_pct, 0) / cogs.length;
  const spend = purch?.reduce((s, r) => s + r.total_spend, 0) ?? 0;
  return [
    { label: "COGS Total", value: formatPrice(cogsTotal), changeLabel: `of ${formatPrice(revTotal)} revenue` },
    { label: "COGS %", value: `${avgPct.toFixed(1)}%`, changeLabel: "avg across period" },
    { label: "Avg Margin", value: `${(100 - avgPct).toFixed(1)}%`, changeLabel: "revenue minus COGS" },
    { label: "Purchase Spend", value: formatPrice(spend), changeLabel: purch ? `${purch.length} purchase days` : undefined },
  ];
}

// ---------------------------------------------------------------------------
// Skeleton helpers
// ---------------------------------------------------------------------------

function StatSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-24 rounded-xl bg-slate-100" />
      ))}
    </div>
  );
}

function ChartSkeleton({ className }: { className?: string }) {
  return <Skeleton className={`h-[340px] rounded-xl bg-slate-100 ${className ?? ""}`} />;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function CostPage() {
  return (
    <Suspense fallback={<StatSkeleton />}>
      <CostDashboard />
    </Suspense>
  );
}

function CostDashboard() {
  const { data: cogsTrendRaw } = useCogsTrend();
  const { data: vendorCreepRaw } = useVendorPriceCreep();
  const { data: foodCostGapRaw } = useFoodCostGap();
  const { data: purchaseCalRaw } = usePurchaseCalendar();
  const { data: waterfallRaw } = useMarginWaterfall();
  const { data: volatilityRaw } = useIngredientVolatility();
  const { data: portionDriftRaw } = usePortionDrift();
  const portionDrift = portionDriftRaw?.data;

  // Unwrap the { data: [...] } wrapper that all these endpoints return
  const cogsTrend = cogsTrendRaw?.data as CogsDayRow[] | undefined;
  const vendorCreep = vendorCreepRaw as VendorCreepData | undefined;
  const foodCostGap = foodCostGapRaw?.data as Record<string, unknown>[] | undefined;
  const purchaseCal = purchaseCalRaw?.data as PurchaseCalRow[] | undefined;
  const waterfall = waterfallRaw?.data as Record<string, unknown>[] | undefined;
  const volatility = volatilityRaw?.data as Record<string, unknown>[] | undefined;

  const stats = useMemo(() => deriveStats(cogsTrend, purchaseCal), [cogsTrend, purchaseCal]);
  const vendorLines = useMemo(
    () => vendorCreep?.items.map((item) => ({ key: item, name: item })) ?? [],
    [vendorCreep],
  );

  return (
    <>
      <PageHeader
        title="Cost & Margin"
        description="COGS tracking, vendor price creep, theoretical vs actual food cost, and margin waterfall"
      >
        <PeriodSelector />
      </PageHeader>

      {/* Row 1 — Stat cards */}
      {stats.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map((s) => <StatCard key={s.label} data={s} />)}
        </div>
      ) : (
        <StatSkeleton />
      )}

      {/* Row 2 — COGS Trend (2/3) + Ingredient Volatility (1/3) */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 rounded-xl border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-slate-800">COGS Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {cogsTrend ? (
              <LineChartWidget
                data={cogsTrend as unknown as Record<string, unknown>[]}
                config={{
                  xKey: "date",
                  lines: [{ key: "cogs", name: "COGS" }, { key: "revenue", name: "Revenue" }],
                  currency: true,
                }}
              />
            ) : (
              <ChartSkeleton />
            )}
          </CardContent>
        </Card>
        <Card className="rounded-xl border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-slate-800">Ingredient Volatility</CardTitle>
          </CardHeader>
          <CardContent>
            {volatility ? (
              <BarChartWidget
                data={volatility}
                config={{ xKey: "item_name", bars: [{ key: "volatility_pct", name: "Volatility %" }] }}
              />
            ) : (
              <ChartSkeleton />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 3 — Margin Waterfall (full width) */}
      <div className="mt-6">
        <Card className="rounded-xl border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-slate-800">
              Margin Waterfall — Revenue to Net Margin
            </CardTitle>
          </CardHeader>
          <CardContent>
            {waterfall ? (
              <WaterfallChartWidget data={waterfall} config={{ currency: true }} />
            ) : (
              <ChartSkeleton />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 4 — Vendor Price Creep (1/2) + Purchase Calendar (1/2) */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="rounded-xl border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-slate-800">Vendor Price Creep</CardTitle>
          </CardHeader>
          <CardContent>
            {vendorCreep ? (
              <LineChartWidget
                data={vendorCreep.data}
                config={{ xKey: "week", lines: vendorLines, currency: true }}
              />
            ) : (
              <ChartSkeleton />
            )}
          </CardContent>
        </Card>
        <Card className="rounded-xl border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-slate-800">Purchase Calendar</CardTitle>
          </CardHeader>
          <CardContent>
            {purchaseCal ? (
              <BarChartWidget
                data={purchaseCal as unknown as Record<string, unknown>[]}
                config={{ xKey: "date", bars: [{ key: "total_spend", name: "Spend" }], currency: true }}
              />
            ) : (
              <ChartSkeleton />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 5 — Food Cost Gap Table (full width) */}
      <div className="mt-6">
        <Card className="rounded-xl border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-slate-800">
              Theoretical vs Actual Food Cost
            </CardTitle>
          </CardHeader>
          <CardContent>
            {foodCostGap ? (
              <TableWidget
                data={foodCostGap}
                config={{
                  columns: [
                    { key: "item_name", label: "Item", format: "text" },
                    { key: "theoretical", label: "Theoretical Cost", format: "currency" },
                    { key: "actual", label: "Actual Cost", format: "currency" },
                    { key: "gap", label: "Gap", format: "currency" },
                    { key: "gap_pct", label: "Gap %", format: "percent" },
                  ],
                  sortable: true,
                }}
              />
            ) : (
              <ChartSkeleton className="h-[200px]" />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 6 — Portion Drift (full width, conditional) */}
      {portionDrift && portionDrift.length > 0 && (
        <div className="mt-6">
          <Card className="rounded-xl border-slate-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold text-slate-800">
                Portion Drift — Top Drifting Ingredients
              </CardTitle>
              <p className="text-xs text-slate-500">
                Actual vs theoretical consumption gap. Positive = over-consumption.
              </p>
            </CardHeader>
            <CardContent>
              <BarChartWidget
                data={portionDrift as unknown as Record<string, unknown>[]}
                config={{
                  xKey: "ingredient",
                  bars: [{ key: "drift_pct", name: "Drift %", color: "#ef4444" }],
                }}
              />
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
