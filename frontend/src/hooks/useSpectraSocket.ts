"use client";

import { useRef, useCallback, useState, useEffect } from "react";

interface SpectraSocketOptions {
  onText: (text: string) => void;
  onTranscript: (text: string) => void;
  onAudio: (base64Data: string) => void;
  onAction: (action: string, params: Record<string, unknown>) => Promise<string>;
  onActionStart?: (action: string, params: Record<string, unknown>) => void;
  onActionComplete?: (action: string, result: string) => void;
  onTurnComplete?: () => void;
  onConnect: () => void;
  onDisconnect: () => void;
  onReconnecting?: (attempt: number) => void;
  onGeminiReconnecting?: () => void;
  onUsageLimit?: (info: { tier: string; used: number; limit: number }) => void;
  onGoAway?: (timeLeft: number) => void;
  audioDuckingEnabled?: boolean; // Enable audio ducking for screen reader compatibility
  audioDuckingLevel?: number; // Volume reduction level (0-1, default 0.5)
}

const RECONNECT_BASE_DELAY = 500;   // Faster reconnection
const RECONNECT_MAX_DELAY = 8000;   // Reduced max delay
const MAX_RECONNECT_ATTEMPTS = 15;  // More attempts for reliability

export function useSpectraSocket(options: SpectraSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const optionsRef = useRef(options);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalCloseRef = useRef(false);
  const [connectionQuality, setConnectionQuality] = useState<"good" | "degraded" | "poor">("good");
  const [isConnected, setIsConnected] = useState(false);
  const lastPongRef = useRef(0);
  const messageQueueRef = useRef<string[]>([]);
  const sessionIdRef = useRef<string>("");  // Persistent session ID for this tab
  const audioContextRef = useRef<AudioContext | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const screenReaderActiveRef = useRef(false);
  const cleanupMonitorRef = useRef<(() => void) | null>(null);
  const extCheckIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const latencyT1Ref = useRef<number>(0);
  const firstChunkLoggedRef = useRef<boolean>(false);
  optionsRef.current = options;

  /** Generate or retrieve persistent session ID for this browser tab */
  const getSessionId = useCallback((): string => {
    if (sessionIdRef.current) return sessionIdRef.current;
    
    // Try to get from sessionStorage (persists for tab lifetime)
    if (typeof window !== 'undefined' && window.sessionStorage) {
      const stored = sessionStorage.getItem('spectra_session_id');
      if (stored) {
        sessionIdRef.current = stored;
        return stored;
      }
    }
    
    // Generate cryptographically secure session ID
    const array = new Uint8Array(8);
    crypto.getRandomValues(array);
    const newId = `s-${Array.from(array).map(b => b.toString(16).padStart(2, '0')).join('')}`;
    sessionIdRef.current = newId;

    // Store in sessionStorage
    if (typeof window !== 'undefined' && window.sessionStorage) {
      sessionStorage.setItem('spectra_session_id', newId);
    }

    return newId;
  }, []);

  /** Initialize audio context and gain node for audio ducking */
  const initializeAudioDucking = useCallback(() => {
    if (!options.audioDuckingEnabled) return;
    
    try {
      if (typeof window !== 'undefined' && !audioContextRef.current) {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        audioContextRef.current = new AudioContextClass();
        gainNodeRef.current = audioContextRef.current.createGain();
        gainNodeRef.current.connect(audioContextRef.current.destination);
        gainNodeRef.current.gain.value = 1.0; // Full volume by default
      }
    } catch (error) {
      console.error('[SpectraSocket] Failed to initialize audio ducking:', error);
    }
  }, [options.audioDuckingEnabled]);

  /** Detect if screen reader is active via UA string only.
   *  DOM heuristics (aria-live, .sr-only, aria-label) were removed — Spectra's
   *  own ARIA-compliant page matches all of them, causing permanent false positives. */
  const detectScreenReader = useCallback(() => {
    if (typeof window === 'undefined') return false;
    const ua = navigator.userAgent.toLowerCase();
    return ua.includes('nvda') || ua.includes('jaws') || ua.includes('voiceover');
  }, []);

  /** Apply audio ducking when screen reader is detected */
  const applyAudioDucking = useCallback((duck: boolean) => {
    if (!options.audioDuckingEnabled || !gainNodeRef.current) return;
    
    const duckingLevel = options.audioDuckingLevel ?? 0.5;
    const targetVolume = duck ? duckingLevel : 1.0;
    const currentTime = audioContextRef.current?.currentTime ?? 0;
    
    // Smooth volume transition over 100ms
    gainNodeRef.current.gain.cancelScheduledValues(currentTime);
    gainNodeRef.current.gain.setValueAtTime(gainNodeRef.current.gain.value, currentTime);
    gainNodeRef.current.gain.linearRampToValueAtTime(targetVolume, currentTime + 0.1);
    
    screenReaderActiveRef.current = duck;
  }, [options.audioDuckingEnabled, options.audioDuckingLevel]);

  /** Monitor for screen reader activity */
  const monitorScreenReaderActivity = useCallback(() => {
    if (!options.audioDuckingEnabled || typeof window === 'undefined') return;
    
    // Initial detection
    const isActive = detectScreenReader();
    if (isActive !== screenReaderActiveRef.current) {
      applyAudioDucking(isActive);
    }
    
    // Monitor only ARIA live regions , observing document.body is too expensive
    const liveRegions = Array.from(document.querySelectorAll('[aria-live]'));
    if (liveRegions.length === 0) return;

    let duckTimer: ReturnType<typeof setTimeout> | null = null;
    const observer = new MutationObserver(() => {
      // Any mutation inside an aria-live region means screen reader is speaking
      applyAudioDucking(true);
      if (duckTimer) clearTimeout(duckTimer);
      duckTimer = setTimeout(() => applyAudioDucking(false), 2000);
    });

    for (const region of liveRegions) {
      observer.observe(region, { childList: true, subtree: true, characterData: true });
    }

    return () => {
      observer.disconnect();
      if (duckTimer) clearTimeout(duckTimer);
    };
  }, [options.audioDuckingEnabled, detectScreenReader, applyAudioDucking]);

  const getWsUrl = useCallback(() => {
    const base = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8080/ws";
    
    // Get persistent session ID for this browser tab
    const sessionId = getSessionId();
    
    const params = new URLSearchParams();
    params.append("session_id", sessionId);
    
    return `${base}?${params.toString()}`;
  }, [getSessionId]);

  const flushQueue = useCallback((ws: WebSocket) => {
    while (messageQueueRef.current.length > 0 && ws.readyState === WebSocket.OPEN) {
      const msg = messageQueueRef.current.shift();
      if (msg) {
        ws.send(msg);
      }
    }
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (intentionalCloseRef.current) return;

    // Stop reconnecting after max attempts
    if (reconnectAttemptRef.current >= MAX_RECONNECT_ATTEMPTS) {
      console.error("[SpectraSocket] Max reconnection attempts reached");
      optionsRef.current.onDisconnect();
      return;
    }

    const delay = Math.min(
      RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttemptRef.current),
      RECONNECT_MAX_DELAY
    );
    reconnectAttemptRef.current++;
    optionsRef.current.onReconnecting?.(reconnectAttemptRef.current);

    reconnectTimerRef.current = setTimeout(() => {
      connectInternal();
    }, delay);
  }, []);

  /**
   * Shared message handler , single source of truth for both connectInternal and connect.
   * Safe JSON.parse: malformed backend messages no longer crash the session.
   * Declared after scheduleReconnect to avoid forward-reference errors.
   */
  const handleMessage = useCallback((ws: WebSocket) => async (event: MessageEvent) => {
    let msg: Record<string, unknown>;
    try {
      msg = JSON.parse(event.data as string);
    } catch {
      console.warn('[SpectraSocket] Received non-JSON message, ignoring');
      return;
    }

    switch (msg.type) {
      case "text":
        optionsRef.current.onText(msg.data as string);
        break;
      case "transcript":
        // T1: Gemini finished hearing the user — processing starts now
        latencyT1Ref.current = performance.now();
        firstChunkLoggedRef.current = false;
        optionsRef.current.onTranscript(msg.data as string);
        break;
      case "audio":
        // T2: first audio chunk back from Gemini — log transcript→audio gap
        if (!firstChunkLoggedRef.current && latencyT1Ref.current > 0) {
          const ms = Math.round(performance.now() - latencyT1Ref.current);
          console.log(`[Spectra Latency] transcript→first_audio: ${ms}ms`);
          // Accumulate samples on window for easy console inspection
          if (typeof window !== 'undefined') {
            (window as any).__spectraLatency = (window as any).__spectraLatency ?? [];
            (window as any).__spectraLatency.push(ms);
            const samples: number[] = (window as any).__spectraLatency;
            if (samples.length >= 3) {
              const sorted = [...samples].sort((a, b) => a - b);
              const median = sorted[Math.floor(sorted.length / 2)];
              console.log(`[Spectra Latency] median over ${samples.length} samples: ${median}ms  (all: ${samples.join(', ')}ms)`);
            }
          }
          firstChunkLoggedRef.current = true;
        }
        optionsRef.current.onAudio(msg.data as string);
        break;
      case "action": {
        const actionName = msg.action as string;
        const actionParams = (msg.params as Record<string, unknown>) ?? {};
        optionsRef.current.onActionStart?.(actionName, actionParams);
        const result = await optionsRef.current.onAction(actionName, actionParams);
        optionsRef.current.onActionComplete?.(actionName, result);
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "action_result", result, id: msg.id }));
        }
        break;
      }
      case "heartbeat": {
        lastPongRef.current = Date.now();
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "pong" }));
        }
        setConnectionQuality((msg.uptime as number) > 0 ? "good" : "degraded");
        break;
      }
      case "turn_complete":
        optionsRef.current.onTurnComplete?.();
        break;
      case "usage_limit":
        optionsRef.current.onUsageLimit?.({
          tier: (msg.tier as string) ?? "free",
          used: (msg.used as number) ?? 0,
          limit: (msg.limit as number) ?? 0,
        });
        break;
      case "go_away":
        optionsRef.current.onGoAway?.((msg.time_left as number) ?? 0);
        setTimeout(() => {
          if (!intentionalCloseRef.current) scheduleReconnect();
        }, ((msg.time_left as number) ?? 5) * 1000);
        break;
      case "gemini_reconnecting":
        // Backend is transparently reconnecting to Gemini (session limit hit).
        // The browser WebSocket stays open , this is NOT a connection failure.
        optionsRef.current.onGeminiReconnecting?.();
        break;
      // Silently ignore status/tool_status , internal backend telemetry
    }
  }, [scheduleReconnect]);

  const connectInternal = useCallback(() => {
    // Guard: close any existing WebSocket before opening a new one.
    // Without this, reconnection creates a second WS while the first
    // is still alive → duplicate Gemini sessions → double audio.
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      const old = wsRef.current;
      wsRef.current = null;
      old.onclose = null;
      old.close(1000);
    }

    const url = getWsUrl();
    const ws = new WebSocket(url);

    ws.onopen = () => {
      wsRef.current = ws;
      reconnectAttemptRef.current = 0;
      setConnectionQuality("good");
      setIsConnected(true);
      lastPongRef.current = Date.now();
      optionsRef.current.onConnect();
      // Tell the backend whether the browser extension is installed.
      // The backend injects this into Gemini's context so it knows upfront
      // whether browser actions (click, type, navigate, scroll) will work.
      let extAvailable = typeof window !== 'undefined' && !!(window as any).spectraExtensionAvailable;
      ws.send(JSON.stringify({ type: "extension_status", available: extAvailable }));
      // Re-send extension_status when extension becomes available (it may respond to ping after connect)
      let lastSentExtension = extAvailable;
      if (extCheckIntervalRef.current) clearInterval(extCheckIntervalRef.current);
      extCheckIntervalRef.current = setInterval(() => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) return;
        const nowAvailable = typeof window !== 'undefined' && !!(window as any).spectraExtensionAvailable;
        if (nowAvailable && !lastSentExtension) {
          wsRef.current!.send(JSON.stringify({ type: "extension_status", available: true }));
          lastSentExtension = true;
          clearInterval(extCheckIntervalRef.current!);
          extCheckIntervalRef.current = null;
        }
      }, 2000);
      window.setTimeout(() => {
        if (extCheckIntervalRef.current) {
          clearInterval(extCheckIntervalRef.current);
          extCheckIntervalRef.current = null;
        }
      }, 16000);
      flushQueue(ws);
    };

    ws.onerror = () => {
      // Error handling is done in onclose
    };

    ws.onclose = (event) => {
      wsRef.current = null;
      setIsConnected(false);
      if (!intentionalCloseRef.current && event.code !== 1000) {
        scheduleReconnect();
      } else {
        optionsRef.current.onDisconnect();
      }
    };

    ws.onmessage = handleMessage(ws);
  }, [flushQueue, scheduleReconnect, getWsUrl]);

  const connect = useCallback(() => {
    return new Promise<void>((resolve, reject) => {
      // Close any existing WebSocket before opening a new one.
      // handleStop() keeps the WS open (intentional — avoids latency on quick
      // Q-stop + Q-start). Without this guard, each Q-start opens a second WS
      // while the first stays alive → two backend sessions → duplicate log lines,
      // double audio, and wasted Gemini quota.
      if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
        const old = wsRef.current;
        wsRef.current = null;
        old.onclose = null; // prevent scheduleReconnect firing for this intentional close
        old.close(1000);
      }

      // Cancel any pending auto-reconnect — we're connecting manually now.
      // Without this, connectInternal() fires after connect() succeeds and kills the new session.
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }

      intentionalCloseRef.current = false;
      reconnectAttemptRef.current = 0;

      // Initialize audio ducking
      initializeAudioDucking();
      
      // Start monitoring screen reader activity
      cleanupMonitorRef.current?.(); // clean up any previous observer
      cleanupMonitorRef.current = monitorScreenReaderActivity() ?? null;

      // Connect directly without token
      const url = getWsUrl();
      const ws = new WebSocket(url);

      const timeout = setTimeout(() => {
        ws.close();
        reject(new Error("Connection timeout"));
      }, 25000);

      ws.onopen = () => {
        clearTimeout(timeout);
        wsRef.current = ws;
        reconnectAttemptRef.current = 0;
        setConnectionQuality("good");
        setIsConnected(true);
        lastPongRef.current = Date.now();
        optionsRef.current.onConnect();
        // Tell backend whether the extension is installed
        let extAvailable = typeof window !== 'undefined' && !!(window as any).spectraExtensionAvailable;
        ws.send(JSON.stringify({ type: "extension_status", available: extAvailable }));
        let lastSentExtension = extAvailable;
        if (extCheckIntervalRef.current) clearInterval(extCheckIntervalRef.current);
        extCheckIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState !== WebSocket.OPEN) return;
          const nowAvailable = typeof window !== 'undefined' && !!(window as any).spectraExtensionAvailable;
          if (nowAvailable && !lastSentExtension) {
            wsRef.current!.send(JSON.stringify({ type: "extension_status", available: true }));
            lastSentExtension = true;
            clearInterval(extCheckIntervalRef.current!);
            extCheckIntervalRef.current = null;
          }
        }, 2000);
        window.setTimeout(() => {
          if (extCheckIntervalRef.current) {
            clearInterval(extCheckIntervalRef.current);
            extCheckIntervalRef.current = null;
          }
        }, 16000);
        flushQueue(ws);

        // Re-wire for reconnection support
        ws.onclose = (event) => {
          wsRef.current = null;
          setIsConnected(false);
          if (!intentionalCloseRef.current && event.code !== 1000) {
            scheduleReconnect();
          } else {
            optionsRef.current.onDisconnect();
          }
        };

        // Use the shared safe handler , no more duplicate 40-line switch blocks
        ws.onmessage = handleMessage(ws);

        resolve();
      };

      ws.onerror = () => {
        clearTimeout(timeout);
        reject(new Error("WebSocket connection failed"));
      };
    });
  }, [flushQueue, scheduleReconnect, getWsUrl, handleMessage, initializeAudioDucking, monitorScreenReaderActivity]);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    wsRef.current?.close(1000);
    wsRef.current = null;
    setIsConnected(false);
    
    // Cleanup extension check interval
    if (extCheckIntervalRef.current) {
      clearInterval(extCheckIntervalRef.current);
      extCheckIntervalRef.current = null;
    }

    // Cleanup screen reader monitor
    cleanupMonitorRef.current?.();
    cleanupMonitorRef.current = null;

    // Cleanup audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
      gainNodeRef.current = null;
    }

    // NOTE: We intentionally DO NOT clear sessionIdRef.current here
    // This allows reconnection to reuse the same session_id
    console.log(`[SpectraSocket] Disconnected but preserving session_id: ${sessionIdRef.current}`);
  }, []);

  const safeSend = useCallback((data: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    } else {
      // Queue messages during reconnection (only keep last 10)
      messageQueueRef.current.push(data);
      if (messageQueueRef.current.length > 10) {
        messageQueueRef.current.shift();
      }
    }
  }, []);

  const sendAudio = useCallback((base64Data: string) => {
    // Audio is time-sensitive , don't queue, just drop if not connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "audio", data: base64Data }));
    }
  }, []);

  const sendScreenshot = useCallback((base64Data: string, width?: number, height?: number) => {
    // Queue screenshots so they're sent when connection is restored
    const msg = JSON.stringify({
      type: "screenshot",
      data: base64Data,
      width: width ?? 0,
      height: height ?? 0,
    });
    // Hot path , no logging here
    safeSend(msg);
  }, [safeSend]);

  const sendText = useCallback((text: string) => {
    safeSend(JSON.stringify({ type: "text", data: text }));
  }, [safeSend]);

  const sendCancel = useCallback(() => {
    safeSend(JSON.stringify({ type: "cancel" }));
  }, [safeSend]);

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      // Cleanup extension check interval
      if (extCheckIntervalRef.current) {
        clearInterval(extCheckIntervalRef.current);
        extCheckIntervalRef.current = null;
      }

      // Cleanup screen reader monitor
      cleanupMonitorRef.current?.();
      cleanupMonitorRef.current = null;

      // Cleanup audio context
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
        gainNodeRef.current = null;
      }

      // Cleanup WebSocket
      if (wsRef.current) {
        wsRef.current.close(1000);
        wsRef.current = null;
      }

      // Cleanup reconnect timer
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, []);

  return {
    connect,
    disconnect,
    sendAudio,
    sendFrame: sendScreenshot,
    sendText,
    sendCancel,
    isConnected,
    connectionQuality,
  };
}
