"use client";

import { useRef, useCallback, useEffect, useState } from "react";

interface OllamaAudioOptions {
  enabled: boolean;
  offlineMode: boolean;
  isActive: boolean;
  onTranscript: (text: string) => void;
  onSendText: (text: string) => void;
  onResponseStart?: () => void;
  onResponseEnd?: () => void;
}

/**
 * Audio pipeline for Ollama offline mode.
 *
 * Flow:
 * 1. Capture voice → Web Speech API (SpeechRecognition)
 * 2. Convert to text → Send to backend
 * 3. Receive text response from backend
 * 4. Convert to speech → Web Speech API (SpeechSynthesis)
 *
 * This makes Ollama feel like a full voice assistant even though it's text-based.
 */
export function useOllamaAudio(options: OllamaAudioOptions) {
  const { enabled, offlineMode, isActive, onTranscript, onSendText, onResponseStart, onResponseEnd } = options;

  const recognitionRef = useRef<any>(null);
  const synthesisRef = useRef<SpeechSynthesisUtterance | null>(null);
  const isListeningRef = useRef(false);
  const isResponsePlayingRef = useRef(false);
  const [transcriptText, setTranscriptText] = useState("");

  // Initialize Web Speech API (recognition)
  useEffect(() => {
    if (!enabled || !offlineMode) return;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("[OllamaAudio] SpeechRecognition not supported");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    let interimTranscript = "";

    recognition.onstart = () => {
      isListeningRef.current = true;
      console.log("[OllamaAudio] Listening started");
    };

    recognition.onresult = (event: any) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          interimTranscript += transcript + " ";
        } else {
          interim += transcript;
        }
      }

      const fullTranscript = interimTranscript + interim;
      setTranscriptText(fullTranscript);
      onTranscript(fullTranscript);
    };

    recognition.onerror = (event: any) => {
      console.error("[OllamaAudio] Speech recognition error:", event.error);
      isListeningRef.current = false;
    };

    recognition.onend = () => {
      isListeningRef.current = false;
      console.log("[OllamaAudio] Listening stopped");

      // If we got final transcript, send it
      if (interimTranscript.trim()) {
        console.log("[OllamaAudio] Final transcript:", interimTranscript.trim());
        onSendText(interimTranscript.trim());
        interimTranscript = "";
        setTranscriptText("");
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {
          // Already stopped
        }
      }
    };
  }, [enabled, offlineMode, onTranscript, onSendText]);

  // Start listening for voice input
  const startListening = useCallback(() => {
    if (!recognitionRef.current || isListeningRef.current) return;

    try {
      setTranscriptText("");
      recognitionRef.current.start();
    } catch (e) {
      console.error("[OllamaAudio] Failed to start listening:", e);
    }
  }, []);

  // Stop listening
  const stopListening = useCallback(() => {
    if (!recognitionRef.current || !isListeningRef.current) return;

    try {
      recognitionRef.current.stop();
    } catch (e) {
      console.error("[OllamaAudio] Failed to stop listening:", e);
    }
  }, []);

  // Speak text response using Web Speech API
  const speakResponse = useCallback((text: string) => {
    if (!enabled || !offlineMode) return;

    // Cancel any ongoing speech
    if (isResponsePlayingRef.current) {
      window.speechSynthesis.cancel();
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    utterance.onstart = () => {
      isResponsePlayingRef.current = true;
      onResponseStart?.();
      console.log("[OllamaAudio] Speech synthesis started");
    };

    utterance.onend = () => {
      isResponsePlayingRef.current = false;
      onResponseEnd?.();
      console.log("[OllamaAudio] Speech synthesis ended");

      // Resume listening after response finishes (for continuous conversation)
      if (isActive) {
        setTimeout(() => {
          startListening();
        }, 500);
      }
    };

    utterance.onerror = (event: any) => {
      console.error("[OllamaAudio] Speech synthesis error:", event.error);
      isResponsePlayingRef.current = false;
      onResponseEnd?.();
    };

    synthesisRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }, [enabled, offlineMode, isActive, onResponseStart, onResponseEnd, startListening]);

  // Stop speaking
  const stopSpeaking = useCallback(() => {
    if (isResponsePlayingRef.current) {
      window.speechSynthesis.cancel();
      isResponsePlayingRef.current = false;
    }
  }, []);

  return {
    startListening,
    stopListening,
    speakResponse,
    stopSpeaking,
    isListening: isListeningRef.current,
    isSpeaking: isResponsePlayingRef.current,
    transcriptText,
  };
}
