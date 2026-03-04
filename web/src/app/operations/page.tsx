"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { Card, CardContent } from "@/components/ui/card";

export default function OperationsPage() {
  return (
    <Suspense>
      <PageHeader
        title="Operational Efficiency"
        description="Revenue per seat-hour, fulfillment times, staff efficiency, and SLA compliance"
      >
        <PeriodSelector />
      </PageHeader>
      <Card className="rounded-xl border-dashed border-slate-300">
        <CardContent className="flex h-64 items-center justify-center p-6">
          <p className="text-sm text-muted-foreground">
            Operations dashboards coming in Phase 2 — 5 visualizations including seat-hour heatmap and staff efficiency ranking.
          </p>
        </CardContent>
      </Card>
    </Suspense>
  );
}
