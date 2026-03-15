"use client";

import { useBriefing } from "@/hooks/use-feed";
import { cn } from "@/lib/utils";

export default function BriefingPage() {
  const { briefing, isLoading, error } = useBriefing();

  return (
    <div className="mx-auto max-w-lg px-4 pt-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-yt-dark">
          Daily Briefing
        </h1>
        <p className="mt-0.5 text-sm text-yt-dark/50">
          {briefing?.target_date
            ? formatDate(briefing.target_date)
            : "Yesterday's performance summary"}
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-28 animate-pulse rounded-xl bg-white/60"
            />
          ))}
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center">
          <p className="text-sm text-red-700">
            Couldn&apos;t load briefing. Make sure the backend is running.
          </p>
        </div>
      )}

      {/* Briefing sections */}
      {briefing && !isLoading && (
        <div className="space-y-3 pb-6">
          {briefing.sections.map((section, i) => (
            <BriefingCard
              key={i}
              emoji={section.emoji}
              title={section.title}
              body={section.body}
              isFirst={i === 0}
            />
          ))}

          {/* Anomalies */}
          {briefing.anomalies.length > 0 && (
            <div className="rounded-xl border border-red-200/50 bg-white p-4">
              <div className="mb-2 flex items-center gap-1.5">
                <span>⚠️</span>
                <h3 className="text-[14px] font-semibold text-yt-dark">
                  {briefing.anomalies.length} anomal{briefing.anomalies.length > 1 ? "ies" : "y"} detected
                </h3>
              </div>
              <div className="space-y-2">
                {briefing.anomalies.map((anomaly, i) => (
                  <div
                    key={i}
                    className={cn(
                      "flex items-start gap-2 rounded-lg p-2 text-[13px]",
                      anomaly.severity === "high"
                        ? "bg-red-50 text-red-800"
                        : anomaly.severity === "medium"
                          ? "bg-amber-50 text-amber-800"
                          : "bg-blue-50 text-blue-800",
                    )}
                  >
                    <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-current" />
                    <span>{anomaly.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* WhatsApp prompt */}
          <div className="rounded-xl border border-yt-gold/20 bg-yt-light p-4 text-center">
            <p className="text-[13px] text-yt-dark/60">
              💡 Get this briefing on WhatsApp every morning at 7:30 AM.
            </p>
            <p className="mt-1 text-[11px] text-yt-dark/40">
              Ask your admin to set up WhatsApp integration.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function BriefingCard({
  emoji,
  title,
  body,
  isFirst,
}: {
  emoji: string;
  title: string;
  body: string;
  isFirst: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border bg-white p-4 shadow-sm",
        isFirst ? "border-yt-primary/20" : "border-yt-gold/20",
      )}
    >
      <div className="mb-2 flex items-center gap-2">
        <span className="text-lg">{emoji}</span>
        <h3 className="text-[14px] font-semibold text-yt-dark">{title}</h3>
      </div>
      <div className="whitespace-pre-line text-[13px] leading-relaxed text-yt-dark/70">
        {body}
      </div>
    </div>
  );
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
