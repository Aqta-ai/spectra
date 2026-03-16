import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Privacy Policy · Spectra",
  description:
    "Spectra privacy policy, what we process, what leaves your device, and what we store (nothing).",
};

export default function PrivacyPage() {
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
        Privacy Policy
      </h1>
      <p className="text-spectra-muted text-sm mb-10">
        Aqta Technologies Ltd, Dublin, Ireland — Last updated: 16 March 2026
      </p>

      {/* Summary */}
      <section className="mb-10" aria-labelledby="summary">
        <h2
          id="summary"
          className="text-lg font-medium mb-4 flex items-center gap-2"
        >
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">
            1
          </span>
          Summary
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>
            Spectra is designed with privacy at its core. We store nothing. No
            screenshots, no audio, no browsing history, no personal data.
            Everything happens in memory and is discarded when your session
            ends.
          </p>
        </div>
      </section>

      {/* What Spectra processes */}
      <section className="mb-10" aria-labelledby="what-we-process">
        <h2
          id="what-we-process"
          className="text-lg font-medium mb-4 flex items-center gap-2"
        >
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">
            2
          </span>
          What Spectra processes
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>
            Spectra only processes data while a session is active, nothing is
            stored, recorded, or retained. Screen and voice data are streamed
            to Google&apos;s Gemini API in real time for understanding and are
            never saved. When your session ends, everything is discarded. No
            accounts, no tracking, no analytics.
          </p>
        </div>
      </section>

      {/* What leaves your device */}
      <section className="mb-10" aria-labelledby="what-leaves">
        <h2
          id="what-leaves"
          className="text-lg font-medium mb-4 flex items-center gap-2"
        >
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">
            3
          </span>
          What leaves your device
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>
            The only data that leaves your device is sent to{" "}
            <strong>Google&apos;s Gemini API</strong>:
          </p>
          <ul className="list-disc list-inside space-y-2">
            <li>
              Screen frames (JPEG images, ~80 KB each) — for visual
              understanding
            </li>
            <li>
              Voice audio (PCM 16 kHz) — for speech recognition and response
              generation
            </li>
          </ul>
          <p>
            This data is sent via an encrypted WebSocket connection (WSS/TLS).{" "}
            <strong>No other third-party services</strong> receive your data.
            There are no analytics, tracking pixels, or advertising networks.
          </p>
        </div>
      </section>

      {/* Google's data handling */}
      <section className="mb-10" aria-labelledby="google-data">
        <h2
          id="google-data"
          className="text-lg font-medium mb-4 flex items-center gap-2"
        >
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">
            4
          </span>
          Google&apos;s data handling
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>
            Data sent to the Gemini API is subject to Google&apos;s own privacy
            policies:
          </p>
          <ul className="list-disc list-inside space-y-2">
            <li>
              <a
                href="https://policies.google.com/privacy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-spectra-secondary hover:underline"
              >
                Google Privacy Policy
              </a>
            </li>
            <li>
              <a
                href="https://ai.google.dev/gemini-api/terms"
                target="_blank"
                rel="noopener noreferrer"
                className="text-spectra-secondary hover:underline"
              >
                Gemini API Terms of Service
              </a>
            </li>
          </ul>
        </div>
      </section>

      {/* What we store */}
      <section className="mb-10" aria-labelledby="what-we-store">
        <h2
          id="what-we-store"
          className="text-lg font-medium mb-4 flex items-center gap-2"
        >
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">
            5
          </span>
          What we store
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>
            <strong>Nothing.</strong>
          </p>
          <ul className="list-disc list-inside space-y-2">
            <li>No files are written to disc</li>
            <li>No database is used</li>
            <li>No cloud storage buckets are provisioned</li>
            <li>No cookies are set beyond what HTTPS requires</li>
            <li>No local storage is used for tracking</li>
            <li>
              No server-side logs contain your screen content or audio
            </li>
          </ul>
        </div>
      </section>

      {/* Chrome extension */}
      <section className="mb-10" aria-labelledby="extension-privacy">
        <h2
          id="extension-privacy"
          className="text-lg font-medium mb-4 flex items-center gap-2"
        >
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">
            6
          </span>
          Chrome extension (Spectra Bridge)
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>
            The extension requires <code>&lt;all_urls&gt;</code> permission to
            execute browser actions. It:
          </p>
          <ul className="list-disc list-inside space-y-2">
            <li>Does not collect, transmit, or store any browsing data</li>
            <li>
              Does not communicate with any server other than the Spectra
              frontend tab
            </li>
            <li>Does not read or store your passwords or cookies</li>
            <li>
              Only executes actions when explicitly instructed by the Spectra
              frontend
            </li>
            <li>
              Is{" "}
              <a
                href="https://github.com/Aqta-ai/spectra/tree/main/extension"
                target="_blank"
                rel="noopener noreferrer"
                className="text-spectra-secondary hover:underline"
              >
                fully open source
              </a>
            </li>
          </ul>
        </div>
      </section>

      {/* Data protection rights */}
      <section className="mb-10" aria-labelledby="your-rights">
        <h2
          id="your-rights"
          className="text-lg font-medium mb-4 flex items-center gap-2"
        >
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">
            7
          </span>
          Your rights
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>
            Because Spectra does not store personal data, most data subject
            rights (access, rectification, erasure, portability) are satisfied
            by default — there is no data to access, correct, delete, or
            transfer.
          </p>
          <p>
            If you have taught Spectra preferences during a session, you can
            clear them by saying{" "}
            <span className="text-spectra-secondary">
              &quot;Forget everything&quot;
            </span>{" "}
            or{" "}
            <span className="text-spectra-secondary">
              &quot;Clear my memory.&quot;
            </span>
          </p>
        </div>
      </section>

      {/* Contact */}
      <section className="mb-12" aria-labelledby="contact">
        <h2
          id="contact"
          className="text-lg font-medium mb-4 flex items-center gap-2"
        >
          <span className="w-7 h-7 rounded-full bg-spectra-primary/20 text-spectra-secondary text-xs flex items-center justify-center">
            8
          </span>
          Contact
        </h2>
        <div className="space-y-3 text-sm text-spectra-muted pl-9">
          <p>
            <strong>Aqta Technologies Ltd</strong>
            <br />
            Dublin, Ireland
          </p>
          <p>
            <a
              href="https://aqta.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-spectra-secondary hover:underline"
            >
              aqta.ai
            </a>
            {" · "}
            <a
              href="https://github.com/Aqta-ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-spectra-secondary hover:underline"
            >
              GitHub
            </a>
          </p>
        </div>
      </section>

      <footer className="px-4 sm:px-6 py-4 text-center text-xs text-white/30 flex flex-col items-center gap-2 border-t border-white/5">
        <div>
          Spectra
          {" · "}
          <Link
            href="/"
            className="hover:text-white/50 transition-colors"
          >
            Home
          </Link>
          {" · "}
          <Link
            href="/guide"
            className="hover:text-white/50 transition-colors"
          >
            Guide
          </Link>
          {" · "}
          <a
            href="https://github.com/Aqta-ai/spectra"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white/50 transition-colors"
          >
            GitHub
          </a>
          {" · Apache 2.0"}
        </div>
      </footer>
    </div>
  );
}
