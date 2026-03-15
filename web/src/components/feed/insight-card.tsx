"use client";

import { useCallback } from "react";
import { cn } from "@/lib/utils";
import type { InsightCard as InsightCardType } from "@/lib/types";

interface InsightCardProps {
  card: InsightCardType;
  onDismiss?: (id: number) => void;
  onAction?: (url: string) => void;
}

const CARD_STYLES: Record<string, { border: string; badge: string; badgeText: string; icon: string }> = {
  attention: {
    border: "border-l-red-500",
    badge: "bg-red-50 text-red-700",
    badgeText: "Needs Attention",
    icon: "🔴",
  },
  opportunity: {
    border: "border-l-amber-500",
    badge: "bg-amber-50 text-amber-700",
    badgeText: "Opportunity",
    icon: "💰",
  },
  growth: {
    border: "border-l-emerald-500",
    badge: "bg-emerald-50 text-emerald-700",
    badgeText: "Growth",
    icon: "📈",
  },
  optimization: {
    border: "border-l-blue-500",
    badge: "bg-blue-50 text-blue-700",
    badgeText: "Optimize",
    icon: "⚙️",
  },
};

const PRIORITY_RING: Record<string, string> = {
  high: "ring-1 ring-red-200",
  medium: "",
  low: "",
};

export function InsightCard({ card, onDismiss, onAction }: InsightCardProps) {
  const style = CARD_STYLES[card.card_type] ?? CARD_STYLES.optimization;
  const priorityClass = PRIORITY_RING[card.priority] ?? "";

  const handleDismiss = useCallback(() => {
    onDismiss?.(card.id);
  }, [card.id, onDismiss]);

  const handleAction = useCallback(() => {
    if (card.action_url) {
      onAction?.(card.action_url);
    }
  }, [card.action_url, onAction]);

  return (
    <div
      className={cn(
        "insight-card relative overflow-hidden rounded-xl border border-yt-gold/20 bg-white p-4 shadow-sm",
        "border-l-4",
        style.border,
        priorityClass,
      )}
    >
      {/* Header: badge + dismiss */}
      <div className="mb-2 flex items-center justify-between">
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
            style.badge,
          )}
        >
          <span>{style.icon}</span>
          {style.badgeText}
        </span>

        {onDismiss && (
          <button
            type="button"
            onClick={handleDismiss}
            className="rounded-full p-1 text-yt-dark/30 hover:bg-yt-cream hover:text-yt-dark/60"
            aria-label="Dismiss"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Headline */}
      <h3 className="mb-1.5 text-[15px] font-semibold leading-snug text-yt-dark">
        {card.headline}
      </h3>

      {/* Body */}
      <p className="whitespace-pre-line text-[13px] leading-relaxed text-yt-dark/70">
        {card.body}
      </p>

      {/* Comparison context */}
      {card.comparison && (
        <p className="mt-2 text-[12px] text-yt-dark/50">
          {card.comparison}
        </p>
      )}

      {/* Sparkline or mini chart */}
      {card.chart_data && (card.chart_data as Record<string, unknown>).type === "sparkline" && (
        <div className="mt-3">
          <MiniSparkline
            values={(card.chart_data as { values: number[] }).values}
            positive={card.card_type === "growth"}
          />
        </div>
      )}

      {/* Action button */}
      {card.action_text && (
        <button
          type="button"
          onClick={handleAction}
          className="mt-3 inline-flex items-center gap-1 text-[13px] font-medium text-yt-primary"
        >
          {card.action_text}
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
          </svg>
        </button>
      )}

      {/* Date */}
      {card.insight_date && (
        <div className="mt-2 text-[11px] text-yt-dark/30">
          {formatInsightDate(card.insight_date)}
        </div>
      )}
    </div>
  );
}

// Mini sparkline component (pure CSS + SVG, no chart library)
function MiniSparkline({ values, positive }: { values: number[]; positive: boolean }) {
  if (!values || values.length < 2) return null;

  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const height = 32;
  const width = 120;

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  const color = positive ? "#16a34a" : "#dc2626";

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function formatInsightDate(dateStr: string): string {
  const d = new Date(dateStr);
  const day = d.getDate();
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${day} ${months[d.getMonth()]} ${d.getFullYear()}`;
}
