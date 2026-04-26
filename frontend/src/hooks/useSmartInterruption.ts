/**
 * Smart Interruption Hook
 * Allows users to interrupt Spectra mid-response
 */

import { useEffect, useRef, useCallback } from 'react';

interface UseSmartInterruptionOptions {
  enabled: boolean;
  onInterruption: () => void;
  audioElement?: HTMLAudioElement | null;
}

export function useSmartInterruption({
  enabled,
  onInterruption,
  audioElement,
}: UseSmartInterruptionOptions) {
  const recognitionRef = useRef<any>(null);
  const isListeningRef = useRef(false);
  const lastInterruptionRef = useRef<number>(0);

  const stopAudioPlayback = useCallback(() => {
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
    }
  }, [audioElement]);

  const handleSpeechDetected = useCallback(() => {
    const now = Date.now();
    // Debounce interruptions (min 500ms between)
    if (now - lastInterruptionRef.current < 500) {
      return;
    }

    lastInterruptionRef.current = now;
    
    stopAudioPlayback();
    onInterruption();
  }, [stopAudioPlayback, onInterruption]);

  const startListening = useCallback(() => {
    if (!enabled || isListeningRef.current) return;

    const SpeechRecognition = 
      (window as any).SpeechRecognition || 
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        isListeningRef.current = true;
      };

      recognition.onresult = (event: any) => {
        // Detect any speech to trigger interruption
        if (event.results.length > 0) {
          const result = event.results[event.results.length - 1];
          if (result[0].transcript.trim().length > 0) {
            handleSpeechDetected();
          }
        }
      };

      recognition.onerror = (event: any) => {
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
          console.error('[SmartInterruption] Error:', event.error);
        }
      };

      recognition.onend = () => {
        isListeningRef.current = false;
        // Auto-restart if still enabled
        if (enabled) {
          setTimeout(() => startListening(), 100);
        }
      };

      recognition.start();
      recognitionRef.current = recognition;
    } catch (error) {
      console.error('[SmartInterruption] Failed to start:', error);
    }
  }, [enabled, handleSpeechDetected]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
        recognitionRef.current = null;
      } catch (error) {
        console.error('[SmartInterruption] Failed to stop:', error);
      }
    }
    isListeningRef.current = false;
  }, []);

  // Start/stop based on enabled state and audio playback
  useEffect(() => {
    if (enabled && audioElement && !audioElement.paused) {
      startListening();
    } else {
      stopListening();
    }

    return () => {
      stopListening();
    };
  }, [enabled, audioElement, startListening, stopListening]);

  // Listen for audio play/pause events
  useEffect(() => {
    if (!audioElement) return;

    const handlePlay = () => {
      if (enabled) startListening();
    };

    const handlePause = () => {
      stopListening();
    };

    const handleEnded = () => {
      stopListening();
    };

    audioElement.addEventListener('play', handlePlay);
    audioElement.addEventListener('pause', handlePause);
    audioElement.addEventListener('ended', handleEnded);

    return () => {
      audioElement.removeEventListener('play', handlePlay);
      audioElement.removeEventListener('pause', handlePause);
      audioElement.removeEventListener('ended', handleEnded);
    };
  }, [audioElement, enabled, startListening, stopListening]);

  return {
    stopAudioPlayback,
  };
}
