"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Hook for browser-native speech recognition (Web Speech API).
 * Works on Chrome, Edge, Safari. Gracefully degrades on unsupported browsers.
 *
 * Uses SpeechRecognition for real-time speech-to-text — no server calls needed.
 * Falls back to a "not supported" state on Firefox/older browsers.
 */

// -------------------------------------------------------------------------
// Web Speech API type declarations (not in standard lib.dom.d.ts)
// -------------------------------------------------------------------------

interface SpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly length: number;
  [index: number]: { readonly transcript: string; readonly confidence: number };
}

interface SpeechRecognitionResultList {
  readonly length: number;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionEventInit extends EventInit {
  resultIndex?: number;
  results?: SpeechRecognitionResultList;
}

interface WebSpeechRecognitionEvent extends Event {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultList;
}

interface WebSpeechRecognitionErrorEvent extends Event {
  readonly error: string;
  readonly message: string;
}

interface WebSpeechRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onstart: ((ev: Event) => void) | null;
  onend: ((ev: Event) => void) | null;
  onresult: ((ev: WebSpeechRecognitionEvent) => void) | null;
  onerror: ((ev: WebSpeechRecognitionErrorEvent) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

interface WebSpeechRecognitionConstructor {
  new (): WebSpeechRecognition;
}

// -------------------------------------------------------------------------
// Hook interfaces
// -------------------------------------------------------------------------

interface UseVoiceInputOptions {
  /** Language for recognition. Default: "en-IN" (English, India) */
  language?: string;
  /** Called with final transcript when speech ends */
  onResult?: (transcript: string) => void;
  /** Called with interim results as user speaks */
  onInterim?: (transcript: string) => void;
}

interface UseVoiceInputReturn {
  /** Whether the browser supports speech recognition */
  isSupported: boolean;
  /** Whether we're currently listening */
  isListening: boolean;
  /** The current interim transcript (updates as user speaks) */
  transcript: string;
  /** Start listening */
  startListening: () => void;
  /** Stop listening */
  stopListening: () => void;
  /** Toggle listening on/off */
  toggleListening: () => void;
  /** Any error message */
  error: string | null;
}

// -------------------------------------------------------------------------
// Get the browser's SpeechRecognition constructor
// -------------------------------------------------------------------------

function getSpeechRecognition(): WebSpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null;

  const win = window as unknown as Record<string, unknown>;
  const SR = win.SpeechRecognition ?? win.webkitSpeechRecognition;

  return (SR as WebSpeechRecognitionConstructor) ?? null;
}

// -------------------------------------------------------------------------
// Hook
// -------------------------------------------------------------------------

export function useVoiceInput(
  options: UseVoiceInputOptions = {},
): UseVoiceInputReturn {
  const { language = "en-IN", onResult, onInterim } = options;

  const [isSupported] = useState(() => getSpeechRecognition() !== null);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<WebSpeechRecognition | null>(null);
  const onResultRef = useRef(onResult);
  const onInterimRef = useRef(onInterim);

  // Keep callback refs fresh
  useEffect(() => {
    onResultRef.current = onResult;
    onInterimRef.current = onInterim;
  }, [onResult, onInterim]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
        recognitionRef.current = null;
      }
    };
  }, []);

  const startListening = useCallback(() => {
    const SRConstructor = getSpeechRecognition();
    if (!SRConstructor) {
      setError("Speech recognition not supported in this browser");
      return;
    }

    // Stop any existing instance
    if (recognitionRef.current) {
      recognitionRef.current.abort();
    }

    setError(null);
    setTranscript("");

    const recognition = new SRConstructor();
    recognition.lang = language;
    recognition.interimResults = true;
    recognition.continuous = false; // Stop after one phrase
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event: WebSpeechRecognitionEvent) => {
      let interimTranscript = "";
      let finalTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }

      if (interimTranscript) {
        setTranscript(interimTranscript);
        onInterimRef.current?.(interimTranscript);
      }

      if (finalTranscript) {
        setTranscript(finalTranscript);
        onResultRef.current?.(finalTranscript);
      }
    };

    recognition.onerror = (event: WebSpeechRecognitionErrorEvent) => {
      if (event.error === "no-speech") {
        setError("No speech detected. Try again.");
      } else if (event.error === "not-allowed") {
        setError("Microphone access denied. Please allow microphone access.");
      } else if (event.error === "aborted") {
        // User cancelled — not an error
      } else {
        setError(`Speech error: ${event.error}`);
      }
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
    } catch {
      setError("Could not start speech recognition");
      setIsListening(false);
    }
  }, [language]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsListening(false);
  }, []);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  return {
    isSupported,
    isListening,
    transcript,
    startListening,
    stopListening,
    toggleListening,
    error,
  };
}
