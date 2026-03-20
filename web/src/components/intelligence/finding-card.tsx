"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { formatPrice } from "@/lib/utils";
import type { IntelligenceFinding } from "@/hooks/use-intelligence";

interface FindingCardProps {
  finding: IntelligenceFinding;
}

const SEVERITY_STYLES: Record<string, { bg: string; text: string; label: string; dot: string }> = {
  critical: { bg: "bg-red-50", text: "text-red-700", label: "Critical", dot: "bg-red-500" },
  alert: { bg: "bg-orange-50", text: "text-orange-700", label: "Alert", dot: "bg-orange-500" },
  high: { bg: "bg-orange-50", text: "text-orange-700", label: "High", dot: "bg-orange-500" },
  watch: { bg: "bg-amber-50", text: "text-amber-700", label: "Watch", dot: "bg-amber-500" },
  medium: { bg: "bg-amber-50", text: "text-amber-700", label: "Medium", dot: "bg-amber-500" },
  info: { bg: "bg-blue-50", text: "text-blue-600", label: "Info", dot: "bg-blue-500" },
  low: { bg: "bg-slate-50", text: "text-slate-600", label: "Low", dot: "bg-slate-400" },
};

const CATEGORY_LABELS: Record<string, string> = {
  revenue: "Revenue",
  revenue_anomaly: "Revenue",
  food_cost_trend: "Food Cost",
  food_cost: "Food Cost",
  cost: "Cost",
  menu: "Menu",
  menu_decline: "Menu Trend",
  operations: "Operations",
  channel: "Channel Mix",
  portion_drift: "Portion Drift",
  vendor_price_spike: "Vendor Price",
};

export function FindingCard({ finding }: FindingCardProps) {
  const [expanded, setExpanded] = useState(false);
  const severity = SEVERITY_STYLES[finding.severity] ?? SEVERITY_STYLES.medium;
  const hasImpact = finding.rupee_impact != null && finding.rupee_impact !== 0;
  const categoryLabel = CATEGORY_LABELS[finding.category] ?? finding.category.replace(/_/g, " ");

  // Claude-generated insights have narrative and action in detail
  const narrative = finding.detail?.narrative as string | undefined;
  const action = finding.detail?.action as string | undefined;
  const isClaudeInsight = finding.detail?.source === "claude_deep_analysis";
  const hasExpandableContent = narrative || action || finding.related_items?.length;

  return (
    <button
      type="button"
      onClick={() => hasExpandableContent && setExpanded(!expanded)}
      className={cn(
        "w-full rounded-xl border bg-white p-4 text-left shadow-sm transition-all",
        expanded ? "border-yt-primary/30 ring-1 ring-yt-primary/10" : "border-yt-gold/20",
        hasExpandableContent && "cursor-pointer active:scale-[0.99]",
      )}
    >
      {/* Top row: severity + category + impact */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={cn("h-2 w-2 rounded-full", severity.dot)} />
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium",
              severity.bg, severity.text,
            )}
          >
            {severity.label}
          </span>
          <span className="text-[11px] font-medium text-yt-dark/40">
            {categoryLabel}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {hasImpact && (
            <span className="text-sm font-semibold text-yt-primary">
              {formatPrice(finding.rupee_impact!)}
            </span>
          )}
          {hasExpandableContent && (
            <svg
              className={cn(
                "h-4 w-4 text-yt-dark/30 transition-transform",
                expanded && "rotate-180",
              )}
              fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
            </svg>
          )}
        </div>
      </div>

      {/* Title */}
      <h3 className="text-[14px] font-semibold leading-snug text-yt-dark">
        {finding.title}
      </h3>

      {/* Collapsed preview — show first line of narrative */}
      {!expanded && narrative && (
        <p className="mt-1 text-[12px] leading-relaxed text-yt-dark/50 line-clamp-2">
          {narrative}
        </p>
      )}

      {/* Expanded content */}
      {expanded && (
        <div className="mt-3 space-y-3">
          {/* Narrative */}
          {narrative && (
            <div className="rounded-lg bg-slate-50 px-3 py-2.5">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Analysis
              </p>
              <p className="text-[13px] leading-relaxed text-slate-700">
                {narrative}
              </p>
            </div>
          )}

          {/* Action recommendation */}
          {action && (
            <div className="rounded-lg bg-emerald-50 px-3 py-2.5">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-700 mb-1">
                Recommended Action
              </p>
              <p className="text-[13px] leading-relaxed text-emerald-800">
                {action}
              </p>
            </div>
          )}

          {/* Detail metrics for mechanical findings */}
          {!isClaudeInsight && finding.detail && (
            <DetailMetrics detail={finding.detail} category={finding.category} />
          )}

          {/* Related items */}
          {finding.related_items && finding.related_items.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              <span className="text-[11px] text-yt-dark/40 mr-1">Related:</span>
              {finding.related_items.slice(0, 6).map((item) => (
                <span
                  key={item}
                  className="rounded-full bg-yt-gold/20 px-2.5 py-0.5 text-[11px] font-medium text-yt-dark/60"
                >
                  {item}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Date + source badge */}
      <div className="mt-2 flex items-center justify-between">
        <span className="text-[11px] text-yt-dark/30">
          {new Date(finding.finding_date).toLocaleDateString("en-IN", {
            day: "numeric", month: "short",
          })}
        </span>
        {isClaudeInsight && (
          <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-medium text-violet-600">
            AI Insight
          </span>
        )}
      </div>
    </button>
  );
}

function DetailMetrics({ detail, category }: { detail: Record<string, unknown>; category: string }) {
  if (category === "menu" || category === "menu_decline") {
    const recentQty = detail.recent_qty as number | undefined;
    const priorQty = detail.prior_qty as number | undefined;
    if (recentQty != null && priorQty != null) {
      return (
        <div className="flex gap-4 text-[12px] text-yt-dark/50">
          <span>Previous: <span className="font-medium text-yt-dark/70">{priorQty} sold</span></span>
          <span>Recent: <span className="font-medium text-yt-dark/70">{recentQty} sold</span></span>
        </div>
      );
    }
  }

  if (category === "revenue" || category === "revenue_anomaly") {
    const actual = detail.actual_paisa as number | undefined;
    const avg = detail.dow_avg_paisa as number | undefined;
    if (actual != null && avg != null) {
      return (
        <div className="flex gap-4 text-[12px] text-yt-dark/50">
          <span>Actual: <span className="font-medium text-yt-dark/70">{formatPrice(actual)}</span></span>
          <span>Day avg: <span className="font-medium text-yt-dark/70">{formatPrice(avg)}</span></span>
        </div>
      );
    }
  }

  return null;
}
