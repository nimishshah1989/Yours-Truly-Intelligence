"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";

export default function DashboardsPage() {
  return (
    <>
      <PageHeader
        title="Saved Dashboards"
        description="Your custom dashboards saved from AI chat conversations"
      />
      <Card className="rounded-xl border-dashed border-slate-300">
        <CardContent className="flex h-64 items-center justify-center p-6">
          <p className="text-sm text-muted-foreground">
            Dashboard library coming in Phase 3. Save and pin dashboards from the AI chat.
          </p>
        </CardContent>
      </Card>
    </>
  );
}
