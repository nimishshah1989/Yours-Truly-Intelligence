"use client";

import { cn } from "@/lib/utils";
import { formatPrice } from "@/lib/utils";
import type { IntelligenceFinding } from "@/hooks/use-intelligence";

interface FindingCardProps {
  finding: IntelligenceFinding;
}

const SEVERITY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  critical: { bg: "bg-red-50", text: "text-red-700", label: "Critical" },
  alert: { bg: "bg-orange-50", text: "text-orange-700", label: "Alert" },
  high: { bg: "bg-orange-50", text: "text-orange-700", label: "High" },
  watch: { bg: "bg-amber-50", text: "text-amber-700", label: "Watch" },
  medium: { bg: "bg-amber-50", text: "text-amber-700", label: "Medium" },
  info: { bg: "bg-blue-50", text: "text-blue-600", label: "Info" },
  low: { bg: "bg-slate-50", text: "text-slate-600", label: "Low" },
};

const CATEGORY_LABELS: Record<string, string> = {
  revenue: "Revenue",
  revenue_anomaly: "Revenue",
  food_cost_trend: "Food Cost",
  cost: "Cost",
  menu: "Menu",
  menu_decline: "Menu Trend",
  operations: "Operations",
  channel: "Channel Mix",
  portion_drift: "Portion Drift",
  vendor_price_spike: "Vendor Price",
};

function deriveActionFromFinding(finding: IntelligenceFinding): string | null {
  const detail = finding.detail;
  if (!detail) return null;

  // Menu decline: suggest action based on volume drop
  if (finding.category === "menu" || finding.category === "menu_decline") {
    const changePct = detail.change_pct as number | undefined;
    const itemName = detail.item_name as string | undefined;
    if (changePct && itemName) {
      if (Math.abs(changePct) > 40) {
        return `${itemName} has dropped significantly. Check if it's still being promoted, visible on the menu, and in stock. Consider a limited-time offer to revive demand.`;
      }
      return `Monitor ${itemName} this week. If the decline continues, consider repositioning it on the menu or creating a combo offer.`;
    }
  }

  // Revenue anomaly: suggest investigation
  if (finding.category === "revenue" || finding.category === "revenue_anomaly") {
    const deviationPct = detail.deviation_pct as number | undefined;
    if (deviationPct && Math.abs(deviationPct) > 25) {
      return "Investigate what was different — was there a local event, weather issue, or staffing change? Check if online orders also dipped.";
    }
    return "Compare foot traffic and online order volume to isolate whether this was a demand or operations issue.";
  }

  // Food cost trend
  if (finding.category === "food_cost" || finding.category === "food_cost_trend") {
    return "Review top-selling items for recipe adherence. Check if any vendor prices spiked. Audit portion sizes this week.";
  }

  return detail.what_to_do as string | null;
}

export function FindingCard({ finding }: FindingCardProps) {
  const severity = SEVERITY_STYLES[finding.severity] ?? SEVERITY_STYLES.medium;
  const hasImpact = finding.rupee_impact != null && finding.rupee_impact !== 0;
  const action = deriveActionFromFinding(finding);
  const categoryLabel = CATEGORY_LABELS[finding.category] ?? finding.category.replace(/_/g, " ");

  return (
    <div className="rounded-xl border border-yt-gold/20 bg-white p-4 shadow-sm">
      {/* Top row: severity badge + category + impact */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium",
              severity.bg,
              severity.text,
            )}
          >
            {severity.label}
          </span>
          <span className="text-[11px] font-medium text-yt-dark/40">
            {categoryLabel}
          </span>
        </div>
        {hasImpact && (
          <span className="text-sm font-semibold text-yt-primary">
            {formatPrice(finding.rupee_impact!)}
          </span>
        )}
      </div>

      {/* Title */}
      <h3 className="mb-2 text-[14px] font-semibold leading-snug text-yt-dark">
        {finding.title}
      </h3>

      {/* Action recommendation */}
      {action && (
        <div className="mb-2 rounded-lg bg-emerald-50 px-3 py-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-700">
            Recommended Action
          </p>
          <p className="mt-0.5 text-[13px] leading-relaxed text-emerald-800">
            {action}
          </p>
        </div>
      )}

      {/* Key metrics from detail */}
      {finding.detail && (
        <DetailMetrics detail={finding.detail} category={finding.category} />
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
        </div>
      )}

      {/* Date */}
      <div className="mt-2 text-[11px] text-yt-dark/30">
        {new Date(finding.finding_date).toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric",
        })}
      </div>
    </div>
  );
}

function DetailMetrics({ detail, category }: { detail: Record<string, unknown>; category: string }) {
  // Show relevant detail metrics based on category
  if (category === "menu" || category === "menu_decline") {
    const recentQty = detail.recent_qty as number | undefined;
    const priorQty = detail.prior_qty as number | undefined;
    if (recentQty != null && priorQty != null) {
      return (
        <div className="flex gap-4 text-[12px] text-yt-dark/50">
          <span>Previous 4 weeks: <span className="font-medium text-yt-dark/70">{priorQty} sold</span></span>
          <span>Recent 4 weeks: <span className="font-medium text-yt-dark/70">{recentQty} sold</span></span>
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
