"use client";

import { formatPrice } from "@/lib/utils";
import { FindingCard } from "./finding-card";
import type { IntelligenceFinding } from "@/hooks/use-intelligence";

interface CategoryTabProps {
  findings: IntelligenceFinding[];
  totalCount: number;
  totalImpact: number;
  isLoading: boolean;
  emptyTitle: string;
  emptyDescription: string;
}

export function CategoryTab({
  findings,
  totalCount,
  totalImpact,
  isLoading,
  emptyTitle,
  emptyDescription,
}: CategoryTabProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-32 animate-pulse rounded-xl bg-white/60"
          />
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* Summary stats */}
      <div className="mb-4 flex gap-3">
        <div className="flex-1 rounded-xl border border-yt-gold/20 bg-white p-3 shadow-sm">
          <p className="text-[11px] font-medium uppercase tracking-wider text-yt-dark/40">
            Findings
          </p>
          <p className="mt-0.5 font-mono text-xl font-semibold text-yt-dark">
            {totalCount}
          </p>
        </div>
        <div className="flex-1 rounded-xl border border-yt-gold/20 bg-white p-3 shadow-sm">
          <p className="text-[11px] font-medium uppercase tracking-wider text-yt-dark/40">
            Rupee Impact
          </p>
          <p className="mt-0.5 font-mono text-xl font-semibold text-yt-primary">
            {formatPrice(totalImpact)}
          </p>
        </div>
      </div>

      {/* Findings list */}
      {findings.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-yt-gold/20 bg-white p-8 text-center">
          <div className="text-3xl">--</div>
          <div>
            <h3 className="text-base font-semibold text-yt-dark">{emptyTitle}</h3>
            <p className="mt-1 text-sm text-yt-dark/50">{emptyDescription}</p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {findings.map((finding) => (
            <FindingCard key={finding.id} finding={finding} />
          ))}
        </div>
      )}
    </div>
  );
}
