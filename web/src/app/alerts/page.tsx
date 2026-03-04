"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";

export default function AlertsPage() {
  return (
    <>
      <PageHeader
        title="Alerts"
        description="Automated daily, weekly, and monthly alert rules and history"
      />
      <Card className="rounded-xl border-dashed border-slate-300">
        <CardContent className="flex h-64 items-center justify-center p-6">
          <p className="text-sm text-muted-foreground">
            Alert management coming in Phase 4. Configure automated revenue, leakage, and inventory alerts.
          </p>
        </CardContent>
      </Card>
    </>
  );
}
