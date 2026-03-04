"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { Card, CardContent } from "@/components/ui/card";

export default function LeakagePage() {
  return (
    <Suspense>
      <PageHeader
        title="Leakage & Loss Detection"
        description="Cancellation patterns, void anomalies, inventory shrinkage, and discount abuse detection"
      >
        <PeriodSelector />
      </PageHeader>
      <Card className="rounded-xl border-dashed border-slate-300">
        <CardContent className="flex h-64 items-center justify-center p-6">
          <p className="text-sm text-muted-foreground">
            Leakage detection dashboards coming in Phase 2 — 6 visualizations including void anomaly detection and discount abuse radar.
          </p>
        </CardContent>
      </Card>
    </Suspense>
  );
}
