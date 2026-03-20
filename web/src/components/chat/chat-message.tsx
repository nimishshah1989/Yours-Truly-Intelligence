"use client";

import { WidgetRenderer } from "@/components/widgets/widget-renderer";
import type { WidgetSpec } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  widgets?: WidgetSpec[] | null;
}

export function ChatMessage({ role, content, widgets }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-medium",
          isUser
            ? "bg-slate-100 text-slate-600"
            : "bg-yt-primary/10 text-yt-primary"
        )}
      >
        {isUser ? "You" : "YT"}
      </div>

      {/* Message content */}
      <div
        className={cn(
          "max-w-[85%] space-y-3",
          isUser && "text-right"
        )}
      >
        <div
          className={cn(
            "inline-block rounded-xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-yt-primary text-white"
              : "bg-white border border-yt-gold/20 text-foreground shadow-sm"
          )}
        >
          <div className="whitespace-pre-wrap break-words chat-content">
            {content}
          </div>
        </div>

        {/* Render widgets inline */}
        {widgets && widgets.length > 0 && (
          <div className="space-y-3">
            {widgets.map((widget, i) => (
              <div
                key={i}
                className="rounded-xl border border-yt-gold/20 bg-white p-4 shadow-sm"
              >
                {widget.title && (
                  <h4 className="mb-2 text-sm font-semibold text-yt-dark">
                    {widget.title}
                  </h4>
                )}
                {widget.subtitle && (
                  <p className="mb-2 text-xs text-yt-dark/50">
                    {widget.subtitle}
                  </p>
                )}
                <WidgetRenderer widget={widget} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
