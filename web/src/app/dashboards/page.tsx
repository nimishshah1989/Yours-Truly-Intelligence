"use client";

import Link from "next/link";
import { LayoutDashboard, Pin } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboards } from "@/hooks/use-dashboards";
import { formatDate } from "@/lib/utils";
import type { SavedDashboard } from "@/lib/types";

// ---------------------------------------------------------------------------
// Dashboard card
// ---------------------------------------------------------------------------

function DashboardCard({ dashboard }: { dashboard: SavedDashboard }) {
  return (
    <Link href={`/dashboards/${dashboard.id}`}>
      <Card className="h-full cursor-pointer rounded-xl border-slate-200 transition-all hover:border-teal-300 hover:shadow-sm">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="line-clamp-2 text-sm font-semibold text-slate-800">
              {dashboard.title}
            </CardTitle>
            {dashboard.is_pinned && (
              <Badge
                variant="secondary"
                className="shrink-0 gap-1 bg-teal-50 text-xs text-teal-700"
              >
                <Pin className="h-3 w-3" />
                Pinned
              </Badge>
            )}
          </div>
          {dashboard.description && (
            <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
              {dashboard.description}
            </p>
          )}
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            {formatDate(dashboard.created_at)}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}

function CardSkeleton() {
  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader>
        <Skeleton className="h-4 w-48 bg-slate-100" />
        <Skeleton className="mt-2 h-3 w-32 bg-slate-100" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-3 w-24 bg-slate-100" />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardsPage() {
  const { data, isLoading } = useDashboards();
  const dashboards = data ?? [];

  return (
    <>
      <PageHeader
        title="Saved Dashboards"
        description="Dashboards saved from your AI chat conversations"
      />

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : dashboards.length === 0 ? (
        <Card className="rounded-xl border-dashed border-slate-300">
          <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <LayoutDashboard className="h-8 w-8 text-slate-300" />
            <div>
              <p className="text-sm font-medium text-slate-700">
                No saved dashboards yet
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Ask the AI to analyse your data, then save the result as a
                dashboard.
              </p>
            </div>
            <Link href="/chat">
              <Button size="sm" className="mt-1">
                Open AI Chat
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {dashboards.map((d) => (
            <DashboardCard key={d.id} dashboard={d} />
          ))}
        </div>
      )}
    </>
  );
}
