/**
 * Wake Word Detection Hook
 * Enables hands-free activation with "Hey Spectra" or "Okay Spectra"
 */

import { useEffect, useRef, useState, useCallback } from 'react';

interface UseWakeWordOptions {
  enabled: boolean;
  onWakeWordDetected: () => void;
  wakeWords?: string[];
  sensitivity?: number; // 0-1, higher = more sensitive
}

export function useWakeWord({
  enabled,
  onWakeWordDetected,
  wakeWords = ['hey spectra', 'okay spectra', 'hi spectra'],
  sensitivity = 0.7,
}: UseWakeWordOptions) {
  const [isListening, setIsListening] = useState(false);
  const [lastDetection, setLastDetection] = useState<Date | null>(null);
  const recognitionRef = useRef<any>(null);
  const isProcessingRef = useRef(false);

  const normalizeText = useCallback((text: string): string => {
    return text.toLowerCase().trim().replace(/[.,!?]/g, '');
  }, []);

  const containsWakeWord = useCallback((text: string): boolean => {
    const normalized = normalizeText(text);
    return wakeWords.some(wakeWord => {
      const normalizedWakeWord = normalizeText(wakeWord);
      // Check for exact match or wake word at start of phrase
      return normalized === normalizedWakeWord || 
             normalized.startsWith(normalizedWakeWord + ' ') ||
             normalized.includes(' ' + normalizedWakeWord + ' ') ||
             normalized.endsWith(' ' + normalizedWakeWord);
    });
  }, [wakeWords, normalizeText]);

  const startListening = useCallback(() => {
    if (!enabled || isListening || isProcessingRef.current) return;

    // Check for browser support
    const SpeechRecognition = 
      (window as any).SpeechRecognition || 
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn('Wake word detection not supported in this browser');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';
      recognition.maxAlternatives = 3;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        if (isProcessingRef.current) return;

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          const transcript = result[0].transcript;

          // Check all alternatives for wake word
          for (let j = 0; j < result.length; j++) {
            const alternative = result[j].transcript;
            const confidence = result[j].confidence;

            if (confidence >= sensitivity && containsWakeWord(alternative)) {
              isProcessingRef.current = true;
              setLastDetection(new Date());
              onWakeWordDetected();
              
              // Stop listening briefly to avoid re-triggering
              recognition.stop();
              setTimeout(() => {
                isProcessingRef.current = false;
                if (enabled) {
                  startListening();
                }
              }, 2000);
              return;
            }
          }
        }
      };

      recognition.onerror = (event: any) => {
        console.error('[WakeWord] Error:', event.error);
        if (event.error === 'no-speech') {
          // This is normal, just restart
          recognition.stop();
          setTimeout(() => {
            if (enabled) startListening();
          }, 100);
        } else if (event.error === 'aborted') {
          // Intentional stop, don't restart
          setIsListening(false);
        } else {
          // Other errors, try to restart after delay
          setIsListening(false);
          setTimeout(() => {
            if (enabled) startListening();
          }, 1000);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
        // Auto-restart if still enabled and not processing
        if (enabled && !isProcessingRef.current) {
          setTimeout(() => startListening(), 100);
        }
      };

      try {
        recognition.start();
        recognitionRef.current = recognition;
      } catch (startError) {
        console.error('[WakeWord] recognition.start() failed:', startError);
        setIsListening(false);
        throw startError; // Re-throw to be caught by outer try-catch
      }
    } catch (error) {
      console.error('[WakeWord] Failed to start:', error);
      setIsListening(false);
    }
  }, [enabled, isListening, onWakeWordDetected, containsWakeWord, sensitivity]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
        recognitionRef.current = null;
      } catch (error) {
        console.error('[WakeWord] Failed to stop:', error);
      }
    }
    setIsListening(false);
    isProcessingRef.current = false;
  }, []);

  // Start/stop based on enabled state
  useEffect(() => {
    if (enabled) {
      startListening();
    } else {
      stopListening();
    }

    return () => {
      stopListening();
    };
  }, [enabled, startListening, stopListening]);

  return {
    isListening,
    lastDetection,
    startListening,
    stopListening,
  };
}
