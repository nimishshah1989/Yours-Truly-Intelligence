"use client";

import { Suspense, useMemo } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { StatCard } from "@/components/widgets/stat-card";
import { BarChartWidget } from "@/components/widgets/bar-chart";
import { LineChartWidget } from "@/components/widgets/line-chart";
import { QuadrantChartWidget } from "@/components/widgets/quadrant-chart";
import { NetworkGraphWidget } from "@/components/widgets/network-graph";
import { TableWidget } from "@/components/widgets/table-widget";
import { ChartSkeleton, StatSkeleton } from "@/components/widgets/dashboard-skeletons";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/utils";
import { useTopItems, useBcgMatrix, useAffinity, useCategoryMix, useDeadSkus } from "@/hooks/use-menu";

// ---------------------------------------------------------------------------
// Type helpers — narrow the unknown SWR responses
// ---------------------------------------------------------------------------

interface TopItemRow { name: string; category: string; revenue: number; quantity: number }
interface TopItemsResponse {
  by_revenue: TopItemRow[];
  by_quantity: TopItemRow[];
  total_unique: number;
  total_quantity: number;
}

// ---------------------------------------------------------------------------
// Chart wrapper — removes repeated Card/Header boilerplate
// ---------------------------------------------------------------------------

function ChartCard({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <Card className={`rounded-xl border-slate-200 ${className ?? ""}`}>
      <CardHeader>
        <CardTitle className="text-base font-semibold text-slate-800">{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Dashboard content
// ---------------------------------------------------------------------------

function MenuDashboard() {
  const { data: topItems, isLoading: loadingTop } = useTopItems();
  const { data: bcgData, isLoading: loadingBcg } = useBcgMatrix();
  const { data: affinityData, isLoading: loadingAffinity } = useAffinity();
  const { data: categoryMix, isLoading: loadingCategory } = useCategoryMix();
  const { data: deadSkus, isLoading: loadingDead } = useDeadSkus();

  const top = topItems as TopItemsResponse | undefined;
  const bcgRows = (bcgData as Record<string, unknown>[] | undefined) ?? [];
  const categoryMixRows = (categoryMix as Record<string, unknown>[] | undefined) ?? [];
  const deadSkuRows = (deadSkus as Record<string, unknown>[] | undefined) ?? [];
  const affinityGraph = affinityData as Record<string, unknown> | undefined;

  // Stat values from backend (total_unique covers ALL items, not just top N)
  const totalSold = top?.total_quantity ?? 0;
  const uniqueItems = top?.total_unique ?? 0;

  // Category names for the line chart — exclude the xKey
  const categoryLines = useMemo(() => {
    if (categoryMixRows.length === 0) return [];
    return Object.keys(categoryMixRows[0])
      .filter((k) => k !== "week")
      .map((cat) => ({ key: cat, name: cat }));
  }, [categoryMixRows]);

  return (
    <div className="space-y-6">
      {/* Row 1 — Stat Cards */}
      <div className="grid grid-cols-2 gap-4">
        {loadingTop ? (
          <><StatSkeleton /><StatSkeleton /></>
        ) : (
          <>
            <StatCard data={{ label: "Total Items Sold", value: formatNumber(totalSold), changeLabel: "in selected period" }} />
            <StatCard data={{ label: "Unique Items Ordered", value: formatNumber(uniqueItems), changeLabel: "distinct menu items" }} />
          </>
        )}
      </div>

      {/* Row 2 — Top by Revenue + Top by Quantity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {loadingTop ? (
          <><ChartSkeleton /><ChartSkeleton /></>
        ) : (
          <>
            <ChartCard title="Top Items by Revenue">
              <BarChartWidget
                data={(top?.by_revenue ?? []).slice(0, 10).map((item) => ({
                  ...item,
                  name: item.name.length > 18 ? item.name.slice(0, 16) + "…" : item.name,
                })) as unknown as Record<string, unknown>[]}
                config={{ xKey: "name", bars: [{ key: "revenue", name: "Revenue" }], currency: true, rotateLabels: true }}
              />
            </ChartCard>
            <ChartCard title="Top Items by Quantity">
              <BarChartWidget
                data={(top?.by_quantity ?? []).slice(0, 10).map((item) => ({
                  ...item,
                  name: item.name.length > 18 ? item.name.slice(0, 16) + "…" : item.name,
                })) as unknown as Record<string, unknown>[]}
                config={{ xKey: "name", bars: [{ key: "quantity", name: "Qty Sold" }], rotateLabels: true }}
              />
            </ChartCard>
          </>
        )}
      </div>

      {/* Row 3 — BCG Matrix (2/3) + Category Mix Trend (1/3) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {loadingBcg ? (
          <div className="lg:col-span-2"><ChartSkeleton height="h-[400px]" /></div>
        ) : (
          <ChartCard title="BCG Matrix — Popularity vs Revenue" className="lg:col-span-2">
            <QuadrantChartWidget
              data={bcgRows}
              config={{
                xKey: "popularity",
                yKey: "revenue_pct",
                nameKey: "name",
                sizeKey: "revenue",
                xLabel: "Popularity (qty sold)",
                yLabel: "Revenue Contribution (%)",
                quadrantLabels: { topLeft: "Premium", topRight: "Stars", bottomLeft: "Dogs", bottomRight: "Drivers" },
              }}
            />
          </ChartCard>
        )}

        {loadingCategory ? (
          <ChartSkeleton />
        ) : (
          <ChartCard title="Category Mix Trend">
            <LineChartWidget data={categoryMixRows} config={{ xKey: "week", lines: categoryLines }} />
          </ChartCard>
        )}
      </div>

      {/* Row 4 — Item Affinity Map (full width) */}
      {loadingAffinity ? (
        <ChartSkeleton height="h-[420px]" />
      ) : (
        <ChartCard title="Item Affinity Map">
          <NetworkGraphWidget data={(affinityGraph ?? { nodes: [], edges: [] }) as Record<string, unknown>} />
        </ChartCard>
      )}

      {/* Row 5 — Dead SKU Table (full width) */}
      {loadingDead ? (
        <ChartSkeleton height="h-[260px]" />
      ) : (
        <ChartCard title="Dead SKUs — Low / No Orders">
          <TableWidget
            data={deadSkuRows}
            config={{
              columns: [
                { key: "name", label: "Item", format: "text" },
                { key: "category", label: "Category", format: "text" },
                { key: "base_price", label: "Price", format: "currency" },
                { key: "orders_in_period", label: "Orders", format: "number" },
              ],
              sortable: true,
            }}
          />
        </ChartCard>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page export
// ---------------------------------------------------------------------------

export default function MenuPage() {
  return (
    <Suspense>
      <PageHeader
        title="Menu Engineering"
        description="BCG matrix, item affinity, cannibalization detection, and category mix analysis"
      >
        <PeriodSelector />
      </PageHeader>
      <MenuDashboard />
    </Suspense>
  );
}
