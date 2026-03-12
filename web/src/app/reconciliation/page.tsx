"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PeriodSelector } from "@/components/layout/period-selector";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ChecksTable } from "@/components/reconciliation/checks-table";
import { formatNumber, formatPrice } from "@/lib/utils";
import { api } from "@/lib/api";
import {
  useReconciliationSummary,
  useReconciliationChecks,
} from "@/hooks/use-reconciliation";
import type { ReconciliationSummary } from "@/lib/types";
import { useState } from "react";

// ---------------------------------------------------------------------------
// Stat card skeleton
// ---------------------------------------------------------------------------

function StatSkeleton() {
  return (
    <Card className="rounded-xl border-slate-200">
      <CardContent className="p-5">
        <Skeleton className="h-4 w-24 bg-slate-100" />
        <Skeleton className="mt-3 h-7 w-20 bg-slate-100" />
        <Skeleton className="mt-2 h-4 w-16 bg-slate-100" />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Summary stat cards
// ---------------------------------------------------------------------------

interface SummaryStatCardProps {
  label: string;
  value: string;
  badge?: { text: string; className: string };
}

function SummaryStatCard({ label, value, badge }: SummaryStatCardProps) {
  return (
    <Card className="rounded-xl border-slate-200 bg-white">
      <CardContent className="p-5">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {label}
        </p>
        <p className="mt-2 font-mono tabular-nums text-2xl font-semibold text-slate-900">
          {value}
        </p>
        {badge && (
          <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium border ${badge.className}`}>
            {badge.text}
          </span>
        )}
      </CardContent>
    </Card>
  );
}

function ReconciliationStats({ summary }: { summary: ReconciliationSummary }) {
  const matchPct =
    summary.total_checks > 0
      ? ((summary.matched_count / summary.total_checks) * 100).toFixed(1)
      : "0.0";

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      <SummaryStatCard
        label="Total Checks"
        value={formatNumber(summary.total_checks)}
      />
      <SummaryStatCard
        label="Matched"
        value={formatNumber(summary.matched_count)}
        badge={{ text: `${matchPct}%`, className: "bg-emerald-50 text-emerald-700 border-emerald-200" }}
      />
      <SummaryStatCard
        label="Minor Variance"
        value={formatNumber(summary.minor_variance_count)}
        badge={{ text: "Amber", className: "bg-amber-50 text-amber-700 border-amber-200" }}
      />
      <SummaryStatCard
        label="Major Variance"
        value={formatNumber(summary.major_variance_count)}
        badge={{ text: "Review", className: "bg-red-50 text-red-700 border-red-200" }}
      />
      <SummaryStatCard
        label="Missing Data"
        value={formatNumber(summary.missing_count)}
        badge={{ text: "Gap", className: "bg-slate-100 text-slate-600 border-slate-300" }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stats skeleton
// ---------------------------------------------------------------------------

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {Array.from({ length: 5 }).map((_, i) => <StatSkeleton key={i} />)}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page (inner, needs Suspense for usePeriod)
// ---------------------------------------------------------------------------

function ReconciliationPageInner() {
  const [running, setRunning] = useState(false);
  const { data: summary, isLoading: summaryLoading } = useReconciliationSummary();
  const { data: checks, isLoading: checksLoading, mutate } = useReconciliationChecks();

  async function handleRunReconciliation() {
    setRunning(true);
    try {
      await api.post("/api/reconciliation/run");
      await mutate();
    } finally {
      setRunning(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Reconciliation"
        description="PetPooja vs Tally reconciliation checks — revenue, tax, and payment mode matching"
      >
        <PeriodSelector />
        <Button
          className="bg-teal-600 hover:bg-teal-700 text-white"
          disabled={running}
          onClick={handleRunReconciliation}
        >
          {running ? "Running..." : "Run Reconciliation"}
        </Button>
      </PageHeader>

      {/* Stat cards */}
      {summaryLoading || !summary ? (
        <StatsSkeleton />
      ) : (
        <ReconciliationStats summary={summary} />
      )}

      {/* Total variance callout */}
      {summary && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-white px-5 py-3 flex items-center gap-4">
          <span className="text-sm text-muted-foreground">Total variance amount:</span>
          <span className={`font-mono tabular-nums font-semibold text-sm ${summary.total_variance_amount > 0 ? "text-red-600" : "text-emerald-600"}`}>
            {formatPrice(Math.abs(summary.total_variance_amount))}
          </span>
        </div>
      )}

      {/* Checks table */}
      <div className="mt-6">
        <Card className="rounded-xl border-slate-200 bg-white">
          <CardContent className="p-5">
            {checksLoading || !checks ? (
              <div className="space-y-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full bg-slate-100" />
                ))}
              </div>
            ) : checks.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <p className="text-sm font-medium text-slate-700">No reconciliation data</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Upload Tally XML or run reconciliation to get started.
                </p>
              </div>
            ) : (
              <ChecksTable checks={checks} onResolved={() => mutate()} />
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Page export
// ---------------------------------------------------------------------------

export default function ReconciliationPage() {
  return (
    <Suspense>
      <ReconciliationPageInner />
    </Suspense>
  );
}
