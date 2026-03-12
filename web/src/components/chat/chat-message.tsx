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
            : "bg-teal-50 text-teal-700"
        )}
      >
        {isUser ? "You" : "AI"}
      </div>

      {/* Message content */}
      <div
        className={cn(
          "max-w-[80%] space-y-3",
          isUser && "text-right"
        )}
      >
        <div
          className={cn(
            "inline-block rounded-xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-teal-600 text-white"
              : "bg-white border border-slate-200 text-foreground"
          )}
        >
          {content.split("\n").map((line, i) => (
            <p key={i} className={i > 0 ? "mt-1" : undefined}>
              {line || "\u00A0"}
            </p>
          ))}
        </div>

        {/* Render widgets inline */}
        {widgets && widgets.length > 0 && (
          <div className="space-y-3">
            {widgets.map((widget, i) => (
              <div
                key={i}
                className="rounded-xl border border-slate-200 bg-white p-4"
              >
                {widget.title && (
                  <h4 className="mb-2 text-sm font-semibold text-slate-800">
                    {widget.title}
                  </h4>
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
