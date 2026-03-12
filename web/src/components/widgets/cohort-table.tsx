"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";
import { CHART_COLOR } from "@/lib/constants";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Cohort {
  label: string;
  size: number;
  retention: number[];
}

interface CohortData {
  cohorts: Cohort[];
}

interface CohortConfig {
  cohortLabel?: string;
  periodLabel?: string;
}

interface CohortTableProps {
  data: Record<string, unknown>;
  config?: CohortConfig;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Convert hex to RGB for interpolation */
function hexToRgb(hex: string): [number, number, number] {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return [20, 184, 166];
  return [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)];
}

/** Map retention 0-100% to white..teal-500 */
function retentionColor(pct: number): string {
  const ratio = Math.max(0, Math.min(1, pct / 100));
  const [r, g, b] = hexToRgb(CHART_COLOR.teal);
  const fr = Math.round(255 - (255 - r) * ratio);
  const fg = Math.round(255 - (255 - g) * ratio);
  const fb = Math.round(255 - (255 - b) * ratio);
  return `rgb(${fr}, ${fg}, ${fb})`;
}

/** Decide text color based on retention intensity */
function retentionTextClass(pct: number): string {
  if (pct >= 60) return "text-white";
  if (pct >= 30) return "text-slate-800";
  return "text-slate-600";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CohortTableWidget({ data, config }: CohortTableProps) {
  const cohortLabel = config?.cohortLabel ?? "Cohort";
  const periodLabel = config?.periodLabel ?? "Month";
  const cohortData = data as unknown as CohortData;
  const cohorts = cohortData?.cohorts ?? [];

  // Max number of periods across all cohorts
  const maxPeriods = useMemo(
    () => cohorts.reduce((max, c) => Math.max(max, c.retention.length), 0),
    [cohorts],
  );

  if (!cohorts.length) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50">
        <p className="text-sm text-muted-foreground">No cohort data available</p>
      </div>
    );
  }

  // Generate period headers
  const periodHeaders = Array.from({ length: maxPeriods }, (_, i) => `${periodLabel} ${i}`);

  return (
    <div className="overflow-auto rounded-lg border border-slate-200">
      <table className="w-full border-collapse text-sm">
        <thead className="sticky top-0 z-10 bg-slate-50">
          <tr>
            <th className="sticky left-0 z-20 min-w-[100px] border-b border-r border-slate-200 bg-slate-50 px-3 py-2.5 text-left text-xs font-semibold text-slate-600">
              {cohortLabel}
            </th>
            <th className="sticky left-[100px] z-20 min-w-[64px] border-b border-r border-slate-200 bg-slate-50 px-3 py-2.5 text-right text-xs font-semibold text-slate-600">
              Size
            </th>
            {periodHeaders.map((header) => (
              <th
                key={header}
                className="min-w-[64px] border-b border-slate-200 px-2 py-2.5 text-center text-xs font-semibold text-slate-600"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cohorts.map((cohort) => (
            <tr key={cohort.label} className="hover:bg-slate-50/50">
              {/* Cohort label — sticky */}
              <td className="sticky left-0 z-10 border-b border-r border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 whitespace-nowrap">
                {cohort.label}
              </td>
              {/* Cohort size — sticky */}
              <td className="sticky left-[100px] z-10 border-b border-r border-slate-200 bg-white px-3 py-2 text-right font-mono text-xs tabular-nums text-slate-700">
                {cohort.size.toLocaleString("en-IN")}
              </td>
              {/* Retention cells */}
              {Array.from({ length: maxPeriods }, (_, i) => {
                const value = cohort.retention[i];
                const hasValue = value !== undefined;
                return (
                  <td
                    key={`${cohort.label}-${i}`}
                    className={cn(
                      "border-b border-slate-100 px-2 py-2 text-center font-mono text-xs tabular-nums",
                      hasValue ? retentionTextClass(value) : "text-transparent",
                    )}
                    style={hasValue ? { backgroundColor: retentionColor(value) } : undefined}
                  >
                    {hasValue ? `${value}%` : ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
