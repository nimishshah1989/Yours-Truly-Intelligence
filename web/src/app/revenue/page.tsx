"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { Card, CardContent } from "@/components/ui/card";

export default function RevenuePage() {
  return (
    <Suspense>
      <PageHeader
        title="Revenue Intelligence"
        description="Revenue trends, heatmaps, concentration analysis, and platform profitability"
      >
        <PeriodSelector />
      </PageHeader>
      <Card className="rounded-xl border-dashed border-slate-300">
        <CardContent className="flex h-64 items-center justify-center p-6">
          <p className="text-sm text-muted-foreground">
            Revenue dashboards coming in Phase 2 — 7 visualizations including revenue heatmap, Pareto analysis, and platform profitability.
          </p>
        </CardContent>
      </Card>
    </Suspense>
  );
}
