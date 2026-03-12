"use client";

import { useCallback, useState } from "react";
import useSWR, { mutate } from "swr";
import { api } from "@/lib/api";
import type { ChatSession, ChatMessage } from "@/lib/types";

const fetcher = <T>(path: string) => api.get<T>(path);

export function useChatSessions() {
  return useSWR<ChatSession[]>("/api/chat/sessions", fetcher);
}

export function useChatMessages(sessionId: number | null) {
  const key = sessionId ? `/api/chat/sessions/${sessionId}/messages` : null;
  return useSWR<ChatMessage[]>(key, fetcher);
}

interface SendMessageResult {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

export function useChat() {
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [isSending, setIsSending] = useState(false);

  const { data: sessions, mutate: mutateSessions } = useChatSessions();
  const { data: messages, mutate: mutateMessages } = useChatMessages(activeSessionId);

  const createSession = useCallback(async (title?: string) => {
    try {
      const session = await api.post<ChatSession>("/api/chat/sessions", {
        title: title || undefined,
      });
      setActiveSessionId(session.id);
      await mutateSessions();
      return session;
    } catch (err) {
      console.error("Failed to create session:", err);
      return null;
    }
  }, [mutateSessions]);

  const sendMessage = useCallback(
    async (content: string) => {
      let sessionId = activeSessionId;

      // Auto-create session if none active
      if (!sessionId) {
        const session = await createSession(content.slice(0, 100));
        if (!session) return null;
        sessionId = session.id;
      }

      setIsSending(true);
      try {
        const result = await api.post<SendMessageResult>(
          `/api/chat/sessions/${sessionId}/messages`,
          { content }
        );

        // Revalidate messages and sessions list
        await mutateMessages();
        await mutateSessions();

        return result;
      } catch (err) {
        console.error("Failed to send message:", err);
        return null;
      } finally {
        setIsSending(false);
      }
    },
    [activeSessionId, createSession, mutateMessages, mutateSessions]
  );

  const switchSession = useCallback((sessionId: number) => {
    setActiveSessionId(sessionId);
  }, []);

  return {
    sessions: sessions ?? [],
    messages: messages ?? [],
    activeSessionId,
    isSending,
    sendMessage,
    createSession,
    switchSession,
  };
}
