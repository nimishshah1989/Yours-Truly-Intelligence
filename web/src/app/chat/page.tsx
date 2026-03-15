"use client";

import { useRef, useEffect, useCallback, useState } from "react";
import { useChat } from "@/hooks/use-chat";
import { cn } from "@/lib/utils";
import type { WidgetSpec } from "@/lib/types";

const SUGGESTIONS = [
  "What was yesterday's revenue?",
  "Top 5 items this week",
  "Compare this week to last week",
  "How's my food cost trending?",
  "Show me revenue by area",
  "Which items are declining?",
];

export default function ChatPage() {
  const {
    messages,
    activeSessionId,
    isSending,
    sendMessage,
    createSession,
  } = useChat();

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [inputValue, setInputValue] = useState("");

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isSending]);

  // Auto-focus input
  useEffect(() => {
    inputRef.current?.focus();
  }, [activeSessionId]);

  const handleSend = useCallback(() => {
    const text = inputValue.trim();
    if (!text || isSending) return;
    setInputValue("");
    sendMessage(text);
  }, [inputValue, isSending, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleSuggestion = useCallback(
    (text: string) => {
      sendMessage(text);
    },
    [sendMessage],
  );

  return (
    <div className="flex h-[calc(100vh-5rem)] flex-col">
      {/* Header */}
      <div className="border-b border-yt-gold/20 bg-white px-4 py-3">
        <h1 className="text-base font-semibold text-yt-dark">
          Ask anything
        </h1>
        <p className="text-[12px] text-yt-dark/40">
          I can query your data, spot trends, and answer questions
        </p>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="hide-scrollbar flex-1 overflow-y-auto px-4 py-4"
      >
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-6 px-4">
            <div className="text-center">
              <div className="mb-3 text-4xl">☕</div>
              <h2 className="text-lg font-semibold text-yt-dark">
                Your data, your way
              </h2>
              <p className="mt-1 text-sm text-yt-dark/50">
                Ask in plain English — I&apos;ll query the database and show you the answer
              </p>
            </div>

            {/* Suggestion chips */}
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => handleSuggestion(s)}
                  className="rounded-full border border-yt-gold/30 bg-white px-3 py-1.5 text-[12px] text-yt-dark/70 shadow-sm transition-colors hover:border-yt-primary/30 hover:text-yt-primary active:bg-yt-cream"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                role={msg.role as "user" | "assistant"}
                content={msg.content}
                widgets={msg.widgets as WidgetSpec[] | null}
              />
            ))}

            {/* Typing indicator */}
            {isSending && (
              <div className="flex items-start gap-2">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-yt-primary text-[11px] text-white">
                  YT
                </div>
                <div className="rounded-2xl rounded-tl-sm bg-white px-4 py-3 shadow-sm">
                  <div className="flex gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-yt-deep" style={{ animationDelay: "0ms" }} />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-yt-deep" style={{ animationDelay: "150ms" }} />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-yt-deep" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-yt-gold/20 bg-white px-3 py-2">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your business..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-yt-gold/30 bg-yt-cream/50 px-3 py-2.5 text-[14px] text-yt-dark placeholder:text-yt-dark/30 focus:border-yt-primary/30 focus:outline-none focus:ring-1 focus:ring-yt-primary/20"
            style={{ maxHeight: "120px" }}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!inputValue.trim() || isSending}
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-colors",
              inputValue.trim() && !isSending
                ? "bg-yt-primary text-white"
                : "bg-yt-gold/30 text-yt-dark/30",
            )}
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

// Message bubble component
function MessageBubble({
  role,
  content,
  widgets,
}: {
  role: "user" | "assistant";
  content: string;
  widgets: WidgetSpec[] | null;
}) {
  const isUser = role === "user";

  return (
    <div className={cn("flex items-start gap-2", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      {!isUser && (
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-yt-primary text-[11px] font-bold text-white">
          YT
        </div>
      )}

      {/* Bubble */}
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-3 text-[14px] leading-relaxed",
          isUser
            ? "rounded-tr-sm bg-yt-primary text-white"
            : "rounded-tl-sm bg-white text-yt-dark shadow-sm",
        )}
      >
        {/* Content */}
        <div className="whitespace-pre-wrap">{content}</div>

        {/* Widgets indicator */}
        {widgets && widgets.length > 0 && (
          <div className="mt-2 flex items-center gap-1 border-t border-yt-gold/10 pt-2 text-[12px] text-yt-dark/40">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
            </svg>
            {widgets.length} chart{widgets.length > 1 ? "s" : ""} generated
          </div>
        )}
      </div>
    </div>
  );
}
