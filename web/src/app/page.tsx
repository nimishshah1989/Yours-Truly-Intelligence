"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useFeed } from "@/hooks/use-feed";
import { useRestaurant } from "@/hooks/use-restaurant";
import { InsightCard } from "@/components/feed/insight-card";
import { useMoneyFound } from "@/hooks/use-home";
import { formatPrice } from "@/lib/utils";

export default function FeedPage() {
  const router = useRouter();
  const { current } = useRestaurant();
  const { cards, isLoading, dismissCard, refresh } = useFeed(30);
  const { data: moneyFound } = useMoneyFound();

  const handleAction = useCallback(
    (url: string) => {
      router.push(url);
    },
    [router],
  );

  const greeting = getGreeting();

  return (
    <div className="mx-auto max-w-lg px-4 pt-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-yt-dark">
          {greeting}
        </h1>
        <p className="mt-0.5 text-sm text-yt-dark/50">
          {current?.name ?? "YoursTruly"}
          {" · "}
          {new Date().toLocaleDateString("en-IN", {
            weekday: "long",
            day: "numeric",
            month: "short",
          })}
        </p>
      </div>

      {/* Quick actions */}
      <div className="mb-6 flex gap-2">
        <button
          type="button"
          onClick={() => router.push("/chat")}
          className="flex-1 rounded-xl border border-yt-gold/30 bg-white px-3 py-3 text-left shadow-sm transition-transform active:scale-[0.98]"
        >
          <div className="mb-1 text-lg">💬</div>
          <div className="text-[13px] font-medium text-yt-dark">Ask anything</div>
          <div className="text-[11px] text-yt-dark/40">Text or voice</div>
        </button>
        <button
          type="button"
          onClick={() => router.push("/briefing")}
          className="flex-1 rounded-xl border border-yt-gold/30 bg-white px-3 py-3 text-left shadow-sm transition-transform active:scale-[0.98]"
        >
          <div className="mb-1 text-lg">📊</div>
          <div className="text-[13px] font-medium text-yt-dark">Today&apos;s briefing</div>
          <div className="text-[11px] text-yt-dark/40">Yesterday&apos;s summary</div>
        </button>
      </div>

      {/* Money Found Banner */}
      {moneyFound && moneyFound.total_impact_paisa > 0 && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-gradient-to-r from-amber-50 to-yellow-50 p-4 shadow-sm">
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
            <div className="text-3xl">💰</div>
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

      {/* Feed */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-36 animate-pulse rounded-xl bg-white/60"
            />
          ))}
        </div>
      ) : cards.length === 0 ? (
        <EmptyFeed onRefresh={refresh} />
      ) : (
        <div className="space-y-3 pb-4">
          {/* Attention cards first */}
          {cards
            .filter((c) => c.card_type === "attention")
            .map((card) => (
              <InsightCard
                key={card.id}
                card={card}
                onDismiss={dismissCard}
                onAction={handleAction}
              />
            ))}

          {/* Then all other cards */}
          {cards
            .filter((c) => c.card_type !== "attention")
            .map((card) => (
              <InsightCard
                key={card.id}
                card={card}
                onDismiss={dismissCard}
                onAction={handleAction}
              />
            ))}
        </div>
      )}
    </div>
  );
}

function EmptyFeed({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border border-yt-gold/20 bg-white p-8 text-center">
      <div className="text-4xl">☕</div>
      <div>
        <h3 className="text-base font-semibold text-yt-dark">
          No insights yet
        </h3>
        <p className="mt-1 text-sm text-yt-dark/50">
          Insights will appear here after the nightly analysis runs.
          Try asking a question in the chat!
        </p>
      </div>
      <button
        type="button"
        onClick={onRefresh}
        className="rounded-lg bg-yt-primary px-4 py-2 text-sm font-medium text-white"
      >
        Refresh
      </button>
    </div>
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning ☀️";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}
