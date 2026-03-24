"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useSpectraSocket } from "@/hooks/useSpectraSocket";
import { useAudioStream } from "@/hooks/useAudioStream";
import { useScreenCapture } from "@/hooks/useScreenCapture";
import { useVoiceActivation } from "@/hooks/useVoiceActivation";
import { useOnboarding } from "@/hooks/useOnboarding";
import { useFeedback } from "@/hooks/useFeedback";
import { ActionExecutor } from "@/lib/actionExecutor";
import { PcmAudioPlayer } from "@/lib/audioPlayer";
import { listenForExtension, isExtensionAvailable } from "@/lib/extensionBridge";
import { OnboardingGuide } from "@/components/OnboardingGuide";
import { getFeedbackSystem } from "@/lib/feedbackSystem";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

/**
 * Strip ALL model inner thoughts, meta-commentary, and process narration.
 * Module-level constant , never recreated per call.
 */
const THINKING_PHRASES = [
  "i've determined", "i've just refined", "i've analysed", "i've begun",
  "i've identified", "i've noted", "i've compiled", "i've hit a snag",
  "i've now analysed", "i'm seeing", "i am seeing", "i'm viewing",
  "i'm starting with", "i'm preparing to", "i'm trying to",
  "i'm puzzled", "i'm still trying", "i'm zeroing", "i'm concentrating",
  "i believe the user", "i plan to", "i will formulate",
  "my immediate task", "my focus is", "my analysis",
  "my next step", "my primary focus",
  "to accomplish this", "this will allow", "this step is",
  "appears incomplete", "lacks context", "remains ambiguous",
  "let me analyze", "let me examine", "let me check",
  "looking at the screen", "based on what i see",
  "i need to understand", "i need to figure out",
  "establishing a friendly", "creating a comprehensive",
  // Inner-thought verbs seen leaking through
  "i'm verifying", "i'm revisiting", "i'm re-examining", "i'm exploring",
  "i'm retrying", "i'm prepared to", "i'm re-analysing", "i'm re-",
  "my next action", "the previous attempt", "a fresh screen",
  "its coordinates are", "i've re-analysed", "once i understand",
  "i'll target", "i'll retry", "prime candidate",
];

const MAX_MESSAGES = 100;

