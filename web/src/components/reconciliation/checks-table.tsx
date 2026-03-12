"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { formatPrice, formatDate } from "@/lib/utils";
import { api } from "@/lib/api";
import type { ReconciliationCheck, ReconciliationStatus } from "@/lib/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

const STATUS_CONFIG: Record<
  ReconciliationStatus,
  { label: string; className: string }
> = {
  matched: { label: "Matched", className: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  minor_variance: { label: "Minor Variance", className: "bg-amber-50 text-amber-700 border-amber-200" },
  major_variance: { label: "Major Variance", className: "bg-red-50 text-red-700 border-red-200" },
  missing: { label: "Missing", className: "bg-slate-50 text-slate-600 border-slate-300" },
};

const CHECK_TYPE_LABELS: Record<string, string> = {
  revenue_match: "Revenue Match",
  payment_mode_match: "Payment Mode",
  tax_match: "Tax Match",
  data_gap: "Data Gap",
};

function StatusBadge({ status }: { status: ReconciliationStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.missing;
  return (
    <Badge variant="outline" className={cn("text-xs font-medium", cfg.className)}>
      {cfg.label}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ChecksTableProps {
  checks: ReconciliationCheck[];
  onResolved: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ChecksTable({ checks, onResolved }: ChecksTableProps) {
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [resolvingId, setResolvingId] = useState<number | null>(null);

  const filtered = checks.filter((c) => {
    const matchType = typeFilter === "all" || c.check_type === typeFilter;
    const matchStatus = statusFilter === "all" || c.status === statusFilter;
    return matchType && matchStatus;
  });

  async function handleResolve(check: ReconciliationCheck) {
    if (check.resolved) return;
    setResolvingId(check.id);
    try {
      await api.put(`/api/reconciliation/checks/${check.id}/resolve`);
      onResolved();
    } finally {
      setResolvingId(null);
    }
  }

  return (
    <div>
      {/* Filter row */}
      <div className="mb-4 flex items-center gap-3">
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Check type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="revenue_match">Revenue Match</SelectItem>
            <SelectItem value="payment_mode_match">Payment Mode</SelectItem>
            <SelectItem value="tax_match">Tax Match</SelectItem>
            <SelectItem value="data_gap">Data Gap</SelectItem>
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="matched">Matched</SelectItem>
            <SelectItem value="minor_variance">Minor Variance</SelectItem>
            <SelectItem value="major_variance">Major Variance</SelectItem>
            <SelectItem value="missing">Missing</SelectItem>
          </SelectContent>
        </Select>

        <span className="ml-auto text-xs text-muted-foreground font-mono tabular-nums">
          {filtered.length} of {checks.length} rows
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Date</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Check Type</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">PetPooja</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Tally</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Variance</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Var %</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Resolved</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-sm text-muted-foreground">
                  No checks match the selected filters.
                </td>
              </tr>
            ) : (
              filtered.map((check) => (
                <tr key={check.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-mono tabular-nums text-slate-700 whitespace-nowrap">
                    {formatDate(check.check_date)}
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {CHECK_TYPE_LABELS[check.check_type] ?? check.check_type}
                    {check.notes && (
                      <p className="text-xs text-muted-foreground mt-0.5 truncate max-w-[160px]">
                        {check.notes}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-700">
                    {formatPrice(check.pp_value)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-700">
                    {formatPrice(check.tally_value)}
                  </td>
                  <td className={cn(
                    "px-4 py-3 text-right font-mono tabular-nums",
                    check.variance > 0 ? "text-red-600" : check.variance < 0 ? "text-emerald-600" : "text-slate-500"
                  )}>
                    {check.variance > 0 ? "+" : ""}{formatPrice(check.variance)}
                  </td>
                  <td className={cn(
                    "px-4 py-3 text-right font-mono tabular-nums",
                    Math.abs(check.variance_pct) > 5 ? "text-red-600" : Math.abs(check.variance_pct) > 1 ? "text-amber-600" : "text-slate-500"
                  )}>
                    {check.variance_pct >= 0 ? "+" : ""}{check.variance_pct.toFixed(2)}%
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={check.status} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Checkbox
                      checked={check.resolved}
                      disabled={check.resolved || resolvingId === check.id}
                      onCheckedChange={() => handleResolve(check)}
                      aria-label="Mark resolved"
                    />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
