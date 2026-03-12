"use client";

import { useRef, useEffect, useCallback } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessage } from "@/components/chat/chat-message";
import { SuggestionChips } from "@/components/chat/suggestion-chips";
import { useChat } from "@/hooks/use-chat";
import { cn } from "@/lib/utils";
import type { WidgetSpec } from "@/lib/types";

export default function ChatPage() {
  const {
    sessions,
    messages,
    activeSessionId,
    isSending,
    sendMessage,
    switchSession,
    createSession,
  } = useChat();

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = useCallback(
    (text: string) => {
      sendMessage(text);
    },
    [sendMessage]
  );

  return (
    <div className="flex h-[calc(100vh-2rem)] flex-col">
      <PageHeader
        title="AI Chat"
        description="Ask anything about your restaurant data in plain English"
      />

      <div className="flex flex-1 gap-4 overflow-hidden">
        {/* Session sidebar */}
        <div className="hidden w-56 shrink-0 flex-col gap-1 overflow-y-auto rounded-xl border border-slate-200 bg-white p-3 md:flex">
          <button
            type="button"
            onClick={() => createSession()}
            className="mb-2 w-full rounded-lg bg-teal-600 px-3 py-2 text-xs font-medium text-white hover:bg-teal-700"
          >
            + New Chat
          </button>
          {sessions.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => switchSession(s.id)}
              className={cn(
                "w-full truncate rounded-lg px-3 py-2 text-left text-xs",
                s.id === activeSessionId
                  ? "bg-teal-50 font-medium text-teal-700"
                  : "text-slate-600 hover:bg-slate-50"
              )}
            >
              {s.title || "Untitled"}
            </button>
          ))}
          {sessions.length === 0 && (
            <p className="px-2 py-4 text-center text-xs text-muted-foreground">
              No conversations yet
            </p>
          )}
        </div>

        {/* Chat area */}
        <div className="flex flex-1 flex-col rounded-xl border border-slate-200 bg-white">
          {/* Messages */}
          <div
            ref={scrollRef}
            className="flex-1 space-y-4 overflow-y-auto p-4"
          >
            {messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-6">
                <div className="text-center">
                  <div className="mb-2 text-3xl">🔍</div>
                  <h3 className="text-base font-semibold text-slate-800">
                    Ask about your data
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    I can query your database, create charts, and surface
                    insights
                  </p>
                </div>
                <SuggestionChips onSelect={handleSend} />
              </div>
            ) : (
              messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  role={msg.role as "user" | "assistant"}
                  content={msg.content}
                  widgets={msg.widgets as WidgetSpec[] | null}
                />
              ))
            )}

            {/* Typing indicator */}
            {isSending && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="flex gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-teal-400" style={{ animationDelay: "0ms" }} />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-teal-400" style={{ animationDelay: "150ms" }} />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-teal-400" style={{ animationDelay: "300ms" }} />
                </span>
                Thinking...
              </div>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-slate-100 p-3">
            <ChatInput onSend={handleSend} isLoading={isSending} />
          </div>
        </div>
      </div>
    </div>
  );
}
