"use client";

import { BarChartWidget } from "@/components/widgets/bar-chart";
import { ParetoChartWidget } from "@/components/widgets/pareto-chart";
import { CohortTableWidget } from "@/components/widgets/cohort-table";
import { TableWidget } from "@/components/widgets/table-widget";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_COLOR } from "@/lib/constants";
import { ChartSkeleton } from "./customer-stats";
import {
  useCohorts,
  useChurnRisk,
  useLtvDistribution,
  useCustomerConcentration,
} from "@/hooks/use-customers";

// ---------------------------------------------------------------------------
// Cohort Retention table
// ---------------------------------------------------------------------------

export function CohortRetention() {
  const { data, isLoading } = useCohorts();

  if (isLoading || !data) return <ChartSkeleton className="h-[240px]" />;

  const cohortData = data as {
    cohorts: { label: string; size: number; retention: number[] }[];
  };

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Cohort Retention</CardTitle>
      </CardHeader>
      <CardContent>
        <CohortTableWidget data={cohortData as unknown as Record<string, unknown>} />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// LTV Distribution histogram
// ---------------------------------------------------------------------------

export function LtvDistribution() {
  const { data, isLoading } = useLtvDistribution();

  if (isLoading || !data) return <ChartSkeleton />;

  const buckets = data as { bucket: string; count: number }[];

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">LTV Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <BarChartWidget
          data={buckets as unknown as Record<string, unknown>[]}
          config={{
            xKey: "bucket",
            bars: [{ key: "count", name: "Customers", color: CHART_COLOR.violet }],
          }}
        />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Revenue Concentration (Pareto)
// ---------------------------------------------------------------------------

export function CustomerConcentration() {
  const { data, isLoading } = useCustomerConcentration();

  if (isLoading || !data) return <ChartSkeleton className="h-[320px]" />;

  const customers = data as { name: string; revenue: number; cumulative_pct: number }[];

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Revenue Concentration</CardTitle>
      </CardHeader>
      <CardContent>
        <ParetoChartWidget
          data={customers as unknown as Record<string, unknown>[]}
          config={{ nameKey: "name", valueKey: "revenue", currency: true }}
        />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Churn Risk table
// ---------------------------------------------------------------------------

export function ChurnRiskTable() {
  const { data, isLoading } = useChurnRisk();

  if (isLoading || !data) return <ChartSkeleton className="h-[240px]" />;

  const risks = data as Record<string, unknown>[];

  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <CardTitle className="text-base text-slate-800">Churn Risk</CardTitle>
      </CardHeader>
      <CardContent>
        <TableWidget
          data={risks}
          config={{
            sortable: true,
            columns: [
              { key: "name", label: "Customer", format: "text" },
              { key: "total_visits", label: "Visits", format: "number" },
              { key: "total_spend", label: "Total Spend", format: "currency" },
              { key: "last_visit", label: "Last Visit", format: "text" },
              { key: "days_since", label: "Days Since", format: "number" },
              { key: "risk_score", label: "Risk Score", format: "number" },
            ],
          }}
        />
      </CardContent>
    </Card>
  );
}
