"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Pin, PinOff } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { WidgetRenderer } from "@/components/widgets/widget-renderer";
import { useDashboard } from "@/hooks/use-dashboards";
import { api } from "@/lib/api";
import type { WidgetSpec } from "@/lib/types";

// ---------------------------------------------------------------------------
// Skeleton loader
// ---------------------------------------------------------------------------

function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <Card key={i} className="rounded-xl border-slate-200">
          <CardHeader>
            <Skeleton className="h-5 w-40 bg-slate-100" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-[200px] w-full bg-slate-100" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Single widget card
// ---------------------------------------------------------------------------

function WidgetCard({ widget }: { widget: WidgetSpec }) {
  const spanClass =
    widget.span === 3
      ? "md:col-span-2 xl:col-span-3"
      : widget.span === 2
        ? "md:col-span-2"
        : "";

  return (
    <div className={spanClass}>
      <Card className="rounded-xl border-slate-200 bg-white h-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-slate-800">
            {widget.title}
          </CardTitle>
          {widget.subtitle && (
            <p className="text-xs text-muted-foreground">{widget.subtitle}</p>
          )}
        </CardHeader>
        <CardContent>
          <WidgetRenderer widget={widget} />
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page inner
// ---------------------------------------------------------------------------

interface PageProps {
  params: Promise<{ id: string }>;
}

function DashboardDetailInner({ id }: { id: number }) {
  const [pinning, setPinning] = useState(false);
  const { data: dashboard, isLoading, mutate } = useDashboard(id);

  async function handlePinToggle() {
    if (!dashboard) return;
    setPinning(true);
    try {
      await api.post(`/api/dashboards/${id}/pin`);
      await mutate();
    } finally {
      setPinning(false);
    }
  }

  if (isLoading) {
    return (
      <>
        <div className="flex items-center justify-between gap-4 pb-6">
          <div className="flex items-center gap-3">
            <Skeleton className="h-8 w-8 bg-slate-100 rounded-lg" />
            <Skeleton className="h-6 w-48 bg-slate-100" />
          </div>
          <Skeleton className="h-9 w-24 bg-slate-100" />
        </div>
        <DashboardSkeleton />
      </>
    );
  }

  if (!dashboard) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-sm font-medium text-slate-700">Dashboard not found</p>
        <Link href="/dashboards">
          <Button variant="outline" className="mt-4">
            Back to Dashboards
          </Button>
        </Link>
      </div>
    );
  }

  const widgets: WidgetSpec[] = Array.isArray(dashboard.widget_specs)
    ? dashboard.widget_specs
    : [];

  return (
    <>
      <PageHeader title={dashboard.title} description={dashboard.description ?? undefined}>
        <Link href="/dashboards">
          <Button variant="outline" size="sm" className="gap-1.5">
            <ArrowLeft className="h-4 w-4" />
            Dashboards
          </Button>
        </Link>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          disabled={pinning}
          onClick={handlePinToggle}
        >
          {dashboard.is_pinned ? (
            <>
              <PinOff className="h-4 w-4" />
              Unpin
            </>
          ) : (
            <>
              <Pin className="h-4 w-4" />
              Pin
            </>
          )}
        </Button>
      </PageHeader>

      {widgets.length === 0 ? (
        <Card className="rounded-xl border-dashed border-slate-300">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-sm font-medium text-slate-700">No widgets saved for this dashboard</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Use the AI chat to generate insights and save them to this dashboard.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {widgets.map((widget, idx) => (
            <WidgetCard key={idx} widget={widget} />
          ))}
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Page export (unwrap async params)
// ---------------------------------------------------------------------------

export default function DashboardDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const numericId = parseInt(id, 10);

  if (isNaN(numericId)) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-sm font-medium text-slate-700">Invalid dashboard ID</p>
        <Link href="/dashboards">
          <Button variant="outline" className="mt-4">
            Back to Dashboards
          </Button>
        </Link>
      </div>
    );
  }

  return <DashboardDetailInner id={numericId} />;
}