function stripThinking(raw: string): string {
  if (!raw) return raw;
  let t = raw;
  t = t.replace(/<think>[\s\S]*?<\/think>/gi, "");
  t = t.replace(/\*\*[A-Z][^*]{2,80}\*\*\s*/g, "");
  const sentences = t.split(/(?<=[.!?])\s+/);
  const kept = sentences.filter((s) => {
    const lower = s.toLowerCase().trim();
    if (lower.length < 5) return false;
    return !THINKING_PHRASES.some((phrase) => lower.includes(phrase));
  });
  t = kept.join(" ");
  t = t.replace(/(?:^|\.\s+)(?:Initiating|Gathering|Refining|Analysing|Understanding|Processing|Examining|Registering|Currently|Specifically|Establishing|Verifying|Revisiting|Exploring|Retrying|Targeting|Reconsidering|Rechecking|Reassessing)\s[^.!?]*[.!?]/gi, ". ");
  t = t.replace(/Now,?\s+I\s+am\s+\w+ing[^.!?]*[.!?]/gi, "");
  t = t.replace(/I\s+am\s+(?:analyzing|examining|reviewing|understanding|processing|also making note|seeing|viewing)[^.!?]*[.!?]/gi, "");
  t = t.replace(/I'?m\s+re-?\w+ing\b[^.!?]*[.!?]/gi, "");
  t = t.replace(/The previous attempt[^.!?]*[.!?]/gi, "");
  t = t.replace(/My next (?:action|move|attempt)[^.!?]*[.!?]/gi, "");
  t = t.replace(/Once I (?:understand|have|can|know)[^.!?]*[.!?]/gi, "");
  t = t.replace(/\s+/g, " ").replace(/^\s*[.!?,]\s*/, "").replace(/\.\s*\./g, ".").trim();
  return t;
}

type ConnectionState = "connected" | "disconnected" | "reconnecting" | "failed";

// Human-readable action names
function humanizeAction(action: string): string {
  const map: Record<string, string> = {
    describe_screen: "Looking at your screen",
    click_element: "Clicking",
    type_text: "Typing",
    scroll_page: "Scrolling",
    press_key: "Pressing key",
    navigate: "Navigating",
    confirm_action: "Confirming action",
  };
  return map[action] ?? action.replace(/_/g, " ");
}

// Humanize action result for screen reader announcement (low-latency ARIA feedback, before Gemini speaks)
function humanizeResult(action: string, result: string): string | null {
  const lower = result.toLowerCase();
  if (lower.startsWith("error") || lower.includes("failed") || lower.includes("timeout") || lower.includes("no_element")) {
    return null; // Spectra's voice will handle failures
  }

  if (action === "navigate") {
    const url = result.replace("navigated_to_", "");
    try {
      const domain = new URL(url).hostname.replace(/^www\./, "");
      return `Page loaded: ${domain}.`;
    } catch { return "Page loaded."; }
  }

  if (action === "click_element") {
    if (result.includes("navigate_expected")) {
      const dest = result.split(":").slice(1).join(":").trim();
      let label = dest;
      try { label = new URL(dest).pathname.split("/").filter(Boolean).pop() || new URL(dest).hostname; } catch { /* keep raw */ }
      return `Opening${label ? " " + label.replace(/[-_]/g, " ") : " link"}. Loading...`;
    }
    return null; // non-link clicks: Gemini handles the announcement
  }

  if (action === "scroll_page") {
    if (result.includes("reached_bottom")) return "Reached the bottom of the page.";
    if (result.includes("reached_top")) return "Reached the top of the page.";
    const dir = result.includes("scrolled_up") ? "up" : "down";
    return `Scrolled ${dir}.`;
  }

  if (action === "type_text") {
    const field = result.replace("typed_into_", "").replace(/_/g, " ");
    return `Typed into ${field}.`;
  }

  return null;
}

export default function Home() {
  // Core state
  const [isActive, setIsActive] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState("");
  const [currentResponse, setCurrentResponse] = useState("");
  const [statusText, setStatusText] = useState("Your screen, your voice, your way");
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const extensionBannerTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [pendingMessages, setPendingMessages] = useState(0);
  const [isThinking, setIsThinking] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [assertiveAnnouncement, setAssertiveAnnouncement] = useState("");
  const [politeAnnouncement, setPoliteAnnouncement] = useState("");
  const [extensionReady, setExtensionReady] = useState(false);
  const [showExtensionBanner, setShowExtensionBanner] = useState(false);

  const { isFirstTime, hasSharedScreen, shouldShowOnboarding, markScreenShared, dismissOnboarding, markOnboardingComplete } = useOnboarding();

  // Multimodal Feedback System - 10X User Experience
  const feedback = useFeedback({
    audioEnabled: true,
    visualEnabled: true,
    hapticEnabled: true,
  });

  // Refs
  const actionExecutorRef = useRef(new ActionExecutor());
  const audioPlayerRef = useRef(new PcmAudioPlayer());
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioContextWarmedRef = useRef(false);
  const geminiReconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmuteSafetyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Multimodal Feedback System - 10X User Experience
  const feedbackSystemRef = useRef(getFeedbackSystem({
    audioEnabled: true,
    visualEnabled: true,
    hapticEnabled: true,
  }));

  const announceAssertive = useCallback((msg: string) => {
    setAssertiveAnnouncement("");
    requestAnimationFrame(() => setAssertiveAnnouncement(msg));
  }, []);

  const announcePolite = useCallback((msg: string) => {
    setPoliteAnnouncement("");
    requestAnimationFrame(() => setPoliteAnnouncement(msg));
  }, []);

  useEffect(() => {
    listenForExtension();
    // Poll extension availability for UI indicator
    const checkExtension = () => setExtensionReady(isExtensionAvailable());
    const id = setInterval(checkExtension, 1500);
    checkExtension();
    // Delay banner by 2s — extension pings back within ~500ms if installed,
    // so showing it immediately causes a visible flicker on every load.
    extensionBannerTimerRef.current = setTimeout(() => setShowExtensionBanner(true), 2000);
    return () => {
      clearInterval(id);
      if (extensionBannerTimerRef.current) clearTimeout(extensionBannerTimerRef.current);
    };
  }, []);

  useEffect(() => {
    document.body.tabIndex = -1;
    document.body.focus();
  }, []);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLButtonElement ||
        e.target instanceof HTMLTextAreaElement
      ) return;
      document.body.focus();
    };
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  useEffect(() => {
    const id = setTimeout(() => {
      requestAnimationFrame(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      });
    }, 50);
    return () => clearTimeout(id);
  }, [messages, currentResponse]);

  useEffect(() => {
    const executor = actionExecutorRef.current;
    return () => {
      handleFullStop();
      executor.destroy();
    };
  }, []);

  // Sync speaking state with actual audio playback
  useEffect(() => {
    const interval = setInterval(() => {
      const isActuallyPlaying = audioPlayerRef.current.playing;
      setIsSpeaking(isActuallyPlaying);
    }, 100); // Check every 100ms

    return () => clearInterval(interval);
  }, []);

  // Socket
  const { connect, disconnect, sendAudio, sendText, sendFrame, isConnected } = useSpectraSocket({
    onText: (text) => {
      const cleaned = stripThinking(text);
      if (cleaned) setCurrentResponse((prev) => prev + cleaned);
      setIsThinking(false);
    },
    onTranscript: (text) => {
      const trimmed = text.trim();
      // Drop Gemini noise annotations and hallucinated non-speech fragments
      const isNoise =
        !trimmed ||
        trimmed.startsWith("<noise>") ||
        trimmed.startsWith("[noise]") ||
        /^[\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF]+$/.test(trimmed) || // pure Arabic/CJK noise
        trimmed.length <= 1;
      if (isNoise) return;
      setCurrentTranscript(trimmed);
      setMessages((prev) => {
        const next = [...prev, { role: "user" as const, content: trimmed, timestamp: Date.now() }];
        return next.length > MAX_MESSAGES ? next.slice(-MAX_MESSAGES) : next;
      });
      setCurrentTranscript("");
      setIsThinking(true);
      announcePolite(`You said: ${trimmed}. Spectra is thinking…`);
    },
    onAudio: (base64Data) => {
      muteMic();
      // Warm up again so AudioContext is running (e.g. after tab background)
      audioPlayerRef.current.warmup();
      setIsSpeaking(true); // Orb shows "speaking" as soon as we get a chunk
      audioPlayerRef.current.play(base64Data);
    },
    onAction: async (action, params) => {
      const feedback = feedbackSystemRef.current;
      try {
        // Provide feedback for action start
        await feedback.provideFeedback(
          { type: action as any, params },
          { success: true }
        );
        
        const result = await actionExecutorRef.current.execute(action, params);
        
        // Provide feedback for action success
        await feedback.showSuccess();
        
        return result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[Spectra] Action '${action}' threw:`, msg);
        
        // Provide feedback for action error
        await feedback.showError(msg);
        
        return `error: ${msg}`;
      }
    },
    onActionStart: (action) => {
      const label = humanizeAction(action);
      setStatusText(`${label}...`);
      announcePolite(`${label}...`);
    },
    onActionComplete: (action, result) => {
      const msg = humanizeResult(action, result);
      if (msg) announcePolite(msg);
      // Revert status to listening after action
      setStatusText(isActive ? "Listening…" : "Press Q or say “Hey Spectra”");
    },
    onTurnComplete: () => {
      // Unmute AFTER audio finishes playing , not immediately on turn_complete.
      // turn_complete arrives while Web Audio API still has chunks scheduled ahead.
      // If we unmute immediately, the mic picks up the playing audio → Gemini
      // hears itself → conversation becomes one-way/looping.
      // Bug fix: both the safety timer and notifyWhenDone can fire doUnmute.
      // Without the hasFired guard, unmuteMic() is called twice , double-unmute
      // can re-open the mic while audio is still playing → feedback loop.
      let hasFired = false;
      const doUnmute = () => {
        if (hasFired) return;
        hasFired = true;
        if (unmuteSafetyTimerRef.current) {
          clearTimeout(unmuteSafetyTimerRef.current);
          unmuteSafetyTimerRef.current = null;
        }
        unmuteMic();
        // Announce "Listening" via ARIA so blind/accessibility users know it's
        // safe to speak — without this, they have no audio cue for when the mic
        // unmutes and may speak into a muted mic, getting no response.
        announceAssertive("Listening");
      };
      // Safety: force-unmute after 2.5s even if audio never fires onended
      // (8s hard backstop handles the case where Gemini dies without sending turn_complete)
      unmuteSafetyTimerRef.current = setTimeout(doUnmute, 2500);
      audioPlayerRef.current.notifyWhenDone(doUnmute);

      // Update speaking state when turn completes
      setIsSpeaking(audioPlayerRef.current.playing);

      if (currentResponse.trim()) {
        const finalText = stripThinking(currentResponse);
        if (finalText.trim()) {
          setMessages((prev) => {
            const next = [...prev, { role: "assistant" as const, content: finalText, timestamp: Date.now() }];
            return next.length > MAX_MESSAGES ? next.slice(-MAX_MESSAGES) : next;
          });
          announcePolite(finalText);
        }
        setCurrentResponse("");
      }
      setIsThinking(false);
      setStatusText(isActive ? "Listening…" : "Press Q or say “Hey Spectra”");
    },
    onConnect: () => {
      setConnectionState("connected");
      setReconnectAttempt(0);
      setStatusText(isActive ? "Listening…" : "Press Q or say “Hey Spectra”");
      announceAssertive("Spectra is connected and ready. Press Q to start, or say Hey Spectra.");
      if (pendingMessages > 0) setPendingMessages(0);
    },
    onDisconnect: () => {
      setConnectionState("disconnected");
      setStatusText("Disconnected");
      announceAssertive("Spectra has disconnected.");
    },
    onReconnecting: (attempt) => {
      setConnectionState("reconnecting");
      setReconnectAttempt(attempt);
      setStatusText(`Reconnecting (${attempt})...`);
      if (attempt === 1) announceAssertive("Connection lost. Reconnecting...");
      if (attempt >= 10) {
        setConnectionState("failed");
        setStatusText("Connection failed");
        announceAssertive("Could not reconnect. Please press Q to try again.");
      }
    },
    onGeminiReconnecting: () => {
      // Gemini internally reconnected , the browser WebSocket is still alive.
      // Just show a transient status; never change connectionState.
      setStatusText("Reconnecting...");
      if (geminiReconnectTimerRef.current) clearTimeout(geminiReconnectTimerRef.current);
      geminiReconnectTimerRef.current = setTimeout(() => {
        setStatusText(isActive ? "Listening…" : "Press Q or say “Hey Spectra”");
      }, 3000);
      // If Gemini dies mid-turn, turn_complete never arrives → mic stays muted forever.
      // Force-unmute and stop stale audio so the user can speak again after reconnect.
      if (unmuteSafetyTimerRef.current) {
        clearTimeout(unmuteSafetyTimerRef.current);
        unmuteSafetyTimerRef.current = null;
      }
      audioPlayerRef.current.stop();
      unmuteMic();
    },
  });

  const { startMic, stopMic, muteMic, unmuteMic } = useAudioStream({
    onAudioChunk: (base64Pcm) => {
      if (isConnected && isActive) sendAudio(base64Pcm);
    },
  });

  const { startCapture, stopCapture } = useScreenCapture({
    onFrame: (base64Jpeg, width, height) => {
      if (isConnected && isActive) sendFrame(base64Jpeg, width, height);
    },
    fps: 3,
  });

  useVoiceActivation({
    enabled: !isActive,
    wakeWords: ["hey spectra", "start spectra", "ok spectra", "spectra"],
    onActivate: () => { handleStart(); },
  });

  const handleFullStop = useCallback(() => {
    setIsActive(false);
    setIsListening(false);
    setIsScreenSharing(false);
    setIsSpeaking(false);
    stopMic();
    stopCapture();
    audioPlayerRef.current.stop();
    disconnect();
    setMessages([]);
    setCurrentTranscript("");
    setCurrentResponse("");
    setStatusText("Your screen, your voice, your way");
    setConnectionState("disconnected");
    setIsThinking(false);
    setPendingMessages(0);
  }, [stopMic, stopCapture, disconnect]);

  const handleStart = useCallback(async () => {
    if (isActive) return;
    try {
      // Pre-warm AudioContext during user gesture so Chrome doesn't block playback
      if (!audioContextWarmedRef.current) {
        audioContextWarmedRef.current = true;
        audioPlayerRef.current.warmup();
      }
      await connect();
      await startMic();
      unmuteMic(); // safety: clear any mute left from a broken previous turn
      setIsListening(true);
      setIsActive(true);
      setStatusText("Listening...");
    } catch (err) {
      console.error("Failed to start Spectra:", err);
      setStatusText("Failed to start - check permissions");
      announceAssertive("Failed to start Spectra. Please check microphone permissions.");
      handleFullStop();
    }
  }, [isActive, connect, startMic, unmuteMic, handleFullStop, announceAssertive]);

  const handleStop = useCallback(() => {
    if (!isActive) return;
    stopMic();
    // Keep screen capture alive across Q-restarts — frames only flow when
    // isActive=true so there's no overhead. User shouldn't need to press W again
    // just because they toggled Spectra off and back on.
    audioPlayerRef.current.stop();
    // Reset warmup flag so the AudioContext is re-warmed on next Q press.
    // stop() closes the AudioContext; without this reset, the next session
    // skips warmup → new AudioContext created cold → may be suspended → audio fails.
    audioContextWarmedRef.current = false;
    setIsActive(false);
    setIsListening(false);
    setIsSpeaking(false);
    setStatusText("Press Q or say “Hey Spectra”");
  }, [isActive, stopMic]);

  const handleToggle = useCallback(() => {
    if (isActive) handleStop();
    else handleStart();
  }, [isActive, handleStart, handleStop]);

  const handleShareScreen = useCallback(async () => {
    if (!isActive) await handleStart();
    if (isScreenSharing) {
      stopCapture();
      setIsScreenSharing(false);
    } else {
      try {
        await startCapture();
        setIsScreenSharing(true);
        markScreenShared();
      } catch { /* denied */ }
    }
  }, [isActive, isScreenSharing, handleStart, startCapture, stopCapture, markScreenShared]);

  const handleSendMessage = useCallback((text: string) => {
    if (!text.trim()) return;
    // Warm up AudioContext on this user gesture so Gemini's audio response can play
    if (!audioContextWarmedRef.current) {
      audioContextWarmedRef.current = true;
      audioPlayerRef.current.warmup();
    }
    setMessages((prev) => [...prev, { role: "user" as const, content: text.trim(), timestamp: Date.now() }]);
    if (isConnected) {
      sendText(text.trim());
      setIsThinking(true);
    } else {
      setPendingMessages((prev) => prev + 1);
    }
    if (inputRef.current) inputRef.current.value = "";
  }, [isConnected, sendText]);

  const handleRetryConnection = useCallback(async () => {
    setConnectionState("reconnecting");
    setReconnectAttempt(0);
    await connect();
  }, [connect]);

  // Keyboard shortcuts: use e.code (KeyQ, KeyW) so physical keys work on any keyboard layout
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Q and W are reserved — always handle them, even when focus is in an input
      if (e.code === "KeyQ") {
        e.preventDefault();
        e.stopPropagation();
        handleToggle();
        return;
      }
      if (e.code === "KeyW") {
        e.preventDefault();
        e.stopPropagation();
        handleShareScreen();
        return;
      }
      if (e.key.toLowerCase() === "escape" && isActive) {
        e.preventDefault();
        e.stopPropagation();
        handleStop();
        return;
      }
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
    };
    document.addEventListener("keydown", handleKeyDown, true);
    return () => document.removeEventListener("keydown", handleKeyDown, true);
  }, [isActive, handleToggle, handleShareScreen, handleStop]);

  // Orb state
  const orbState = isSpeaking ? "speaking" : isListening && isActive ? "listening" : "idle";

  return (
    <div
      className="min-h-screen bg-spectra-bg text-spectra-text flex flex-col"
      tabIndex={-1}
      style={{ outline: "none" }}
    >
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="border-b border-white/8 px-4 sm:px-6 py-3 sm:py-4 glass-dark">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-4">
          {/* Logo + tagline */}
          <div className="flex items-center gap-2.5 flex-shrink-0">
            <img src="/icon512.png" alt="" aria-hidden="true" className="w-7 h-7 sm:w-8 sm:h-8" />
            <div>
              <span className="text-lg sm:text-xl font-semibold tracking-tight">Spectra</span>
              <span className="hidden sm:inline text-white/40 text-xs font-normal ml-2">Browse by voice</span>
            </div>
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-2 sm:gap-4">
            {/* Connection dot + label */}
            <div className="flex items-center gap-2 text-sm" aria-label={`Connection: ${connectionState}`}>
              <div
                className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  connectionState === "connected"
                    ? "bg-green-400"
                    : connectionState === "reconnecting"
                    ? "bg-amber-400 animate-pulse"
                    : connectionState === "failed"
                    ? "bg-red-500"
                    : "bg-white/20"
                }`}
              />
              <span className={`text-xs ${
                connectionState === "connected" ? "text-green-400/70"
                : connectionState === "reconnecting" ? "text-amber-400/70"
                : connectionState === "failed" ? "text-red-400/80"
                : "text-white/40"
              }`}>
                {connectionState === "reconnecting"
                  ? `Reconnecting (${reconnectAttempt})…`
                  : connectionState === "failed"
                  ? "Failed"
                  : connectionState === "connected"
                  ? "Connected"
                  : "Disconnected"}
              </span>
              {connectionState === "failed" && (
                <button
                  onClick={handleRetryConnection}
                  className="ml-1 px-2.5 py-1 text-xs bg-spectra-primary hover:bg-spectra-primary/80 rounded-md transition-colors"
                >
                  Retry
                </button>
              )}
            </div>

            {/* Extension status — with install CTA when missing */}
            <div
              className={`flex items-center gap-1.5 text-xs ${extensionReady ? "text-green-400/70" : "text-amber-400/70"}`}
              title={extensionReady ? "Extension active" : "Install Spectra Bridge for click/scroll/type"}
              aria-label={extensionReady ? "Browser extension connected" : "Browser extension not found"}
            >
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${extensionReady ? "bg-green-400" : "bg-amber-400 animate-pulse"}`} />
              {extensionReady ? <span className="hidden sm:inline">Extension</span> : (
                <a
                  href="https://github.com/Aqta-ai/spectra#browser-extension"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-amber-300 underline underline-offset-1"
                >
                  Install extension
                </a>
              )}
            </div>

            <button
              onClick={() => setShowKeyboardShortcuts((v) => !v)}
              className="text-xs text-white/40 hover:text-white/80 transition-colors"
              aria-label="Toggle keyboard shortcuts"
              aria-expanded={showKeyboardShortcuts}
            >
              Shortcuts
            </button>

            <a
              href="/guide"
              className="text-xs text-white/40 hover:text-white/80 transition-colors hidden sm:block"
            >
              Guide
            </a>

            <a
              href="/overlay"
              className="text-xs text-white/40 hover:text-white/80 transition-colors hidden sm:block"
            >
              Overlay
            </a>
          </div>
        </div>

        {/* Shortcuts panel */}
        {showKeyboardShortcuts && (
          <div className="max-w-5xl mx-auto mt-3 p-4 glass rounded-xl border border-white/10 animate-fade-in">
            <p className="text-xs font-medium text-white/50 uppercase tracking-wider mb-3">Keyboard Shortcuts</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              {[
                { key: "Q", label: "Toggle Spectra" },
                { key: "W", label: "Share screen" },
                { key: "Esc", label: "Stop" },
                { key: "Tab", label: "Navigate" },
              ].map(({ key, label }) => (
                <div key={key} className="flex items-center gap-2">
                  <kbd className="px-2 py-1 bg-white/8 rounded text-xs font-mono text-white/70 border border-white/10">{key}</kbd>
                  <span className="text-white/60 text-xs">{label}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </header>

      {/* ── Main ───────────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col items-center px-4 sm:px-6 py-8 sm:py-12 relative">
        {/* Simple, working onboarding - REMOVED */}

        {/* Extension banner when connected but extension missing — dismissible */}
        {!extensionReady && isConnected && showExtensionBanner && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-40 max-w-lg mx-4 flex items-center gap-3 px-4 py-3 rounded-xl bg-amber-500/15 border border-amber-500/30 backdrop-blur-sm" role="status">
            <span className="text-amber-300 text-sm">
              Install the <a href="https://github.com/Aqta-ai/spectra#browser-extension" target="_blank" rel="noopener noreferrer" className="underline font-medium">Spectra Bridge</a> extension to click, type, and navigate with voice.
            </span>
            <button onClick={() => setShowExtensionBanner(false)} className="flex-shrink-0 p-1 rounded hover:bg-amber-500/20 text-amber-200" aria-label="Dismiss">×</button>
          </div>
        )}

        {/* Dot-grid background , only in hero state */}
        {!isActive && messages.length === 0 && (
          <div className="absolute inset-0 hero-mesh pointer-events-none" aria-hidden="true" />
        )}
        {!isActive && messages.length === 0 ? (
          /* ── Idle hero ──────────────────────────────────────────────────── */
          <div className="flex flex-col items-center justify-center flex-1 text-center space-y-7 sm:space-y-9 -mt-8 sm:-mt-12">

            {/* Orb + rings */}
            <div className="relative flex items-center justify-center">
              {/* Outer glow ring , brightens when connected */}
              <div
                className={`absolute rounded-full border transition-all duration-1000 pointer-events-none ${
                  connectionState === "connected" ? "border-spectra-primary/20 opacity-100" : "border-white/5 opacity-60"
                }`}
                style={{ width: "calc(100% + 44px)", height: "calc(100% + 44px)" }}
                aria-hidden="true"
              />
              {/* Inner ring */}
              <div
                className={`absolute rounded-full border-2 transition-all duration-700 pointer-events-none ${
                  connectionState === "connected" ? "border-spectra-primary/30" : "border-white/8"
                }`}
                style={{ width: "calc(100% + 20px)", height: "calc(100% + 20px)" }}
                aria-hidden="true"
              />
              {/* Orb */}
              <button
                onClick={handleToggle}
                className="relative w-32 h-32 sm:w-40 sm:h-40 spectra-orb animate-orb-idle focus:outline-none focus-visible:outline-4 focus-visible:outline-yellow-400"
                aria-label={isActive ? "Stop Spectra" : "Start Spectra"}
              >
                <span className="absolute inset-0 flex items-center justify-center text-white text-4xl sm:text-5xl font-bold select-none" aria-hidden="true">S</span>
              </button>
            </div>

            {/* Copy */}
            <div className="space-y-3">
              <h2 className={`text-2xl sm:text-3xl font-semibold ${
                statusText === "Your screen, your voice, your way"
                  ? "bg-gradient-to-r from-white via-spectra-secondary to-spectra-primary bg-clip-text text-transparent"
                  : "text-white"
              }`}>{statusText}</h2>

              {/* Helpful shortcuts - always visible */}
              {!isActive && messages.length === 0 && (
                <div className="flex flex-wrap justify-center gap-3 text-sm text-white/60">
                  <div className="flex items-center gap-2">
                    <kbd className="px-2 py-1 bg-white/10 rounded border border-white/20 font-mono text-xs">Q</kbd>
                    <span>to connect</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <kbd className="px-2 py-1 bg-white/10 rounded border border-white/20 font-mono text-xs">W</kbd>
                    <span>to share screen</span>
                  </div>
                </div>
              )}
            </div>

            {/* CTA */}
            {connectionState === "connected" ? (
              <button
                onClick={handleStart}
                className="flex items-center gap-2.5 px-10 py-3.5 bg-spectra-primary hover:bg-spectra-primary/85 active:scale-95 text-white font-semibold rounded-xl transition-all text-base shadow-lg shadow-spectra-primary/30"
                aria-label="Start Spectra , tap to begin"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 3a4 4 0 014 4v4a4 4 0 01-8 0V7a4 4 0 014-4z" />
                </svg>
                Start listening
              </button>
            ) : connectionState === "reconnecting" ? (
              <div className="flex items-center gap-2.5 px-10 py-3.5 rounded-xl border border-amber-400/20 bg-amber-400/5 text-amber-400/80 text-base font-semibold" role="status" aria-live="polite">
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                Reconnecting…
              </div>
            ) : (
              <button
                onClick={handleRetryConnection}
                className="flex items-center gap-2.5 px-10 py-3.5 bg-spectra-primary hover:bg-spectra-primary/90 active:scale-95 text-white font-semibold rounded-xl transition-all text-base cta-glow"
                aria-label="Connect to Spectra"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
                </svg>
                Connect
              </button>
            )}

            {/* Feature pills */}
            <div className="flex flex-wrap justify-center gap-2 text-xs text-white/40">
              {[
                { label: "Voice first", icon: <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 3a4 4 0 014 4v4a4 4 0 01-8 0V7a4 4 0 014-4z" /></svg> },
                { label: "Screen aware", icon: <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg> },
                { label: "Hands-free", icon: <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11" /></svg> },
                { label: "Accessibility focused", icon: <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="5" r="1" strokeWidth={2} /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l1-5H7l3-7h4l3 7h-3l1 5" /></svg> },
              ].map(({ label, icon }) => (
                <span key={label} className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-white/10 bg-white/4">
                  {icon}{label}
                </span>
              ))}
            </div>

            {/* Try asking me prompts */}
            <div className="space-y-2 text-center">
              <p className="text-xs text-white/30 uppercase tracking-wider">Try saying</p>
              <div className="flex flex-wrap justify-center gap-2">
                {[
                  "Search for flights to London",
                  "Read this article aloud",
                  "Fill in this form",
                  "Find the cheapest option",
                  "Click the sign in button",
                  "Scroll down and summarise",
                ].map((prompt) => (
                  <span
                    key={prompt}
                    className="px-3 py-1.5 text-xs text-white/50 rounded-full border border-white/10 bg-white/3 cursor-default select-none"
                  >
                    &ldquo;{prompt}&rdquo;
                  </span>
                ))}
              </div>
            </div>

          </div>
        ) : (
          /* ── Active / conversation state ────────────────────────────────── */
          <div className="w-full max-w-3xl flex flex-col gap-4">

            {/* ── Orb + status row ──────────────────────────────────────────── */}
            <div className="flex items-center gap-5 p-4 sm:p-5 glass-dark rounded-2xl border border-white/8">
              {/* Mini orb */}
              <button
                onClick={handleToggle}
                className={`relative flex-shrink-0 w-14 h-14 sm:w-16 sm:h-16 spectra-orb
                  ${orbState === "listening" ? "spectra-orb-listening animate-orb-listen" : ""}
                  ${orbState === "speaking"  ? "spectra-orb-speaking animate-orb-speak"  : ""}
                  ${orbState === "idle"      ? "animate-orb-idle"                        : ""}
                  focus:outline-none focus-visible:outline-4 focus-visible:outline-yellow-400`}
                aria-label={isActive ? "Stop Spectra (Q)" : "Start Spectra (Q)"}
              >
                <span className="absolute inset-0 flex items-center justify-center text-white text-xl font-bold select-none" aria-hidden="true">S</span>
              </button>

              {/* Waveform , visible only when listening */}
              {orbState === "listening" && (
                <div className="flex items-center gap-0.5 h-8" aria-hidden="true">
                  {["wave-1","wave-2","wave-3","wave-4","wave-5"].map((cls) => (
                    <div key={cls} className={`waveform-bar h-full text-green-400 animate-${cls}`} />
                  ))}
                </div>
              )}

              {/* Status text + indicators */}
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm sm:text-base truncate">{statusText}</p>
                <div className="flex items-center gap-3 mt-1">
                  {/* Mic */}
                  <span className={`flex items-center gap-1.5 text-xs ${isListening ? "text-green-400" : "text-white/30"}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${isListening ? "bg-green-400 animate-pulse" : "bg-white/20"}`} />
                    Mic
                  </span>
                  {/* Screen */}
                  <span className={`flex items-center gap-1.5 text-xs ${isScreenSharing ? "text-green-400" : "text-white/30"}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${isScreenSharing ? "bg-green-400 animate-pulse" : "bg-white/20"}`} />
                    Screen
                  </span>
                  {/* Connection */}
                  <span className={`flex items-center gap-1.5 text-xs ${isConnected ? "text-green-400" : "text-amber-400"}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-green-400" : "bg-amber-400 animate-pulse"}`} />
                    {isConnected ? "Online" : "Offline"}
                  </span>
                </div>
              </div>

              {/* Controls */}
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={handleShareScreen}
                  className={`p-2 rounded-lg text-xs transition-all border ${
                    isScreenSharing
                      ? "bg-green-500/20 border-green-500/40 text-green-300"
                      : "bg-white/5 border-white/10 text-white/50 hover:text-white/80"
                  }`}
                  aria-label={isScreenSharing ? "Stop screen share (W)" : "Share screen (W)"}
                  title={isScreenSharing ? "Stop sharing (W)" : "Share screen (W)"}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </button>
                <button
                  onClick={handleFullStop}
                  className="px-3 py-2 bg-red-600/80 hover:bg-red-600 rounded-lg transition-all text-xs font-medium text-white border border-red-500/30"
                  aria-label="End session"
                >
                  End
                </button>
              </div>
            </div>

            {/* ── Messages ─────────────────────────────────────────────────── */}
            <div
              className="relative space-y-3 min-h-[360px] sm:min-h-[420px] max-h-[520px] overflow-y-auto p-4 sm:p-6 glass-dark rounded-2xl border border-white/8 scroll-smooth"
              role="log"
              aria-label="Conversation with Spectra"
              aria-live="off"
            >
              {/* Empty state */}
              {messages.length === 0 && !currentTranscript && !currentResponse && !isThinking && (
                <div className="flex flex-col items-center justify-center h-full text-center py-10 animate-fade-in">
                  <div className="w-12 h-12 mb-4 rounded-full bg-spectra-primary/10 border border-spectra-primary/20 flex items-center justify-center">
                    <svg className="w-6 h-6 text-spectra-primary/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                  </div>
                  <p className="text-white/40 text-sm">Speak or type to start the conversation</p>
                </div>
              )}

              {/* Message bubbles */}
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex items-end gap-2.5 animate-slide-up ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
                >
                  {/* Avatar */}
                  <div
                    className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${
                      msg.role === "user"
                        ? "bg-spectra-primary text-white"
                        : "spectra-orb w-7 h-7 text-white text-xs font-bold"
                    }`}
                    aria-hidden="true"
                  >
                    {msg.role === "user" ? "You" : "S"}
                  </div>

                  {/* Bubble */}
                  <div className={`max-w-[78%] sm:max-w-[72%] ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col gap-1`}>
                    <div
                      className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                        msg.role === "user"
                          ? "bg-spectra-primary text-white rounded-br-sm"
                          : "bg-white/6 text-white border border-white/8 rounded-bl-sm"
                      }`}
                    >
                      <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                    </div>
                    <span className="text-xs text-white/40 px-1">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                </div>
              ))}

              {/* Live transcript (user speaking) */}
              {currentTranscript && (
                <div className="flex items-end gap-2.5 flex-row-reverse animate-slide-up">
                  <div className="flex-shrink-0 w-7 h-7 rounded-full bg-spectra-primary/50 flex items-center justify-center text-xs font-semibold text-white" aria-hidden="true">
                    You
                  </div>
                  <div className="max-w-[78%] sm:max-w-[72%] items-end flex flex-col gap-1">
                    <div className="px-4 py-3 rounded-2xl rounded-br-sm bg-spectra-primary/30 text-white border border-spectra-primary/20 text-sm">
                      <p className="italic whitespace-pre-wrap break-words">{currentTranscript}</p>
                    </div>
                    <span className="text-xs text-white/40 px-1">Speaking…</span>
                  </div>
                </div>
              )}

              {/* Streaming response */}
              {currentResponse && (
                <div className="flex items-end gap-2.5 flex-row animate-slide-up">
                  <div className="flex-shrink-0 w-7 h-7 rounded-full spectra-orb text-white text-xs font-bold flex items-center justify-center" aria-hidden="true">S</div>
                  <div className="max-w-[78%] sm:max-w-[72%] items-start flex flex-col gap-1">
                    <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-white/6 text-white border border-white/8 text-sm">
                      <p className="whitespace-pre-wrap break-words">
                        {currentResponse}
                        <span className="inline-block w-0.5 h-4 bg-spectra-primary/70 ml-1 animate-pulse align-middle" />
                      </p>
                    </div>
                    <span className="text-xs text-white/40 px-1">Typing…</span>
                  </div>
                </div>
              )}

              {/* Thinking dots */}
              {isThinking && !currentResponse && (
                <div className="flex items-end gap-2.5 flex-row animate-slide-up">
                  <div className="flex-shrink-0 w-7 h-7 rounded-full spectra-orb text-white text-xs font-bold flex items-center justify-center" aria-hidden="true">S</div>
                  <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-white/6 border border-white/8">
                    <div className="flex items-center gap-1.5" aria-label="Spectra is thinking">
                      <div className="w-2 h-2 bg-spectra-primary/70 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <div className="w-2 h-2 bg-spectra-primary/70 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <div className="w-2 h-2 bg-spectra-primary/70 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                  </div>
                </div>
              )}

              {/* Pending messages */}
              {pendingMessages > 0 && (
                <div className="flex justify-center">
                  <div className="px-4 py-2 bg-amber-500/10 border border-amber-500/20 rounded-full text-xs text-amber-400 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse" />
                    {pendingMessages} message{pendingMessages > 1 ? "s" : ""} queued, waiting for connection
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* ── Text input ───────────────────────────────────────────────── */}
            <div className="relative">
              <div className={`flex gap-2 p-2 glass-dark rounded-xl border transition-colors duration-200 ${
                isConnected ? "border-white/10 focus-within:border-spectra-primary/40" : "border-red-500/20"
              }`}>
                <input
                  ref={inputRef}
                  type="text"
                  placeholder={isConnected ? "Type a message…" : "Disconnected, press Q to reconnect"}
                  className="flex-1 px-3 py-2.5 bg-transparent border-none focus:outline-none text-white placeholder-white/30 text-sm"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey && inputRef.current) {
                      e.preventDefault();
                      handleSendMessage(inputRef.current.value);
                    }
                  }}
                  aria-label="Message to Spectra"
                />
                <button
                  onClick={() => inputRef.current && handleSendMessage(inputRef.current.value)}
                  className="flex-shrink-0 px-3 py-2.5 bg-spectra-primary hover:bg-spectra-primary/80 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-all text-white"
                  disabled={!isConnected}
                  aria-label="Send message"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Shortcuts hint */}
            <p className="text-center text-xs text-white/25">
              <kbd className="font-mono">Q</kbd> toggle · <kbd className="font-mono">W</kbd> screen · <kbd className="font-mono">Esc</kbd> stop
            </p>
          </div>
        )}
      </main>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer className="px-4 sm:px-6 py-4 text-center text-xs text-white/30">
        Spectra
        {" · "}
        <a href="/guide" className="hover:text-white/50 transition-colors">Guide</a>
        {" · "}
        <a href="/privacy" className="hover:text-white/50 transition-colors">Privacy</a>
        {" · "}
        <a href="/overlay" className="hover:text-white/50 transition-colors">Overlay</a>
        {" · "}
        <a href="https://github.com/Aqta-ai/spectra" target="_blank" rel="noopener noreferrer" className="hover:text-white/50 transition-colors">GitHub</a>
        {" · Apache 2.0"}
      </footer>

      {/*
       * ACCESSIBILITY: Two ARIA live regions.
       * assertive , urgent events (connect/disconnect/errors).
       * polite , Spectra's replies and action status.
       * Visually hidden , AT users who run a screen reader alongside Spectra.
       */}
      <div className="sr-only" role="alert" aria-live="assertive" aria-atomic="true" aria-label="Spectra urgent announcements">
        {assertiveAnnouncement}
      </div>
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="false" aria-label="Spectra status and responses">
        {politeAnnouncement}
      </div>
      <div className="sr-only" aria-label="Keyboard shortcuts">
        <p>Press Q to {isActive ? "stop" : "start"} Spectra.</p>
        <p>Press W to share your screen.</p>
        <p>Press Escape to stop Spectra.</p>
        <p>Connection: {connectionState}.</p>
      </div>
    </div>
  );
}
