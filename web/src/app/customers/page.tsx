"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { Card, CardContent } from "@/components/ui/card";

export default function CustomersPage() {
  return (
    <Suspense>
      <PageHeader
        title="Customer Intelligence"
        description="RFM segmentation, cohort retention, churn prediction, and LTV analysis"
      >
        <PeriodSelector />
      </PageHeader>
      <Card className="rounded-xl border-dashed border-slate-300">
        <CardContent className="flex h-64 items-center justify-center p-6">
          <p className="text-sm text-muted-foreground">
            Customer intelligence dashboards coming in Phase 2 — 6 visualizations including RFM segmentation and cohort retention.
          </p>
        </CardContent>
      </Card>
    </Suspense>
  );
}
