"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useRestaurant } from "@/hooks/use-restaurant";
import { useMoneyFound } from "@/hooks/use-home";
import {
  useIntelligenceSummary,
  useIntelligenceRevenue,
  useIntelligenceCost,
  useIntelligenceMenu,
  useIntelligenceOperations,
} from "@/hooks/use-intelligence";
import { FindingCard } from "@/components/intelligence/finding-card";
import { CategoryTab } from "@/components/intelligence/category-tab";
import { formatPrice } from "@/lib/utils";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------

type TabKey = "overview" | "revenue" | "cost" | "menu" | "operations";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "revenue", label: "Revenue" },
  { key: "cost", label: "Cost" },
  { key: "menu", label: "Menu" },
  { key: "operations", label: "Ops" },
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function IntelligenceDashboard() {
  const router = useRouter();
  const { current } = useRestaurant();
  const [activeTab, setActiveTab] = useState<TabKey>("overview");

  const greeting = getGreeting();

  return (
    <div className="mx-auto max-w-lg px-4 pt-6">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-lg font-semibold text-yt-dark">{greeting}</h1>
        <p className="mt-0.5 text-sm text-yt-dark/50">
          {current?.name ?? "YoursTruly"}
          {" \u00B7 "}
          {new Date().toLocaleDateString("en-IN", {
            weekday: "long",
            day: "numeric",
            month: "short",
          })}
        </p>
      </div>

      {/* Quick actions */}
      <div className="mb-4 flex gap-2">
        <button
          type="button"
          onClick={() => router.push("/chat")}
          className="flex-1 rounded-xl border border-yt-gold/30 bg-white px-3 py-3 text-left shadow-sm transition-transform active:scale-[0.98]"
        >
          <div className="mb-1 text-lg">
            <svg className="h-5 w-5 text-yt-primary" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
            </svg>
          </div>
          <div className="text-[13px] font-medium text-yt-dark">Ask anything</div>
          <div className="text-[11px] text-yt-dark/40">Text or voice</div>
        </button>
        <button
          type="button"
          onClick={() => router.push("/briefing")}
          className="flex-1 rounded-xl border border-yt-gold/30 bg-white px-3 py-3 text-left shadow-sm transition-transform active:scale-[0.98]"
        >
          <div className="mb-1 text-lg">
            <svg className="h-5 w-5 text-yt-primary" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 0 1-2.25 2.25M16.5 7.5V18a2.25 2.25 0 0 0 2.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875V18a2.25 2.25 0 0 0 2.25 2.25h13.5M6 7.5h3v3H6v-3Z" />
            </svg>
          </div>
          <div className="text-[13px] font-medium text-yt-dark">Briefing</div>
          <div className="text-[11px] text-yt-dark/40">Yesterday&apos;s summary</div>
        </button>
      </div>

      {/* Tab bar */}
      <div className="mb-4 flex gap-1 overflow-x-auto rounded-xl bg-white p-1 shadow-sm hide-scrollbar">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              "flex-1 whitespace-nowrap rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
              activeTab === tab.key
                ? "bg-yt-primary text-white shadow-sm"
                : "text-yt-dark/50 active:bg-yt-cream",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="pb-6">
        {activeTab === "overview" && <OverviewTab />}
        {activeTab === "revenue" && <RevenueTab />}
        {activeTab === "cost" && <CostTab />}
        {activeTab === "menu" && <MenuTab />}
        {activeTab === "operations" && <OperationsTab />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Overview Tab
// ---------------------------------------------------------------------------

function OverviewTab() {
  const { data: moneyFound } = useMoneyFound();
  const { data: summary, isLoading } = useIntelligenceSummary();

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 animate-pulse rounded-xl bg-white/60" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Money Found Banner */}
      {moneyFound && moneyFound.total_impact_paisa > 0 && (
        <div className="rounded-xl border border-amber-200 bg-gradient-to-r from-amber-50 to-yellow-50 p-4 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-amber-700">
                Money Found
              </p>
              <p className="mt-1 text-2xl font-bold text-amber-900">
                {formatPrice(moneyFound.total_impact_paisa)}
                <span className="text-sm font-normal text-amber-600">/year</span>
              </p>
              <p className="mt-0.5 text-xs text-amber-600">
                {moneyFound.finding_count} finding{moneyFound.finding_count !== 1 ? "s" : ""} need attention
              </p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100">
              <svg className="h-5 w-5 text-amber-700" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
            </div>
          </div>
          {moneyFound.top_findings.length > 0 && (
            <div className="mt-3 space-y-1.5 border-t border-amber-200 pt-3">
              {moneyFound.top_findings.map((f, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-amber-800 line-clamp-1">{f.title}</span>
                  <span className="ml-2 whitespace-nowrap font-medium text-amber-900">
                    {formatPrice(f.rupee_impact)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Quick stats from summary */}
      {summary?.stats && (
        <div className="grid grid-cols-2 gap-3">
          <QuickStat
            label="Yesterday Revenue"
            value={formatPrice(summary.stats.revenue_yesterday)}
          />
          <QuickStat
            label="Orders"
            value={String(summary.stats.orders_yesterday)}
          />
          <QuickStat
            label="Avg Ticket"
            value={formatPrice(summary.stats.avg_ticket)}
          />
          <QuickStat
            label="COGS %"
            value={
              summary.stats.cogs_pct != null
                ? `${summary.stats.cogs_pct.toFixed(1)}%`
                : "N/A"
            }
          />
        </div>
      )}

      {/* Category breakdown */}
      {summary && summary.by_category && Object.keys(summary.by_category).length > 0 && (
        <div className="rounded-xl border border-yt-gold/20 bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-[13px] font-semibold text-yt-dark">
            Findings by Category
          </h3>
          <div className="space-y-2">
            {Object.entries(summary.by_category).map(([cat, info]) => (
              <div key={cat} className="flex items-center justify-between">
                <span className="text-[13px] text-yt-dark/70 capitalize">
                  {cat.replace(/_/g, " ")}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-[12px] text-yt-dark/40">
                    {info.count} finding{info.count !== 1 ? "s" : ""}
                  </span>
                  {info.impact > 0 && (
                    <span className="text-[12px] font-medium text-yt-primary">
                      {formatPrice(info.impact)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top findings */}
      {summary?.top_findings && summary.top_findings.length > 0 && (
        <div>
          <h3 className="mb-3 text-[13px] font-semibold text-yt-dark">
            Top Insights
          </h3>
          <div className="space-y-3">
            {summary.top_findings.map((finding) => (
              <FindingCard key={finding.id} finding={finding} />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {(!summary || (summary.total_findings === 0 && (!moneyFound || moneyFound.total_impact_paisa === 0))) && (
        <EmptyState />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Category Tabs
// ---------------------------------------------------------------------------

function RevenueTab() {
  const { data, isLoading } = useIntelligenceRevenue();
  return (
    <CategoryTab
      findings={data?.findings ?? []}
      totalCount={data?.total_count ?? 0}
      totalImpact={data?.total_impact_paisa ?? 0}
      isLoading={isLoading}
      emptyTitle="No revenue findings"
      emptyDescription="Revenue intelligence findings will appear after the nightly analysis."
    />
  );
}

function CostTab() {
  const { data, isLoading } = useIntelligenceCost();
  return (
    <CategoryTab
      findings={data?.findings ?? []}
      totalCount={data?.total_count ?? 0}
      totalImpact={data?.total_impact_paisa ?? 0}
      isLoading={isLoading}
      emptyTitle="No cost findings"
      emptyDescription="Cost and COGS findings will appear after the nightly analysis."
    />
  );
}

function MenuTab() {
  const { data, isLoading } = useIntelligenceMenu();
  return (
    <CategoryTab
      findings={data?.findings ?? []}
      totalCount={data?.total_count ?? 0}
      totalImpact={data?.total_impact_paisa ?? 0}
      isLoading={isLoading}
      emptyTitle="No menu findings"
      emptyDescription="Menu engineering findings will appear after the nightly analysis."
    />
  );
}

function OperationsTab() {
  const { data, isLoading } = useIntelligenceOperations();
  return (
    <CategoryTab
      findings={data?.findings ?? []}
      totalCount={data?.total_count ?? 0}
      totalImpact={data?.total_impact_paisa ?? 0}
      isLoading={isLoading}
      emptyTitle="No operations findings"
      emptyDescription="Operations findings will appear after the nightly analysis."
    />
  );
}

// ---------------------------------------------------------------------------
// Helper components
// ---------------------------------------------------------------------------

function QuickStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-yt-gold/20 bg-white p-3 shadow-sm">
      <p className="text-[11px] font-medium uppercase tracking-wider text-yt-dark/40">
        {label}
      </p>
      <p className="mt-1 font-mono text-lg font-semibold tabular-nums text-yt-dark">
        {value}
      </p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border border-yt-gold/20 bg-white p-8 text-center">
      <svg className="h-10 w-10 text-yt-dark/20" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
      </svg>
      <div>
        <h3 className="text-base font-semibold text-yt-dark">
          No insights yet
        </h3>
        <p className="mt-1 text-sm text-yt-dark/50">
          Intelligence findings will appear here after the nightly analysis
          runs. Try asking a question in the chat!
        </p>
      </div>
    </div>
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}
