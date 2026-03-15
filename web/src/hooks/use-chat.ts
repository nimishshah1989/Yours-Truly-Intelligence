"use client";

import { useCallback, useState, useRef } from "react";
import useSWR, { mutate as globalMutate } from "swr";
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
  // Track session ID in a ref so callbacks always see the latest value
  const sessionIdRef = useRef<number | null>(null);

  const { data: sessions, mutate: mutateSessions } = useChatSessions();
  const { data: messages, mutate: mutateMessages } = useChatMessages(activeSessionId);

  const createSession = useCallback(async (title?: string) => {
    try {
      const session = await api.post<ChatSession>("/api/chat/sessions", {
        title: title || undefined,
      });
      sessionIdRef.current = session.id;
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
      let sessionId = sessionIdRef.current ?? activeSessionId;

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

        // Use global mutate with the EXPLICIT key for this session
        // This avoids the stale closure bug where activeSessionId hasn't
        // updated yet in the SWR hook
        const messagesKey = `/api/chat/sessions/${sessionId}/messages`;
        await globalMutate(messagesKey);
        await mutateSessions();

        return result;
      } catch (err) {
        console.error("Failed to send message:", err);
        return null;
      } finally {
        setIsSending(false);
      }
    },
    [activeSessionId, createSession, mutateSessions]
  );

  const switchSession = useCallback((sessionId: number) => {
    sessionIdRef.current = sessionId;
    setActiveSessionId(sessionId);
  }, []);

  const deleteSession = useCallback(async (sessionId: number) => {
    try {
      await api.delete(`/api/chat/sessions/${sessionId}`);
      if (sessionIdRef.current === sessionId) {
        sessionIdRef.current = null;
        setActiveSessionId(null);
      }
      await mutateSessions();
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  }, [mutateSessions]);

  return {
    sessions: sessions ?? [],
    messages: messages ?? [],
    activeSessionId,
    isSending,
    sendMessage,
    createSession,
    switchSession,
    deleteSession,
  };
}
