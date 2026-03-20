"use client";

import { cn } from "@/lib/utils";
import { formatPrice } from "@/lib/utils";
import type { IntelligenceFinding } from "@/hooks/use-intelligence";

interface FindingCardProps {
  finding: IntelligenceFinding;
}

const SEVERITY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  critical: { bg: "bg-red-50", text: "text-red-700", label: "Critical" },
  high: { bg: "bg-orange-50", text: "text-orange-700", label: "High" },
  medium: { bg: "bg-amber-50", text: "text-amber-700", label: "Medium" },
  low: { bg: "bg-slate-50", text: "text-slate-600", label: "Low" },
};

const CATEGORY_ICONS: Record<string, string> = {
  revenue: "bar-chart",
  cost: "dollar-sign",
  menu: "utensils",
  operations: "clock",
  food_cost_trend: "trending-up",
  portion_drift: "scale",
  vendor_price_spike: "alert-triangle",
  menu_decline: "trending-down",
  revenue_anomaly: "activity",
};

export function FindingCard({ finding }: FindingCardProps) {
  const severity = SEVERITY_STYLES[finding.severity] ?? SEVERITY_STYLES.medium;
  const hasImpact = finding.rupee_impact != null && finding.rupee_impact !== 0;

  return (
    <div className="rounded-xl border border-yt-gold/20 bg-white p-4 shadow-sm transition-transform active:scale-[0.99]">
      {/* Top row: severity badge + impact */}
      <div className="mb-2 flex items-center justify-between">
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium",
            severity.bg,
            severity.text,
          )}
        >
          {severity.label}
        </span>
        {hasImpact && (
          <span className="text-sm font-semibold text-yt-primary">
            {formatPrice(finding.rupee_impact!)}
          </span>
        )}
      </div>

      {/* Title */}
      <h3 className="mb-1.5 text-[15px] font-semibold leading-snug text-yt-dark">
        {finding.title}
      </h3>

      {/* Category tag */}
      <div className="mb-2">
        <span className="inline-flex items-center rounded-md bg-yt-cream px-2 py-0.5 text-[11px] font-medium text-yt-dark/60">
          {finding.category.replace(/_/g, " ")}
        </span>
      </div>

      {/* What to do */}
      {finding.detail?.what_to_do && (
        <div className="mb-2 rounded-lg bg-emerald-50 px-3 py-2">
          <p className="text-[12px] font-medium text-emerald-800">What to do</p>
          <p className="mt-0.5 text-[13px] leading-relaxed text-emerald-700">
            {finding.detail.what_to_do}
          </p>
        </div>
      )}

      {/* Logic / reasoning */}
      {finding.detail?.logic && (
        <p className="text-[12px] leading-relaxed text-yt-dark/50">
          {finding.detail.logic}
        </p>
      )}

      {/* Related items */}
      {finding.related_items && finding.related_items.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {finding.related_items.slice(0, 5).map((item) => (
            <span
              key={item}
              className="rounded-full bg-yt-gold/20 px-2 py-0.5 text-[10px] text-yt-dark/60"
            >
              {item}
            </span>
          ))}
          {finding.related_items.length > 5 && (
            <span className="rounded-full bg-yt-gold/20 px-2 py-0.5 text-[10px] text-yt-dark/60">
              +{finding.related_items.length - 5} more
            </span>
          )}
        </div>
      )}

      {/* Date */}
      <div className="mt-2 text-[11px] text-yt-dark/30">
        {new Date(finding.finding_date).toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
        })}
      </div>
    </div>
  );
}
