"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";

export default function ChatPage() {
  return (
    <>
      <PageHeader
        title="AI Chat"
        description="Ask anything about your restaurant data in plain English"
      />
      <Card className="rounded-xl border-dashed border-slate-300">
        <CardContent className="flex h-96 items-center justify-center p-6">
          <p className="text-sm text-muted-foreground">
            Claude-powered conversational analytics coming in Phase 3.
          </p>
        </CardContent>
      </Card>
    </>
  );
}
