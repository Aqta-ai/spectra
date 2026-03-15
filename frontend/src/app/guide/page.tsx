import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Guide , Spectra",
  description: "Learn how to use Spectra: voice commands, keyboard shortcuts, and tips.",
};

export default function GuidePage() {
  return (
    <div className="min-h-[100dvh] w-full px-4 sm:px-6 max-w-3xl mx-auto py-8 sm:py-12">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-sm text-spectra-muted hover:text-spectra-secondary transition-colors mb-8"
        aria-label="Back to Spectra"
      >
        <ArrowLeft size={14} aria-hidden="true" />
        Back to Spectra
      </Link>

      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight mb-2">
        How to use Spectra
      </h1>
      <p className="text-spectra-muted text-sm mb-10">
        Spectra sees your screen, speaks what matters, and acts on your voice command.
        No reading. No staring. No typing. Just talk.
      </p>

      {/* Getting started */}
      <section className="mb-10" aria-labelledby="getting-started">
        <h2 id="getting-started" className="text-lg font-medium mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">1</span>
          Getting started
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>Press <kbd className="px-1.5 py-0.5 bg-spectra-dark rounded text-[10px] font-mono text-spectra-text">Q</kbd> or say <span className="text-spectra-secondary">&quot;Hey Spectra&quot;</span> to start.</p>
          <p>Allow microphone and screen sharing when your browser asks.</p>
          <p>Spectra will say <span className="text-spectra-text">&quot;Connected&quot;</span> when ready.</p>
        </div>
      </section>

      {/* Voice commands */}
      <section className="mb-10" aria-labelledby="voice-commands">
        <h2 id="voice-commands" className="text-lg font-medium mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">2</span>
          Voice commands
        </h2>
        <div className="grid gap-2 pl-9">
          {[
            { cmd: "Where am I?", desc: "Describes the current screen" },
            { cmd: "What's on screen?", desc: "Full screen description" },
            { cmd: "Click the [button name]", desc: "Clicks an element" },
            { cmd: "Type [your text]", desc: "Types into the focused field" },
            { cmd: "Scroll down / up", desc: "Scrolls the page" },
            { cmd: "Go to [website]", desc: "Navigates to a URL" },
            { cmd: "Press Enter / Tab / Escape", desc: "Presses a key" },
            { cmd: "Remember this", desc: "Saves a screen snapshot" },
            { cmd: "What changed?", desc: "Compares to a saved snapshot" },
            { cmd: "Teach me this app", desc: "Guided tour of the screen" },
            { cmd: "Stop / Cancel", desc: "Interrupts the current action" },
          ].map(({ cmd, desc }) => (
            <div key={cmd} className="flex items-baseline gap-3 text-sm py-1.5 border-b border-white/5 last:border-0">
              <span className="text-spectra-secondary font-mono text-xs whitespace-nowrap">&quot;{cmd}&quot;</span>
              <span className="text-spectra-muted">{desc}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Keyboard shortcuts */}
      <section className="mb-10" aria-labelledby="keyboard-shortcuts">
        <h2 id="keyboard-shortcuts" className="text-lg font-medium mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">3</span>
          Keyboard shortcuts
        </h2>
        <div className="grid gap-2 pl-9">
          {[
            { key: "Q", desc: "Start or stop Spectra" },
            { key: "W", desc: "Share your screen" },
            { key: "Esc", desc: "Stop Spectra" },
            { key: "Tab", desc: "Navigate between controls" },
          ].map(({ key, desc }) => (
            <div key={key} className="flex items-center gap-3 text-sm py-1.5 border-b border-white/5 last:border-0">
              <kbd className="px-2 py-1 bg-spectra-dark rounded text-[11px] font-mono text-spectra-text min-w-[2.5rem] text-center">{key}</kbd>
              <span className="text-spectra-muted">{desc}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Chrome extension */}
      <section className="mb-10" aria-labelledby="extension">
        <h2 id="extension" className="text-lg font-medium mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">4</span>
          Spectra Bridge extension
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>
            To control other tabs (click, type, scroll on any website), install the
            <span className="text-spectra-text"> Spectra Bridge</span> Chrome extension:
          </p>
          <ol className="list-decimal list-inside space-y-1.5">
            <li>Open <span className="text-spectra-text font-mono text-xs">chrome://extensions</span></li>
            <li>Enable Developer mode (top right toggle)</li>
            <li>Click Load unpacked</li>
            <li>Select the <span className="font-mono text-xs text-spectra-text">extension/</span> folder from the repo</li>
          </ol>
          <p>Without the extension, Spectra can still describe your screen and respond by voice.</p>
        </div>
      </section>

      {/* Privacy */}
      <section className="mb-10" aria-labelledby="privacy">
        <h2 id="privacy" className="text-lg font-medium mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">5</span>
          Privacy
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>Nothing touches disk. Nothing persists.</p>
          <p>
            Screenshots are held in memory only, each new frame replaces the last.
            When your session ends, the data is garbage collected. No files, no database, no cloud storage.
          </p>
          <p>
            The only external service that sees your screen is the AI vision API for analysis.
            No other third parties are involved.
          </p>
        </div>
      </section>

      {/* Tips */}
      <section className="mb-12" aria-labelledby="tips">
        <h2 id="tips" className="text-lg font-medium mb-4 flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">6</span>
          Tips
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>Speak naturally, Spectra understands conversational language, not just commands.</p>
          <p>Say <span className="text-spectra-secondary">&quot;Stop&quot;</span> at any time to interrupt.</p>
          <p>Spectra confirms before destructive actions like deleting or sending.</p>
          <p>If Spectra can&apos;t find an element, it will scroll and try again automatically.</p>
        </div>
      </section>

      <footer className="px-4 sm:px-6 py-4 text-center text-xs text-white/30 flex flex-col items-center gap-2 border-t border-white/5">
        <a
          href="https://cloud.google.com/run"
          target="_blank"
          rel="noopener noreferrer"
          className="opacity-60 hover:opacity-90 transition-opacity"
          aria-label="Deployed on Google Cloud Run"
        >
          <img src="https://deploy.cloud.run/button.svg" alt="Run on Google Cloud" className="h-7" />
        </a>
        <div>
          Spectra
          {" · "}
          <Link href="/" className="hover:text-white/50 transition-colors">Spectra</Link>
          {" · "}
          <Link href="/overlay" className="hover:text-white/50 transition-colors">Overlay</Link>
          {" · "}
          <a href="https://github.com/Aqta-ai/spectra" target="_blank" rel="noopener noreferrer" className="hover:text-white/50 transition-colors">GitHub</a>
          {" · Apache 2.0"}
        </div>
      </footer>
    </div>
  );
}
