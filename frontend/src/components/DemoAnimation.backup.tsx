"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import {
  Mic,
  Eye,
  Globe,
  Accessibility,
  Star,
  ChevronLeft,
  ChevronRight,
  Play,
  Pause,
  RotateCcw,
} from "lucide-react";

interface DemoAnimationProps {
  autoStart?: boolean;
  showControls?: boolean;
  onComplete?: () => void;
}

const SCENES = ["logo", "features", "commands", "cta"] as const;
const TOTAL_DURATION = 60;
const SCENE_DURATION = TOTAL_DURATION / SCENES.length;

export default function DemoAnimation({
  autoStart = true,
  showControls = false,
  onComplete,
}: DemoAnimationProps) {
  const [currentScene, setCurrentScene] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState(
    "Scene 1 of 4 • 0:00 / 1:00"
  );

  const startTimeRef = useRef<number | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const particlesRef = useRef<HTMLDivElement>(null);
  const autoStartedRef = useRef(false);
  const playAnimationRef = useRef<() => void>(() => {});

  const createParticles = useCallback(() => {
    if (!particlesRef.current) return;
    particlesRef.current.innerHTML = "";
    for (let i = 0; i < 20; i++) {
      const particle = document.createElement("div");
      particle.className = "demo-particle";
      particle.style.left = Math.random() * 100 + "%";
      particle.style.top = Math.random() * 100 + "%";
      particle.style.animationDelay = Math.random() * 6 + "s";
      particle.style.animationDuration = Math.random() * 3 + 3 + "s";
      particlesRef.current.appendChild(particle);
    }
  }, []);

  const updateProgress = useCallback(() => {
    if (!isPlaying || startTimeRef.current == null) return;

    const elapsed = (Date.now() - startTimeRef.current) / 1000;
    const progressPercent = Math.min((elapsed / TOTAL_DURATION) * 100, 100);
    const sceneIndex = Math.floor(elapsed / SCENE_DURATION);

    setProgress(progressPercent);
    const m = Math.floor(elapsed / 60);
    const s = Math.floor(elapsed % 60);
    const tM = Math.floor(TOTAL_DURATION / 60);
    const tS = TOTAL_DURATION % 60;
    setProgressText(
      `Scene ${Math.min(sceneIndex + 1, SCENES.length)} of ${SCENES.length} • ${m}:${s.toString().padStart(2, "0")} / ${tM}:${tS.toString().padStart(2, "0")}`
    );

    if (sceneIndex !== currentScene && sceneIndex < SCENES.length) {
      setCurrentScene(sceneIndex);
    }

    if (elapsed >= TOTAL_DURATION) {
      setIsPlaying(false);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      onComplete?.();
      return;
    }

    animationFrameRef.current = requestAnimationFrame(updateProgress);
  }, [isPlaying, currentScene, onComplete]);

  const playAnimation = useCallback(() => {
    if (isPlaying) {
      setIsPlaying(false);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      return;
    }
    setIsPlaying(true);
    startTimeRef.current = Date.now() - currentScene * SCENE_DURATION * 1000;
    updateProgress();
  }, [isPlaying, currentScene, updateProgress]);

  const stopAnimation = useCallback(() => {
    setIsPlaying(false);
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
  }, []);

  const restartAnimation = useCallback(() => {
    stopAnimation();
    setCurrentScene(0);
    setProgress(0);
    setProgressText("Scene 1 of 4 • 0:00 / 1:00");
  }, [stopAnimation]);

  const previousScene = useCallback(() => {
    if (currentScene > 0) {
      const next = currentScene - 1;
      setCurrentScene(next);
      if (isPlaying) {
        startTimeRef.current = Date.now() - next * SCENE_DURATION * 1000;
      }
    }
  }, [currentScene, isPlaying]);

  const nextScene = useCallback(() => {
    if (currentScene < SCENES.length - 1) {
      const next = currentScene + 1;
      setCurrentScene(next);
      if (isPlaying) {
        startTimeRef.current = Date.now() - next * SCENE_DURATION * 1000;
      }
    }
  }, [currentScene, isPlaying]);

  playAnimationRef.current = playAnimation;

  useEffect(() => {
    createParticles();
  }, [createParticles]);

  useEffect(() => {
    if (autoStart && !autoStartedRef.current) {
      autoStartedRef.current = true;
      const t = setTimeout(() => playAnimationRef.current(), 500);
      return () => clearTimeout(t);
    }
  }, [autoStart]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case " ":
        case "Enter":
          e.preventDefault();
          playAnimation();
          break;
        case "ArrowLeft":
          e.preventDefault();
          previousScene();
          break;
        case "ArrowRight":
          e.preventDefault();
          nextScene();
          break;
        case "r":
        case "R":
          e.preventDefault();
          restartAnimation();
          break;
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [playAnimation, previousScene, nextScene, restartAnimation]);

  useEffect(() => {
    const handleContextMenu = (e: MouseEvent) => e.preventDefault();
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key === "F12" ||
        (e.ctrlKey && e.shiftKey && e.key === "I") ||
        (e.ctrlKey && e.key === "u")
      ) {
        e.preventDefault();
      }
    };
    document.addEventListener("contextmenu", handleContextMenu);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("contextmenu", handleContextMenu);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return (
    <div className="demo-animation min-h-screen">
      <div
        ref={particlesRef}
        className="absolute inset-0 pointer-events-none z-0"
        aria-hidden
      />

      {/* Scene 1: Logo & Title */}
      <div
        className={`demo-scene ${currentScene === 0 ? "active" : ""}`}
        aria-hidden={currentScene !== 0}
      >
        <div className="text-center max-w-[800px] px-6 sm:px-10 py-8">
          <div className="demo-logo">S</div>
          <h1 className="demo-title">SPECTRA</h1>
          <p className="demo-subtitle">
            The best voice-controlled screen reader
          </p>
          <p className="text-base text-[#64748b] mt-5">
            Powered by Gemini Live API
          </p>
        </div>
      </div>

      {/* Scene 2: Features */}
      <div
        className={`demo-scene ${currentScene === 1 ? "active" : ""}`}
        aria-hidden={currentScene !== 1}
      >
        <div className="text-center max-w-[800px] px-6 sm:px-10 py-8">
          <h2 className="text-4xl sm:text-5xl font-bold mb-10">
            What Spectra Does
          </h2>
          <div className="demo-features">
            <div className="demo-feature">
              <div className="flex justify-center mb-2 text-[#A29BFE]">
                <Mic size={32} aria-hidden />
              </div>
              <div className="demo-feature-title">Voice Control</div>
              <div className="demo-feature-desc">
                Navigate with natural speech
              </div>
            </div>
            <div className="demo-feature">
              <div className="flex justify-center mb-2 text-[#A29BFE]">
                <Eye size={32} aria-hidden />
              </div>
              <div className="demo-feature-title">AI Vision</div>
              <div className="demo-feature-desc">
                Sees and understands your screen
              </div>
            </div>
            <div className="demo-feature">
              <div className="flex justify-center mb-2 text-[#A29BFE]">
                <Globe size={32} aria-hidden />
              </div>
              <div className="demo-feature-title">Multilingual</div>
              <div className="demo-feature-desc">Speaks 20+ languages</div>
            </div>
            <div className="demo-feature">
              <div className="flex justify-center mb-2 text-[#A29BFE]">
                <Accessibility size={32} aria-hidden />
              </div>
              <div className="demo-feature-title">Accessible</div>
              <div className="demo-feature-desc">Built for everyone</div>
            </div>
          </div>
        </div>
      </div>

      {/* Scene 3: Demo Commands */}
      <div
        className={`demo-scene ${currentScene === 2 ? "active" : ""}`}
        aria-hidden={currentScene !== 2}
      >
        <div className="text-center max-w-[800px] px-6 sm:px-10 py-8">
          <h2 className="text-4xl sm:text-5xl font-bold mb-10">
            Try These Commands
          </h2>
          <div className="demo-commands">
            <div className="demo-command">&quot;What&apos;s on my screen?&quot;</div>
            <div className="demo-command">&quot;Open Gmail&quot;</div>
            <div className="demo-command">&quot;Click the blue button&quot;</div>
            <div className="demo-command">&quot;مرحبا، افتح جوجل&quot; (Arabic)</div>
            <div className="demo-command">&quot;Ouvre YouTube&quot; (French)</div>
            <div className="demo-command">&quot;Scroll down&quot;</div>
          </div>
          <p className="text-xl text-[#A29BFE] mt-8">Just press Q and speak</p>
        </div>
      </div>

      {/* Scene 4: CTA */}
      <div
        className={`demo-scene ${currentScene === 3 ? "active" : ""}`}
        aria-hidden={currentScene !== 3}
      >
        <div className="text-center max-w-[800px] px-6 sm:px-10 py-8">
          <div className="demo-logo mx-auto mb-10">S</div>
          <h2 className="text-4xl sm:text-5xl font-bold mb-5">
            Try Spectra Today
          </h2>
          <div className="demo-cta">
            <Link
              href="/"
              className="demo-cta-button inline-block no-underline"
            >
              Get Started
            </Link>
            <a
              href="https://github.com/Aqta-ai/spectra"
              target="_blank"
              rel="noopener noreferrer"
              className="block mt-5 text-[#A29BFE] hover:text-[#c4befe] text-base flex items-center justify-center gap-2"
            >
              <Star size={16} aria-hidden />
              github.com/Aqta-ai/spectra
            </a>
            <p className="mt-5 text-[#64748b] text-sm">
              Open Source • Apache 2.0
            </p>
          </div>
        </div>
      </div>

      {/* Progress */}
      <div className="demo-progress-container">
        <div className="demo-progress-track">
          <div
            className="demo-progress-bar"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="text-xs text-[#cbd5e1] text-center" aria-live="polite">
          {progressText}
        </div>
      </div>

      {/* Controls */}
      {showControls && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 flex gap-2 z-50">
          <button
            type="button"
            onClick={previousScene}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-black/70 border border-white/20 text-white text-sm hover:bg-spectra-primary/50 hover:border-spectra-primary transition-all"
            aria-label="Previous scene"
          >
            <ChevronLeft size={16} />
            Previous
          </button>
          <button
            type="button"
            onClick={playAnimation}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-black/70 border border-white/20 text-white text-sm hover:bg-spectra-primary/50 hover:border-spectra-primary transition-all"
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            {isPlaying ? "Pause" : "Play"}
          </button>
          <button
            type="button"
            onClick={nextScene}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-black/70 border border-white/20 text-white text-sm hover:bg-spectra-primary/50 hover:border-spectra-primary transition-all"
            aria-label="Next scene"
          >
            Next
            <ChevronRight size={16} />
          </button>
          <button
            type="button"
            onClick={restartAnimation}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-black/70 border border-white/20 text-white text-sm hover:bg-spectra-primary/50 hover:border-spectra-primary transition-all"
            aria-label="Restart"
          >
            <RotateCcw size={16} />
            Watch Again
          </button>
        </div>
      )}
    </div>
  );
}
