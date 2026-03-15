"use client";

import { useRef, useEffect, useCallback, useState } from "react";
import { useChat } from "@/hooks/use-chat";
import { useVoiceInput } from "@/hooks/use-voice-input";
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
  } = useChat();

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [inputValue, setInputValue] = useState("");

  // Voice input — uses browser's Web Speech API (free, no server calls)
  const {
    isSupported: voiceSupported,
    isListening,
    transcript: voiceTranscript,
    toggleListening,
    error: voiceError,
  } = useVoiceInput({
    language: "en-IN",
    onResult: (text) => {
      // When voice recognition finishes, put the text in the input
      setInputValue((prev) => {
        const combined = prev ? `${prev} ${text}` : text;
        return combined;
      });
    },
    onInterim: () => {
      // Interim results shown via voiceTranscript state
    },
  });

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isSending]);

  // Auto-focus input (only on desktop — avoids keyboard popup on mobile)
  useEffect(() => {
    if (window.innerWidth > 768) {
      inputRef.current?.focus();
    }
  }, [activeSessionId]);

  const handleSend = useCallback(() => {
    const text = inputValue.trim();
    if (!text || isSending) return;
    setInputValue("");
    sendMessage(text);
    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
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
      if (isSending) return;
      sendMessage(text);
    },
    [isSending, sendMessage],
  );

  // Auto-resize textarea
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, []);

  return (
    <div className="flex h-[calc(100dvh-5rem)] flex-col">
      {/* Header — compact for mobile */}
      <div className="border-b border-yt-gold/20 bg-white px-4 py-2.5">
        <h1 className="text-base font-semibold text-yt-dark">
          Ask anything
        </h1>
        <p className="text-[11px] text-yt-dark/40">
          Query your data, spot trends, get answers
        </p>
      </div>

      {/* Messages area */}
      <div
        ref={scrollRef}
        className="hide-scrollbar flex-1 overflow-y-auto overscroll-contain px-3 py-3"
      >
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-5 px-2">
            <div className="text-center">
              <div className="mb-2 text-3xl">☕</div>
              <h2 className="text-lg font-semibold text-yt-dark">
                Your data, your way
              </h2>
              <p className="mt-1 text-[13px] text-yt-dark/50">
                Ask in plain English — I&apos;ll query the database and show you
              </p>
            </div>

            {/* Suggestion chips — scrollable on mobile */}
            <div className="flex max-w-full flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => handleSuggestion(s)}
                  disabled={isSending}
                  className="rounded-full border border-yt-gold/30 bg-white px-3 py-1.5 text-[12px] text-yt-dark/70 shadow-sm transition-colors active:scale-[0.97] active:bg-yt-cream disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>

            {/* Voice hint */}
            {voiceSupported && (
              <p className="text-[11px] text-yt-dark/30">
                💡 Tap the mic icon to ask with your voice
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
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
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-yt-primary text-[11px] font-bold text-white">
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

      {/* Voice listening indicator */}
      {isListening && (
        <div className="flex items-center justify-center gap-2 border-t border-yt-gold/10 bg-yt-primary/5 px-4 py-2">
          <div className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
          <span className="text-[12px] font-medium text-yt-primary">
            {voiceTranscript || "Listening..."}
          </span>
          <button
            type="button"
            onClick={toggleListening}
            className="ml-auto text-[11px] font-medium text-yt-dark/50 underline"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Voice error */}
      {voiceError && !isListening && (
        <div className="flex items-center justify-center bg-red-50 px-4 py-1.5">
          <span className="text-[11px] text-red-600">{voiceError}</span>
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-yt-gold/20 bg-white px-3 py-2 safe-area-bottom">
        <div className="flex items-end gap-2">
          {/* Voice button */}
          {voiceSupported && (
            <button
              type="button"
              onClick={toggleListening}
              disabled={isSending}
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-all",
                isListening
                  ? "bg-red-500 text-white animate-pulse"
                  : "bg-yt-cream text-yt-dark/50 active:bg-yt-gold/30",
                isSending && "opacity-40",
              )}
              aria-label={isListening ? "Stop listening" : "Voice input"}
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
              </svg>
            </button>
          )}

          {/* Text input */}
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={isListening ? "Speak now..." : "Ask about your business..."}
            rows={1}
            disabled={isListening}
            className="flex-1 resize-none rounded-xl border border-yt-gold/30 bg-yt-cream/50 px-3 py-2.5 text-[14px] text-yt-dark placeholder:text-yt-dark/30 focus:border-yt-primary/30 focus:outline-none focus:ring-1 focus:ring-yt-primary/20 disabled:opacity-50"
            style={{ maxHeight: "120px" }}
          />

          {/* Send button */}
          <button
            type="button"
            onClick={handleSend}
            disabled={!inputValue.trim() || isSending}
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-all active:scale-95",
              inputValue.trim() && !isSending
                ? "bg-yt-primary text-white"
                : "bg-yt-gold/30 text-yt-dark/30",
            )}
            aria-label="Send message"
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

// ---------------------------------------------------------------------------
// Message bubble component
// ---------------------------------------------------------------------------
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
          "max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[14px] leading-relaxed",
          isUser
            ? "rounded-tr-sm bg-yt-primary text-white"
            : "rounded-tl-sm bg-white text-yt-dark shadow-sm",
        )}
      >
        {/* Content — support newlines and basic formatting */}
        <div className="whitespace-pre-wrap break-words">{content}</div>

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
