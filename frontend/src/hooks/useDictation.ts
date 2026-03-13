"use client";

import { useRef, useCallback, useState, useEffect } from "react";

interface DictationOptions {
  onSend: (text: string) => void;
  sendTriggers?: string[];
}

/**
 * Voice dictation for the command input.
 * Accumulates interim + final transcripts into the input field.
 * Saying any sendTrigger word (default: "send") submits the text.
 */
export function useDictation({
  onSend,
  sendTriggers = ["send", "submit", "go"],
}: DictationOptions) {
  const recognitionRef = useRef<any>(null);
  const isRunningRef = useRef(false);
  const [isDictating, setIsDictating] = useState(false);
  const [transcript, setTranscript] = useState("");
  const transcriptRef = useRef("");
  const onSendRef = useRef(onSend);
  onSendRef.current = onSend;

  useEffect(() => {
    return () => {
      if (isRunningRef.current) {
        stop();
      }
    };
  }, []);

  const stop = useCallback(() => {
    isRunningRef.current = false;
    setIsDictating(false);
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

  const start = useCallback(() => {
    if (typeof window === "undefined") return;
    if (isRunningRef.current) return;

    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SR) {
      console.warn("SpeechRecognition not supported");
      return;
    }

    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-GB";
    recognitionRef.current = recognition;

    recognition.onresult = (event: any) => {
      let interim = "";
      let finalChunk = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalChunk += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (finalChunk) {
        const lower = finalChunk.trim().toLowerCase();
        // Check if the final chunk is a send trigger
        if (sendTriggers.some((t) => lower === t || lower === t + ".")) {
          const toSend = transcriptRef.current.trim();
          if (toSend) {
            onSendRef.current(toSend);
            transcriptRef.current = "";
            setTranscript("");
          }
          return;
        }
        transcriptRef.current = (transcriptRef.current + " " + finalChunk).trim();
        setTranscript(transcriptRef.current);
      } else if (interim) {
        // Show interim as preview (appended to confirmed text)
        setTranscript((transcriptRef.current + " " + interim).trim());
      }
    };

    recognition.onerror = (event: any) => {
      if (event.error === "not-allowed") {
        stop();
      } else if (event.error === "no-speech") {
        console.log("No speech detected");
      } else if (event.error === "audio-capture") {
        console.log("No microphone found");
      }
    };

    recognition.onend = () => {
      // Restart automatically while dictation is active
      if (isRunningRef.current) {
        try {
          recognition.start();
        } catch {
          // already started
        }
      }
    };

    try {
      recognition.start();
      isRunningRef.current = true;
      setIsDictating(true);
    } catch (err) {
      console.warn("Dictation start failed:", err);
    }
  }, [sendTriggers, stop]);

  const clear = useCallback(() => {
    transcriptRef.current = "";
    setTranscript("");
  }, []);

  return { start, stop, clear, isDictating, transcript };
}
