"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";

export default function DigestsPage() {
  return (
    <>
      <PageHeader
        title="Digests"
        description="AI-generated daily, weekly, and monthly performance summaries"
      />
      <Card className="rounded-xl border-dashed border-slate-300">
        <CardContent className="flex h-64 items-center justify-center p-6">
          <p className="text-sm text-muted-foreground">
            Digest archive coming in Phase 4. View AI-generated performance reports with actionable insights.
          </p>
        </CardContent>
      </Card>
    </>
  );
}
