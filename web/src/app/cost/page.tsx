"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { Card, CardContent } from "@/components/ui/card";

export default function CostPage() {
  return (
    <Suspense>
      <PageHeader
        title="Cost & Margin"
        description="COGS tracking, vendor price creep, theoretical vs actual food cost, and margin waterfall"
      >
        <PeriodSelector />
      </PageHeader>
      <Card className="rounded-xl border-dashed border-slate-300">
        <CardContent className="flex h-64 items-center justify-center p-6">
          <p className="text-sm text-muted-foreground">
            Cost & margin dashboards coming in Phase 2 — 6 visualizations including vendor price creep and margin waterfall.
          </p>
        </CardContent>
      </Card>
    </Suspense>
  );
}
