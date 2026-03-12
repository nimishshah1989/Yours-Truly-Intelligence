"use client";

import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPrice, formatNumber } from "@/lib/utils";
import { useDataStatus } from "@/hooks/use-data-status";
import type { DataGapItem, DataStatusFieldInfo, TopItem, TopVendor } from "@/hooks/use-data-status";
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  if (status === "ok") return (
    <span className="inline-flex items-center gap-1 text-emerald-700 font-medium text-sm">
      <CheckCircle className="h-4 w-4" /> Available
    </span>
  );
  if (status === "missing") return (
    <span className="inline-flex items-center gap-1 text-red-600 font-medium text-sm">
      <XCircle className="h-4 w-4" /> Missing
    </span>
  );
  if (status === "not_configured") return (
    <span className="inline-flex items-center gap-1 text-amber-600 font-medium text-sm">
      <Clock className="h-4 w-4" /> Not Configured
    </span>
  );
  return (
    <span className="inline-flex items-center gap-1 text-slate-500 font-medium text-sm">
      <AlertCircle className="h-4 w-4" /> Empty
    </span>
  );
}

function CoverageBadge({ level }: { level: string }) {
  const map: Record<string, { label: string; className: string }> = {
    full:    { label: "Full",    className: "bg-emerald-100 text-emerald-800 border-emerald-200" },
    partial: { label: "Partial", className: "bg-amber-100 text-amber-800 border-amber-200" },
    limited: { label: "Limited", className: "bg-orange-100 text-orange-800 border-orange-200" },
    none:    { label: "None",    className: "bg-red-100 text-red-700 border-red-200" },
  };
  const { label, className } = map[level] ?? map.none;
  return (
    <Badge variant="outline" className={`text-xs font-semibold ${className}`}>
      {label}
    </Badge>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    high:   "bg-red-100 text-red-700 border-red-200",
    medium: "bg-amber-100 text-amber-800 border-amber-200",
    low:    "bg-slate-100 text-slate-600 border-slate-200",
  };
  return (
    <Badge variant="outline" className={`text-xs uppercase ${map[severity] ?? map.low}`}>
      {severity}
    </Badge>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="rounded-xl border-slate-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold text-slate-800">{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Sections
// ---------------------------------------------------------------------------

function PetPoojaSection({ petpooja }: { petpooja: NonNullable<ReturnType<typeof useDataStatus>["data"]>["petpooja"] }) {
  return (
    <ChartCard title="PetPooja — Orders & Menu Data">
      <div className="space-y-4">
        {/* Core stats */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs text-slate-500 mb-1">Total Orders</p>
            <p className="text-xl font-mono font-semibold text-slate-900">{formatNumber(petpooja.orders.count)}</p>
            <p className="text-xs text-slate-400 mt-0.5">{petpooja.orders.date_from} → {petpooja.orders.date_to}</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs text-slate-500 mb-1">Order Items</p>
            <p className="text-xl font-mono font-semibold text-slate-900">{formatNumber(petpooja.order_items.count)}</p>
            <p className="text-xs text-slate-400 mt-0.5">{formatNumber(petpooja.order_items.unique_items)} unique items</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs text-slate-500 mb-1">Categories</p>
            <p className="text-xl font-mono font-semibold text-slate-900">{petpooja.order_items.categories}</p>
            <p className="text-xs text-slate-400 mt-0.5">menu categories</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs text-slate-500 mb-1">Order Types</p>
            <div className="mt-1 space-y-0.5">
              {Object.entries(petpooja.order_types).map(([type, count]) => (
                <div key={type} className="flex justify-between text-xs">
                  <span className="text-slate-600 capitalize">{type.replace("_", " ")}</span>
                  <span className="font-mono font-medium text-slate-800">{formatNumber(count)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Top items */}
        {petpooja.top_items.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Top 5 Items by Revenue</p>
            <div className="space-y-1.5">
              {(petpooja.top_items as TopItem[]).map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                  <div>
                    <span className="text-sm font-medium text-slate-800">{item.name}</span>
                    <span className="ml-2 text-xs text-slate-400">{item.category}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-mono font-semibold text-teal-700">{formatPrice(item.revenue)}</span>
                    <span className="ml-3 text-xs text-slate-400">{formatNumber(item.quantity)} sold</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Field availability */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Field Availability</p>
          <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
            {[
              { label: "Revenue & Orders", info: petpooja.orders as DataStatusFieldInfo },
              { label: "Item-Level Data", info: petpooja.order_items as DataStatusFieldInfo },
              { label: "Cost Price (COGS)", info: petpooja.cost_price },
              { label: "Staff Assignments", info: petpooja.staff_data },
              { label: "Modifier Data", info: petpooja.modifiers },
              { label: "Void Records", info: petpooja.void_records },
              { label: "Customer IDs", info: petpooja.customer_data },
              { label: "Inventory Snapshots", info: petpooja.inventory },
            ].map(({ label, info }) => (
              <div key={label} className="flex items-start justify-between px-3 py-2.5">
                <div>
                  <span className="text-sm text-slate-700">{label}</span>
                  {info.reason && (
                    <p className="text-xs text-slate-400 mt-0.5">{info.reason}</p>
                  )}
                </div>
                <StatusBadge status={info.status} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </ChartCard>
  );
}

function TallySection({ tally }: { tally: NonNullable<ReturnType<typeof useDataStatus>["data"]>["tally"] }) {
  const expSummary = tally.expense_summary;
  const expTotal = Object.values(expSummary).reduce((a, b) => a + b, 0);

  return (
    <ChartCard title="Tally — Expense & Purchase Data">
      <div className="space-y-4">
        {/* Core stats */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs text-slate-500 mb-1">Vouchers</p>
            <p className="text-xl font-mono font-semibold text-slate-900">{formatNumber(tally.vouchers.count)}</p>
            <p className="text-xs text-slate-400 mt-0.5">{tally.voucher_date_from} → {tally.voucher_date_to}</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs text-slate-500 mb-1">Purchase Invoices</p>
            <p className="text-xl font-mono font-semibold text-slate-900">{formatNumber(tally.food_purchases.count)}</p>
            <p className="text-xs text-slate-400 mt-0.5">{tally.food_purchases.vendor_count} vendors</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs text-slate-500 mb-1">Total Purchases</p>
            <p className="text-xl font-mono font-semibold text-teal-700">{formatPrice(tally.food_purchases.total_amount)}</p>
            <p className="text-xs text-slate-400 mt-0.5">food & beverage</p>
          </div>
        </div>

        {/* Expense breakdown */}
        {expTotal > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Expense Categories (all time)</p>
            <div className="space-y-2">
              {[
                { label: "Food & Beverage Cost", value: expSummary.food_cost },
                { label: "Labour", value: expSummary.labour },
                { label: "Rent & Facility", value: expSummary.rent_facility },
                { label: "Marketing", value: expSummary.marketing },
                { label: "Other Opex", value: expSummary.other },
              ].filter((e) => e.value > 0).map(({ label, value }) => {
                const pct = expTotal > 0 ? (value / expTotal * 100) : 0;
                return (
                  <div key={label}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-600">{label}</span>
                      <span className="font-mono font-medium text-slate-800">
                        {formatPrice(value)} <span className="text-slate-400">({pct.toFixed(1)}%)</span>
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-teal-500"
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Top vendors */}
        {tally.top_vendors.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Top Vendors by Spend</p>
            <div className="space-y-1.5">
              {(tally.top_vendors as TopVendor[]).map((v, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                  <div>
                    <span className="text-sm font-medium text-slate-800">{v.vendor_name}</span>
                    <span className="ml-2 text-xs text-slate-400">{v.invoice_count} invoices</span>
                  </div>
                  <span className="text-sm font-mono font-semibold text-teal-700">{formatPrice(v.total_amount)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </ChartCard>
  );
}

function DataGapsSection({ gaps }: { gaps: DataGapItem[] }) {
  const byPriority = [...gaps].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return order[a.severity] - order[b.severity];
  });

  return (
    <ChartCard title="Data Gaps — What's Missing & Why">
      <div className="space-y-3">
        <p className="text-sm text-slate-500">
          The following data fields are not available from current integrations.
          Resolving high-severity gaps will significantly improve analytics coverage.
        </p>
        <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
          {byPriority.map((gap) => (
            <div key={gap.field} className="px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-medium text-slate-800 font-mono">{gap.field}</span>
                    <SeverityBadge severity={gap.severity} />
                  </div>
                  <p className="text-xs text-slate-500">{gap.impact}</p>
                  <p className="text-xs text-slate-400 mt-0.5">Source: {gap.source}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </ChartCard>
  );
}

function AnalyticsCoverageSection({ coverage }: { coverage: Record<string, string> }) {
  const modules = [
    { key: "revenue",          label: "Revenue Intelligence" },
    { key: "menu_engineering", label: "Menu Engineering" },
    { key: "cost_margin",      label: "Cost & Margin" },
    { key: "leakage",          label: "Leakage & Loss" },
    { key: "customers",        label: "Customer Intelligence" },
    { key: "operations",       label: "Operational Efficiency" },
  ];

  const descriptions: Record<string, string> = {
    full:    "All visualizations working with real data",
    partial: "Most charts available; some require missing data fields",
    limited: "Basic views only; key metrics need additional data",
    none:    "No data available for this module",
  };

  return (
    <ChartCard title="Analytics Module Coverage">
      <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
        {modules.map(({ key, label }) => {
          const level = coverage[key] ?? "none";
          return (
            <div key={key} className="flex items-center justify-between px-4 py-3">
              <div>
                <span className="text-sm font-medium text-slate-800">{label}</span>
                <p className="text-xs text-slate-400 mt-0.5">{descriptions[level]}</p>
              </div>
              <CoverageBadge level={level} />
            </div>
          );
        })}
      </div>
    </ChartCard>
  );
}

// ---------------------------------------------------------------------------
// Main content
// ---------------------------------------------------------------------------

function DataStatusContent() {
  const { data, isLoading, error } = useDataStatus();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Skeleton className="h-[480px] rounded-xl" />
          <Skeleton className="h-[480px] rounded-xl" />
        </div>
        <Skeleton className="h-[320px] rounded-xl" />
        <Skeleton className="h-[260px] rounded-xl" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card className="rounded-xl border-slate-200">
        <CardContent className="py-12 text-center">
          <XCircle className="mx-auto h-10 w-10 text-red-400 mb-3" />
          <p className="text-sm text-slate-500">Failed to load data status. Check backend connection.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Last sync timestamps */}
      <div className="flex items-center gap-6 rounded-xl border border-slate-200 bg-white px-5 py-3">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <span className="font-medium">Last Order:</span>
          <span className="font-mono text-slate-800">{data.last_order_date ?? "—"}</span>
        </div>
        <div className="h-4 w-px bg-slate-200" />
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <span className="font-medium">Last Tally Voucher:</span>
          <span className="font-mono text-slate-800">{data.last_tally_date ?? "—"}</span>
        </div>
      </div>

      {/* Two-column: PetPooja + Tally */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <PetPoojaSection petpooja={data.petpooja} />
        <TallySection tally={data.tally} />
      </div>

      {/* Analytics coverage */}
      <AnalyticsCoverageSection coverage={data.data_coverage} />

      {/* Data gaps */}
      <DataGapsSection gaps={data.data_gaps} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page export
// ---------------------------------------------------------------------------

export default function DataPage() {
  return (
    <Suspense>
      <PageHeader
        title="Data Status"
        description="Live view of available data from PetPooja and Tally, analytics coverage, and known gaps"
      />
      <DataStatusContent />
    </Suspense>
  );
}
