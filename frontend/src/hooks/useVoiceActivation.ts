"use client";

import { useEffect, useRef, useCallback } from "react";

// Web Speech API types (not in standard TypeScript lib)
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface VoiceActivationOptions {
  enabled: boolean;
  wakeWords: string[];
  onActivate: () => void;
}

/**
 * Hook for wake word detection using Web Speech API.
 * Listens for phrases like "Hey Spectra" or "Start Spectra" to activate.
 */
export function useVoiceActivation({
  enabled,
  wakeWords,
  onActivate,
}: VoiceActivationOptions) {
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const isRunningRef = useRef(false);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const enabledRef = useRef(enabled);
  const onActivateRef = useRef(onActivate);
  enabledRef.current = enabled;
  onActivateRef.current = onActivate;

  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  const startListening = useCallback(() => {
    if (!enabledRef.current || typeof window === "undefined") return;
    if (isRunningRef.current) return;

    // Check for browser support
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn("Speech recognition not supported in this browser");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    // Bug fix: hardcoded en-GB degrades accuracy for non-UK English speakers
    // and breaks detection for other languages entirely. Use the browser's
    // preferred language and fall back to en-GB only if unavailable.
    recognition.lang = navigator.language || "en-GB";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const lastResult = event.results[event.results.length - 1];

      // Check all alternatives (not just [0]) , Chrome sometimes puts the correct
      // transcription in alternative 1 or 2 with a lower score.
      // Confidence threshold is intentionally removed: Chrome Web Speech API on
      // macOS frequently returns 0.0 confidence for correct transcriptions.
      // The word-boundary regex below is the sole false-positive filter.
      const transcripts: string[] = [];
      for (let i = 0; i < lastResult.length; i++) {
        transcripts.push(lastResult[i].transcript.toLowerCase().trim());
      }

      for (const transcript of transcripts) {
        for (const wakeWord of wakeWords) {
          const escaped = wakeWord.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
          if (new RegExp(`\\b${escaped}\\b`).test(transcript)) {
            console.log(`[WakeWord] Detected: "${transcript}"`);
            onActivateRef.current();
            return;
          }
        }
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      // Filter out common non-critical errors
      if (event.error === "no-speech") {
        // Normal - just means no speech was detected, will retry automatically
        return;
      }
      if (event.error === "aborted") {
        // Normal - recognition was stopped intentionally
        return;
      }
      
      // Log other errors
      console.warn("Speech recognition error:", event.error);
      isRunningRef.current = false;
      
      // Don't retry if permission denied
      if (event.error !== "not-allowed" && enabledRef.current) {
        retryTimerRef.current = setTimeout(() => startListening(), 1000);
      }
    };

    recognition.onend = () => {
      isRunningRef.current = false;
      if (enabledRef.current) {
        retryTimerRef.current = setTimeout(() => startListening(), 100);
      }
    };

    try {
      recognition.start();
      isRunningRef.current = true;
      recognitionRef.current = recognition;
    } catch (err) {
      isRunningRef.current = false;
      console.warn("Could not start speech recognition:", err);
    }
  }, [wakeWords]);

  const stopListening = useCallback(() => {
    isRunningRef.current = false;
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    if (recognitionRef.current) {
      recognitionRef.current.onend = null;
      recognitionRef.current.onerror = null;
      recognitionRef.current.onresult = null;
      try {
        recognitionRef.current.stop();
      } catch {
        // already stopped
      }
      recognitionRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      startListening();
    } else {
      stopListening();
    }

    return () => stopListening();
  }, [enabled, startListening, stopListening]);

  return { startListening, stopListening };
}
