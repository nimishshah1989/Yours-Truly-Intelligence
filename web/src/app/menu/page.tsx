"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { Card, CardContent } from "@/components/ui/card";

export default function MenuPage() {
  return (
    <Suspense>
      <PageHeader
        title="Menu Engineering"
        description="BCG matrix, item affinity, cannibalization detection, and category mix analysis"
      >
        <PeriodSelector />
      </PageHeader>
      <Card className="rounded-xl border-dashed border-slate-300">
        <CardContent className="flex h-64 items-center justify-center p-6">
          <p className="text-sm text-muted-foreground">
            Menu engineering dashboards coming in Phase 2 — 7 visualizations including BCG matrix, affinity map, and cannibalization detector.
          </p>
        </CardContent>
      </Card>
    </Suspense>
  );
}
