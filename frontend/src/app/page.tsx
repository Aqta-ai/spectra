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

interface SystemInfo {
  provider: string;
  offline_mode: boolean;
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
  const [provider, setProvider] = useState<string>("gemini");
  const [offlineMode, setOfflineMode] = useState(false);

  // Typing effect for demo commands
  const DEMO_COMMANDS = [
    "Go to BBC News and read me the top headline",
    "Search for flights to London under €100",
    "Fill in this form with my details",
    "Click the sign in button",
    "Scroll down and summarise this article",
    "Find the cheapest option and book it",
  ];
  const [typedText, setTypedText] = useState("");
  const [cmdIndex, setCmdIndex] = useState(0);
  const [isTyping, setIsTypingEffect] = useState(true);

  useEffect(() => {
    if (isActive) return; // Don't run when Spectra is active
    const cmd = DEMO_COMMANDS[cmdIndex];
    let charIndex = 0;
    let timeout: ReturnType<typeof setTimeout>;

    if (isTyping) {
      const typeChar = () => {
        if (charIndex <= cmd.length) {
          setTypedText(cmd.slice(0, charIndex));
          charIndex++;
          timeout = setTimeout(typeChar, 45 + Math.random() * 30);
        } else {
          timeout = setTimeout(() => setIsTypingEffect(false), 2000);
        }
      };
      typeChar();
    } else {
      // Erase
      let eraseIndex = cmd.length;
      const eraseChar = () => {
        if (eraseIndex >= 0) {
          setTypedText(cmd.slice(0, eraseIndex));
          eraseIndex--;
          timeout = setTimeout(eraseChar, 20);
        } else {
          setCmdIndex((prev) => (prev + 1) % DEMO_COMMANDS.length);
          setIsTypingEffect(true);
        }
      };
      eraseChar();
    }

    return () => clearTimeout(timeout);
  }, [cmdIndex, isTyping, isActive]);

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

  const speakText = useCallback((text: string) => {
    if (!offlineMode || !text.trim()) return;

    try {
      // Cancel any pending speech
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);

      // Try to find a natural-sounding voice
      const voices = window.speechSynthesis.getVoices();
      if (voices.length > 0) {
        // Prefer Google or high-quality voices; macOS has better voices than Linux
        const preferredVoice = voices.find(v =>
          v.name.includes('Google') ||
          v.lang.startsWith('en-US') ||
          v.name.includes('Samantha') ||  // macOS
          v.name.includes('Victoria')     // macOS/Windows
        ) || voices[0];
        utterance.voice = preferredVoice;
      }

      // Natural speech parameters (slightly slower, higher pitch for clarity)
      utterance.rate = 0.95;   // Slightly slower for clarity
      utterance.pitch = 1.1;   // Slightly higher for presence
      utterance.volume = 1.0;

      utterance.onstart = () => {
        setIsSpeaking(true);
      };

      utterance.onend = () => {
        setIsSpeaking(false);
      };

      utterance.onerror = () => {
        setIsSpeaking(false);
      };

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.error('[Spectra] TTS error:', err);
    }
  }, [offlineMode]);

  // Fetch provider info from backend
  useEffect(() => {
    const fetchProvider = async () => {
      try {
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
        const res = await fetch(`${backendUrl}/api/system-info`);
        if (res.ok) {
          const info: SystemInfo = await res.json();
          setProvider(info.provider || 'gemini');
          setOfflineMode(info.offline_mode ?? false);
        }
      } catch (err) {
        console.debug('Could not fetch provider info:', err);
      }
    };
    fetchProvider();
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
      if (cleaned) {
        setCurrentResponse((prev) => prev + cleaned);
        if (offlineMode) {
          speakText(cleaned);
        }
      }
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
      setStatusText("Connection ended");
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
    onStop: () => setIsScreenSharing(false),
    fps: 3,
  });

  // Wake word detection for "Hey Spectra"
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

      // Gemini Live mode: use PCM audio stream
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
    // Offline mode doesn't support screen sharing (text-only)
    if (offlineMode) {
      announcePolite("Screen sharing is not available in offline mode");
      return;
    }

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
  }, [isActive, isScreenSharing, offlineMode, handleStart, startCapture, stopCapture, markScreenShared, announcePolite]);

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
      // In offline mode (text-only), don't intercept W in text inputs
      const isTextInput = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;

      // Q and W are reserved — but never hijack them when the user is typing
      if (e.code === "KeyQ" && !isTextInput) {
        e.preventDefault();
        e.stopPropagation();
        handleToggle();
        return;
      }
      if (e.code === "KeyW" && !offlineMode && !isTextInput) {
        // W hotkey only works in Cloud (Gemini) mode, not offline text mode
        e.preventDefault();
        e.stopPropagation();
        handleShareScreen();
        return;
      }
      if (e.code === "Escape" && isActive) {
        e.preventDefault();
        e.stopPropagation();
        handleStop();
        return;
      }
      if (isTextInput) return;
    };
    document.addEventListener("keydown", handleKeyDown, true);
    return () => document.removeEventListener("keydown", handleKeyDown, true);
  }, [isActive, offlineMode, handleToggle, handleShareScreen, handleStop]);

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
              <span className="hidden sm:inline text-white/60 text-xs font-normal ml-2">Browse by voice</span>
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
                : "text-white/60"
              }`}>
                {connectionState === "reconnecting"
                  ? `Reconnecting (${reconnectAttempt})…`
                  : connectionState === "failed"
                  ? "Failed"
                  : connectionState === "connected"
                  ? "Connected"
                  : "Ready"}
              </span>
              {connectionState === "failed" && (
                <button
                  onClick={handleRetryConnection}
                  className="ml-1 px-2.5 py-1 text-xs bg-spectra-primary hover:bg-white/20 rounded-md transition-colors"
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
                  href="https://chromewebstore.google.com/detail/spectra/ocaghbifpjeaaomknnbmckdemhdllnhg"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-amber-300 underline underline-offset-1"
                >
                  Install extension
                </a>
              )}
            </div>

            {/* Provider toggle - Clean line icon button */}
            <button
              onClick={async () => {
                const newProvider = provider === 'gemini' ? 'ollama' : 'gemini';
                try {
                  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
                  const res = await fetch(`${backendUrl}/api/switch-provider`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ new_provider: newProvider }),
                  });
                  if (res.ok) {
                    setStatusText('Switching...');
                    setTimeout(() => window.location.reload(), 800);
                  } else {
                    setStatusText('Failed to switch');
                  }
                } catch (e) {
                  console.error(e);
                }
              }}
              className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded transition-all cursor-pointer ${
                provider === 'gemini'
                  ? 'bg-white/10 text-white/80 hover:bg-white/15'
                  : 'bg-white/10 text-white/80 hover:bg-white/15'
              }`}
              title={`Click to switch to ${provider === 'gemini' ? 'Local' : 'Cloud'}`}
            >
              <span className="font-medium text-xs">
                {provider === 'gemini' ? 'Cloud' : 'Local'}
              </span>
            </button>

            <a
              href="#features"
              className="text-xs text-white/60 hover:text-white/80 transition-colors hidden sm:block"
            >
              Features
            </a>

            <a
              href="#how-it-works"
              className="text-xs text-white/60 hover:text-white/80 transition-colors hidden sm:block"
            >
              How it works
            </a>

            <a
              href="/overlay"
              className="text-xs text-white/60 hover:text-white/80 transition-colors hidden sm:block"
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
        {/* Onboarding guide for first-time users */}
        {shouldShowOnboarding && (
          <OnboardingGuide
            isFirstTime={isFirstTime}
            hasSharedScreen={hasSharedScreen}
            isConnected={isConnected}
            onConnect={handleStart}
            onDismiss={dismissOnboarding}
            onComplete={markOnboardingComplete}
          />
        )}

        {/* Extension banner when connected but extension missing — dismissible */}
        {!extensionReady && isConnected && showExtensionBanner && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-40 max-w-lg mx-4 flex items-center gap-3 px-4 py-3 rounded-xl bg-amber-500/15 border border-amber-500/30 backdrop-blur-sm" role="status">
            <span className="text-amber-300 text-sm">
              Install the <a href="https://chromewebstore.google.com/detail/spectra/ocaghbifpjeaaomknnbmckdemhdllnhg" target="_blank" rel="noopener noreferrer" className="underline font-medium">Spectra Bridge</a> extension to click, type, and navigate with voice.
            </span>
            <button onClick={() => setShowExtensionBanner(false)} className="flex-shrink-0 p-1 rounded hover:bg-amber-500/20 text-amber-200" aria-label="Dismiss">×</button>
          </div>
        )}

        {/* Floating glow orbs — ambient background */}
        {!isActive && messages.length === 0 && (
          <>
            <div className="absolute inset-0 hero-mesh pointer-events-none" aria-hidden="true" />
            <div className="absolute top-20 left-[15%] w-72 h-72 bg-spectra-primary/5 rounded-full blur-3xl float-slow pointer-events-none" aria-hidden="true" />
            <div className="absolute bottom-32 right-[10%] w-96 h-96 bg-spectra-secondary/5 rounded-full blur-3xl float-slower pointer-events-none" aria-hidden="true" />
          </>
        )}
        {!isActive && messages.length === 0 ? (
          /* ── Full Landing Page ────────────────────────────────────────── */
          <div className="flex flex-col items-center w-full max-w-5xl mx-auto space-y-16 sm:space-y-24 pb-12">

            {/* ═══ HERO SECTION ═══════════════════════════════════════════ */}
            <div className="flex flex-col items-center text-center space-y-8 pt-4 sm:pt-8 stagger-1">
              {/* Orb + rings */}
              <div className="relative flex items-center justify-center">
                <div
                  className={`absolute rounded-full border transition-all duration-1000 pointer-events-none ${
                    connectionState === "connected" ? "border-spectra-primary/20 opacity-100" : "border-white/5 opacity-60"
                  }`}
                  style={{ width: "calc(100% + 44px)", height: "calc(100% + 44px)" }}
                  aria-hidden="true"
                />
                <div
                  className={`absolute rounded-full border-2 transition-all duration-700 pointer-events-none ${
                    connectionState === "connected" ? "border-spectra-primary/30" : "border-white/8"
                  }`}
                  style={{ width: "calc(100% + 20px)", height: "calc(100% + 20px)" }}
                  aria-hidden="true"
                />
                <button
                  onClick={handleToggle}
                  className="relative w-28 h-28 sm:w-36 sm:h-36 spectra-orb animate-orb-idle focus:outline-none focus-visible:outline-4 focus-visible:outline-yellow-400"
                  aria-label={isActive ? "Stop Spectra" : "Start Spectra"}
                >
                  <span className="absolute inset-0 flex items-center justify-center text-white/90 drop-shadow-lg" aria-hidden="true">
                    <svg className="w-10 h-10 sm:w-14 sm:h-14" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                    </svg>
                  </span>
                </button>
              </div>

              {/* Headline + sub */}
              <div className="space-y-4">
                <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-tight">
                  <span className="bg-gradient-to-r from-white via-spectra-primary to-spectra-secondary bg-clip-text text-transparent text-shimmer">
                    Your screen, your voice,
                  </span>
                  <br />
                  <span className="text-white">your way.</span>
                </h1>
                <p className="text-base sm:text-lg text-white max-w-2xl mx-auto leading-relaxed">
                  Spectra is an AI agent that sees your screen, listens to your voice, and takes action, <em>click, type, navigate, read</em>, entirely hands-free. Built for accessibility. Designed for everyone.
                </p>
              </div>

              {/* Animated typing demo */}
              <div className="w-full max-w-xl mx-auto">
                <div className="glass rounded-2xl border border-white/10 px-6 py-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                    <span className="text-xs text-white/60 uppercase tracking-wider">Listening</span>
                  </div>
                  <p className="text-left text-base sm:text-lg text-white font-medium min-h-[28px]">
                    &ldquo;{typedText}<span className="inline-block w-0.5 h-5 bg-spectra-primary ml-0.5 align-middle animate-blink" />&rdquo;
                  </p>
                </div>
              </div>

              {/* CTA buttons */}
              <div className="flex flex-col sm:flex-row items-center gap-3">
                {connectionState === "connected" ? (
                  <button
                    onClick={handleStart}
                    className="flex items-center gap-2.5 px-10 py-3.5 bg-[#6C5CE7] hover:bg-[#5a4cd0] active:scale-95 text-white font-semibold rounded-xl transition-all text-base shadow-lg shadow-[#6C5CE7]/30"
                    aria-label="Start Spectra"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 3a4 4 0 014 4v4a4 4 0 01-8 0V7a4 4 0 014-4z" />
                    </svg>
                    Start listening
                  </button>
                ) : connectionState === "reconnecting" ? (
                  <div className="flex items-center gap-2.5 px-10 py-3.5 rounded-xl border border-amber-400/20 bg-amber-400/5 text-amber-400/80 text-base font-semibold" role="status">
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                    </svg>
                    Reconnecting…
                  </div>
                ) : (
                  <button
                    onClick={handleRetryConnection}
                    disabled={!extensionReady}
                    className={`flex items-center gap-2.5 px-10 py-3.5 font-semibold rounded-xl transition-all text-base ${
                      extensionReady
                        ? "bg-[#6C5CE7] hover:bg-[#5a4cd0] active:scale-95 cta-glow cursor-pointer"
                        : "bg-white/10 cursor-not-allowed opacity-50"
                    } text-white`}
                    aria-label={extensionReady ? "Start Spectra" : "Install extension first"}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
                    </svg>
                    Start Spectra
                  </button>
                )}
                <a
                  href="https://www.youtube.com/watch?v=MJQX4xapRA0"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-6 py-3.5 rounded-xl border border-white/10 text-white/70 hover:text-white hover:border-white/20 transition-all text-sm font-medium"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                  Watch demo
                </a>
              </div>

              {/* Keyboard hints */}
              <div className="flex flex-wrap justify-center gap-4 text-sm text-white/60">
                <div className="flex items-center gap-2">
                  <kbd className="px-2 py-1 bg-white/8 rounded border border-white/15 font-mono text-xs">Q</kbd>
                  <span>to connect</span>
                </div>
                <div className="flex items-center gap-2">
                  <kbd className="px-2 py-1 bg-white/8 rounded border border-white/15 font-mono text-xs">W</kbd>
                  <span>to share screen</span>
                </div>
                {!extensionReady && (
                  <a
                    href="https://chromewebstore.google.com/detail/spectra/ocaghbifpjeaaomknnbmckdemhdllnhg"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-spectra-primary/70 hover:text-white underline underline-offset-2 text-xs"
                  >
                    Install Chrome extension
                  </a>
                )}
              </div>
            </div>

            {/* ═══ STATS BAR ══════════════════════════════════════════════ */}
            <div className="w-full stagger-2">
              <div className="glass rounded-2xl border border-white/8 px-6 py-6">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
                  {[
                    { value: "99.2%", label: "Test pass rate", sub: "442 tests" },
                    { value: "<1s", label: "Voice response", sub: "Real-time streaming" },
                    { value: "97", label: "Languages", sub: "Gemini Live native audio" },
                    { value: "Zero", label: "Data stored", sub: "Privacy by design", showLock: true },
                  ].map(({ value, label, sub, showLock }) => (
                    <div key={label} className="space-y-1">
                      <div className="flex items-center justify-center gap-2">
                        <p className="text-2xl sm:text-3xl font-bold text-spectra-secondary">{value}</p>
                        {showLock && <svg className="w-6 h-6 text-spectra-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>}
                      </div>
                      <p className="text-sm text-white font-medium">{label}</p>
                      <p className="text-xs text-white/60">{sub}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* ═══ VIDEO DEMO ═════════════════════════════════════════════ */}
            <div className="w-full stagger-3">
              <div className="text-center mb-6">
                <h2 className="text-xl sm:text-2xl font-bold text-white">See Spectra in action</h2>
                <p className="text-sm text-white/50 mt-1">A blind user browses BBC News, entirely by voice</p>
              </div>
              <div className="relative rounded-2xl overflow-hidden video-glow">
                <div className="aspect-video bg-spectra-dark">
                  <iframe
                    className="w-full h-full"
                    src="https://www.youtube.com/embed/MJQX4xapRA0?rel=0&modestbranding=1"
                    title="Spectra demo, voice-controlled browser for accessibility"
                    frameBorder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                </div>
              </div>
            </div>

            {/* ═══ WHO IT'S FOR ═══════════════════════════════════════════ */}
            <div className="w-full stagger-4">
              <div id="features" className="text-center mb-8">
                <h2 className="text-xl sm:text-2xl font-bold text-white">Built for people, not just browsers</h2>
                <p className="text-sm text-white/50 mt-1">
                  2.2 billion people worldwide live with a vision impairment
                  <a href="https://www.who.int/news-room/fact-sheets/detail/blindness-and-visual-impairment" target="_blank" rel="noopener noreferrer" className="text-white/40 hover:text-white/70 underline underline-offset-2 ml-1"><sup>WHO</sup></a>.
                  Spectra closes the gap.
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  {
                    icon: <svg className="w-8 h-8 text-white/80" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>,
                    title: "Blind & low-vision users",
                    desc: "Navigate any website by voice. No more rigid screen readers that break on modern UIs.",
                    stat: "43M blind people worldwide",
                  },
                  {
                    icon: <svg className="w-8 h-8 text-white/80" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11" /></svg>,
                    title: "Hands-free workers",
                    desc: "Surgeons, mechanics, cooks, anyone whose hands are busy but needs their browser.",
                    stat: "100% keyboard + voice control",
                  },
                  {
                    icon: <svg className="w-8 h-8 text-white/80" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
                    title: "Accessibility teams",
                    desc: "See your site through Spectra's eyes. Reveal what AI sees, and what's fundamentally broken.",
                    stat: "96% of top 1M sites fail WCAG",
                  },
                ].map(({ icon, title, desc, stat }) => (
                  <div
                    key={title}
                    className="persona-card glass rounded-2xl border border-white/8 p-6 text-left space-y-3"
                  >
                    <div aria-hidden="true">{icon}</div>
                    <h3 className="text-base font-semibold text-white">{title}</h3>
                    <p className="text-sm text-white/70 leading-relaxed">{desc}</p>
                    <p className="text-xs text-spectra-primary font-medium">{stat}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* ═══ HOW IT WORKS ═══════════════════════════════════════════ */}
            <div id="how-it-works" className="w-full stagger-5">
              <div className="text-center mb-8">
                <h2 className="text-xl sm:text-2xl font-bold text-white">How it works</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                {[
                  { step: "1", title: "Press Q", desc: "Connect to Spectra instantly", icon: <svg className="w-6 h-6 mx-auto text-white/70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg> },
                  { step: "2", title: "Press W", desc: "Share your browser tab", icon: <svg className="w-6 h-6 mx-auto text-white/70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg> },
                  { step: "3", title: "Speak", desc: "Say what you want, in any language", icon: <svg className="w-6 h-6 mx-auto text-white/70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 3a4 4 0 014 4v4a4 4 0 01-8 0V7a4 4 0 014-4z" /></svg> },
                  { step: "4", title: "Watch", desc: "Spectra clicks, types, and reads", icon: <svg className="w-6 h-6 mx-auto text-white/70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 13l4 4L19 7" /></svg> },
                ].map(({ step, title, desc, icon }) => (
                  <div key={step} className="relative glass rounded-2xl border border-white/8 p-5 text-center space-y-2">
                    <div aria-hidden="true">{icon}</div>
                    <div className="text-xs text-spectra-primary font-bold uppercase tracking-widest pt-1">Step {step}</div>
                    <h3 className="text-sm font-semibold text-white">{title}</h3>
                    <p className="text-xs text-white/70 leading-relaxed">{desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* ═══ OPEN SOURCE + OFFLINE ══════════════════════════════════ */}
            <div className="w-full stagger-6">
              <div className="glass rounded-2xl border border-white/8 p-8 sm:p-10">
                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
                  <div className="flex-1 space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-green-400 oss-pulse" />
                      <span className="text-xs text-green-400 font-semibold uppercase tracking-wider">Open Source · Apache 2.0</span>
                    </div>
                    <h2 className="text-xl sm:text-2xl font-bold text-white">Fully open. Runs offline.</h2>
                    <p className="text-sm text-white/80 leading-relaxed max-w-xl">
                      Spectra is 100% open source. With <span className="text-spectra-primary font-medium">Gemma offline mode</span>,
                      run the entire stack on your own hardware, no API keys, no cloud, no data leaving your machine.
                      Perfect for hospitals, schools, and regulated industries.
                    </p>
                    <div className="flex flex-wrap items-center gap-3 pt-2">
                      <a
                        href="https://github.com/Aqta-ai/spectra"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/8 hover:bg-white/12 border border-white/10 text-sm text-white hover:text-white/90 transition-all"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" /></svg>
                        View on GitHub
                      </a>
                      <span className="flex items-center gap-1.5 text-xs text-white/60">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                        ~8,500 lines of code
                      </span>
                      <span className="flex items-center gap-1.5 text-xs text-white/60">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        442 tests
                      </span>
                    </div>
                  </div>
                  {/* Offline mode badge */}
                  <div className="flex-shrink-0 glass rounded-xl border border-spectra-primary/20 p-5 text-center space-y-2 min-w-[160px]">
                    <div className="flex justify-center" aria-hidden="true">
                      <svg className="w-8 h-8 text-spectra-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                    </div>
                    <p className="text-sm font-semibold text-white pt-1">Offline mode</p>
                    <p className="text-xs text-white/50">Gemma 3 + Ollama</p>
                    <p className="text-xs text-white/35">No API key needed</p>
                  </div>
                </div>
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
                <span className="absolute inset-0 flex items-center justify-center text-white/90 drop-shadow-sm" aria-hidden="true">
                  <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                  </svg>
                </span>
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
                  <span className={`flex items-center gap-1.5 text-xs ${isListening ? "text-green-400" : "text-white/50"}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${isListening ? "bg-green-400 animate-pulse" : "bg-white/20"}`} />
                    Mic
                  </span>
                  {/* Screen */}
                  <span className={`flex items-center gap-1.5 text-xs ${isScreenSharing ? "text-green-400" : "text-white/50"}`}>
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
                  disabled={offlineMode}
                  className={`p-2 rounded-lg text-xs transition-all border ${
                    offlineMode
                      ? "opacity-40 cursor-not-allowed bg-white/5 border-white/10 text-white/30"
                      : isScreenSharing
                      ? "bg-green-500/20 border-green-500/40 text-green-300 hover:bg-green-500/30"
                      : "bg-white/5 border-white/10 text-white/50 hover:text-white/80 hover:bg-white/10"
                  }`}
                  aria-label={offlineMode ? "Screen share unavailable (offline mode text-only)" : (isScreenSharing ? "Stop screen share (W)" : "Share screen (W)")}
                  title={offlineMode ? "Screen share unavailable in offline mode (text-only)" : (isScreenSharing ? "Stop sharing (W)" : "Share screen (W)")}
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
                  <p className="text-white/60 text-sm">Speak or type to start the conversation</p>
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
                    {msg.role === "user" ? "You" : (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                      </svg>
                    )}
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
                    <span className="text-xs text-white/60 px-1">
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
                    <span className="text-xs text-white/60 px-1">Speaking…</span>
                  </div>
                </div>
              )}

              {/* Streaming response */}
              {currentResponse && (
                <div className="flex items-end gap-2.5 flex-row animate-slide-up">
                  <div className="flex-shrink-0 w-7 h-7 rounded-full spectra-orb text-white text-xs font-bold flex items-center justify-center" aria-hidden="true">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                    </svg>
                  </div>
                  <div className="max-w-[78%] sm:max-w-[72%] items-start flex flex-col gap-1">
                    <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-white/6 text-white border border-white/8 text-sm">
                      <p className="whitespace-pre-wrap break-words">
                        {currentResponse}
                        <span className="inline-block w-0.5 h-4 bg-spectra-primary/70 ml-1 animate-pulse align-middle" />
                      </p>
                    </div>
                    <span className="text-xs text-white/60 px-1">Typing…</span>
                  </div>
                </div>
              )}

              {/* Thinking dots */}
              {isThinking && !currentResponse && (
                <div className="flex items-end gap-2.5 flex-row animate-slide-up">
                  <div className="flex-shrink-0 w-7 h-7 rounded-full spectra-orb text-white text-xs font-bold flex items-center justify-center" aria-hidden="true">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                    </svg>
                  </div>
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
                    Not connected — message not sent
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
                  placeholder={isConnected ? "Type a message…" : "Press Q to connect"}
                  className="flex-1 px-3 py-2.5 bg-transparent border-none focus:outline-none text-white placeholder-white/30 text-sm"
                  disabled={!isConnected}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey && inputRef.current) {
                      e.preventDefault();
                      const text = inputRef.current.value.trim();
                      if (text && isConnected) {
                        sendText(text);
                        inputRef.current.value = "";
                      }
                      handleSendMessage(inputRef.current.value);
                    }
                  }}
                  aria-label="Message to Spectra"
                />
                <button
                  onClick={() => inputRef.current && handleSendMessage(inputRef.current.value)}
                  className="flex-shrink-0 px-3 py-2.5 bg-spectra-primary hover:bg-white/20 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-all text-white"
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
      <footer className="px-4 sm:px-6 py-8 border-t border-white/5">
        <div className="max-w-5xl mx-auto space-y-6">
          {/* Feature capsules */}
          <div className="flex flex-wrap justify-center gap-3 text-xs">
            {[
              "Voice first", "Screen vision", "Hands-free",
              "Wake word", "Barge-in", "Zero data stored", "WCAG 2.1 AA",
              "Open source", "Offline capable",
            ].map((label) => (
              <span key={label} className="px-3 py-1.5 rounded-full border border-white/12 bg-white/5 text-white/50 hover:text-white/80 hover:border-white/20 transition-colors">
                {label}
              </span>
            ))}
          </div>
          {/* Links row */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-white/50">
            <div className="flex items-center gap-1.5">
              <img src="/icon512.png" alt="" aria-hidden="true" className="w-4 h-4 opacity-40" />
              <span>Spectra · Apache 2.0</span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <a href="/guide" className="hover:text-white/50 transition-colors">Guide</a>
              <a href="/privacy" className="hover:text-white/50 transition-colors">Privacy</a>
              <a href="/overlay" className="hover:text-white/50 transition-colors">Overlay</a>
              <a href="https://github.com/Aqta-ai/spectra" target="_blank" rel="noopener noreferrer" className="hover:text-white/50 transition-colors">GitHub</a>
            </div>
            <span className="text-white/60">Built by <a href="https://github.com/Aqta-ai" target="_blank" rel="noopener noreferrer" className="text-white hover:text-white/80 transition-colors font-medium">Aqta</a></span>
          </div>
        </div>
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
