"use client";

import { useState, useRef, useCallback, useMemo, useEffect } from "react";
import {
  Eye,
  Loader2,
  MousePointerClick,
  Link2,
  TextCursorInput,
  Heading,
  TriangleAlert,
  CircleCheck,
  ExternalLink,
  Globe,
} from "lucide-react";

interface PageElement {
  type: "button" | "link" | "input" | "heading";
  text: string;
  role: string;
  selector: string;
  importance: "high" | "medium" | "low";
}

interface AnalyseResult {
  url: string;
  title: string;
  elements: PageElement[];
}

// Derive HTTP base from NEXT_PUBLIC_WS_URL or NEXT_PUBLIC_API_URL
// wss://backend.run.app/ws → https://backend.run.app
// ws://localhost:8080/ws → http://localhost:8080
// Production: NEXT_PUBLIC_WS_URL is set at build time by deploy script
function getApiUrl(): string {
  const api = process.env.NEXT_PUBLIC_API_URL;
  if (api) return api.replace(/\/$/, "");
  const ws = process.env.NEXT_PUBLIC_WS_URL;
  if (ws) {
    const protocol = ws.startsWith("wss") ? "https" : "http";
    return ws.replace(/^wss?:\/\//, `${protocol}://`).replace(/\/ws\/?$/, "");
  }
  return "http://localhost:8080";
}
const API_URL = getApiUrl();

// Session-scoped cache: skip the round-trip if we've already analysed this URL
const _resultCache = new Map<string, AnalyseResult>();

const PRESETS = [
  { label: "apple.com", url: "https://www.apple.com" },
  { label: "bbc.co.uk", url: "https://www.bbc.co.uk" },
  { label: "github.com", url: "https://github.com" },
  { label: "wikipedia.org", url: "https://en.wikipedia.org" },
];

// Preload popular sites on mount for instant results
const PRELOAD_URLS = [
  "https://www.bbc.co.uk",
  "https://github.com",
];

const TYPE_ICON = {
  button: MousePointerClick,
  link: Link2,
  input: TextCursorInput,
  heading: Heading,
} as const;

const IMPORTANCE_BADGE: Record<string, { bg: string; color: string }> = {
  high: { bg: "rgba(108,92,231,0.25)", color: "#a29bfe" },
  medium: { bg: "rgba(148,161,178,0.15)", color: "#94a1b2" },
  low: { bg: "rgba(255,255,255,0.05)", color: "#64748b" },
};

function deriveA11yHints(elements: PageElement[]): { ok: boolean; text: string }[] {
  const hints: { ok: boolean; text: string }[] = [];

  const unlabelled = elements.filter(
    (e) => e.type === "input" && (!e.text || e.text.trim() === "")
  );
  if (unlabelled.length > 0)
    hints.push({
      ok: false,
      text: `${unlabelled.length} input${unlabelled.length > 1 ? "s" : ""} missing accessible label`,
    });

  const genericButtons = elements.filter(
    (e) =>
      e.type === "button" &&
      (!e.text ||
        ["click", "click here", "submit", "button", "ok", "go"].includes(
          e.text.toLowerCase().trim()
        ))
  );
  if (genericButtons.length > 0)
    hints.push({
      ok: false,
      text: `${genericButtons.length} button${genericButtons.length > 1 ? "s" : ""} with unclear or generic text`,
    });

  const genericLinks = elements.filter(
    (e) =>
      e.type === "link" &&
      (!e.text ||
        ["here", "click here", "read more", "more", "link"].includes(
          e.text.toLowerCase().trim()
        ))
  );
  if (genericLinks.length > 0)
    hints.push({
      ok: false,
      text: `${genericLinks.length} link${genericLinks.length > 1 ? "s" : ""} with non-descriptive anchor text ("read more", "here")`,
    });

  const headings = elements.filter((e) => e.type === "heading");
  const hasH1 = headings.some(
    (e) => e.role?.toLowerCase() === "h1" || e.role?.toLowerCase().includes("h1")
  );
  if (headings.length > 0 && !hasH1)
    hints.push({
      ok: false,
      text: "No H1 detected , screen-readers expect one landmark heading per page",
    });

  if (hints.length === 0)
    hints.push({ ok: true, text: "No obvious accessibility issues found in the extracted elements." });

  return hints;
}

export default function OverlayPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState<"fetch" | "analyse" | null>(null);
  const [result, setResult] = useState<AnalyseResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"elements" | "a11y">("elements");
  const abortRef = useRef<AbortController | null>(null);

  // Preload common sites in the background for instant results
  const preloadSites = useCallback(async () => {
    for (const url of PRELOAD_URLS) {
      if (_resultCache.has(url)) continue;
      try {
        const res = await fetch(`${API_URL}/api/analyse-page`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
        });
        if (res.ok) {
          const data = await res.json();
          _resultCache.set(url, data);
        }
      } catch {
        // Silently fail preloading
      }
    }
  }, []);

  // Preload on mount
  useEffect(() => {
    const timer = setTimeout(preloadSites, 1000); // Delay 1s to not block initial render
    return () => clearTimeout(timer);
  }, [preloadSites]);

  const analyse = useCallback(
    async (targetUrl?: string) => {
      const raw = (targetUrl ?? url).trim();
      if (!raw) return;
      const normalised = raw.startsWith("http") ? raw : `https://${raw}`;

      // Cancel any in-flight request
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      // Client-side cache hit , instant
      const cached = _resultCache.get(normalised);
      if (cached) {
        setResult(cached);
        setError(null);
        if (targetUrl) setUrl(targetUrl);
        return;
      }

      setLoading(true);
      setError(null);
      setResult(null);
      setActiveTab("elements");
      setLoadingStage("fetch");
      try {
        const res = await fetch(`${API_URL}/api/analyse-page`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: normalised }),
          signal: abortRef.current.signal,
        });
        setLoadingStage("analyse");
        const data = await res.json();
        if (!res.ok) {
          const detail = data.detail || data.error;
          if (res.status === 504) throw new Error("Gemini timed out , try again or use a simpler URL.");
          throw new Error(detail || `HTTP ${res.status}`);
        }
        _resultCache.set(normalised, data);
        setResult(data);
        if (targetUrl) setUrl(targetUrl);
      } catch (e: unknown) {
        if (e instanceof Error && e.name === "AbortError") return;
        const msg = e instanceof Error ? e.message : String(e);
        // "Failed to fetch" usually means CORS, network, or backend not reachable
        if (msg === "Failed to fetch") {
          setError(
            "Could not reach the backend. Ensure the backend is running, ALLOWED_ORIGINS includes this site, and GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT is set."
          );
        } else {
          setError(msg);
        }
      } finally {
        setLoading(false);
        setLoadingStage(null);
      }
    },
    [url]
  );

  const grouped = useMemo(
    () =>
      result
        ? {
            button: result.elements.filter((e) => e.type === "button"),
            link: result.elements.filter((e) => e.type === "link"),
            input: result.elements.filter((e) => e.type === "input"),
            heading: result.elements.filter((e) => e.type === "heading"),
          }
        : null,
    [result]
  );

  const a11yHints = useMemo(
    () => (result ? deriveA11yHints(result.elements) : []),
    [result]
  );

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--spectra-bg)", color: "var(--spectra-text)" }}
    >
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header
        className="px-6 py-4 flex-shrink-0"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <a href="/" className="flex items-center gap-2 opacity-60 hover:opacity-100 transition-opacity">
              <img src="/icon512.png" alt="Spectra" className="w-6 h-6" />
            </a>
            <span style={{ color: "rgba(255,255,255,0.2)" }}>/</span>
            <div>
              <h1
                className="text-lg font-semibold tracking-tight leading-none"
                style={{ color: "var(--spectra-secondary)" }}
              >
                Overlay
              </h1>
              <p className="text-xs mt-0.5" style={{ color: "var(--spectra-muted)" }}>
                See your site the way an AI agent or screen-reader does
              </p>
            </div>
          </div>
          <a
            href="/guide"
            className="text-xs transition-colors hidden sm:block"
            style={{ color: "var(--spectra-muted)" }}
          >
            Guide
          </a>
        </div>
      </header>

      {/* ── URL bar ────────────────────────────────────────────────────────── */}
      <div
        className="px-6 py-4 flex-shrink-0"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}
      >
        <div className="max-w-7xl mx-auto">
          <div className="flex gap-2">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && analyse()}
              placeholder="https://example.com"
              aria-label="Page URL to analyse"
              className="flex-1 rounded-lg px-4 py-2.5 text-sm"
              style={{
                background: "var(--spectra-surface)",
                border: "1px solid rgba(255,255,255,0.12)",
                color: "var(--spectra-text)",
                outline: "none",
              }}
            />
            <button
              onClick={() => analyse()}
              disabled={loading || !url.trim()}
              className="px-5 py-2.5 rounded-lg text-sm font-semibold transition-opacity disabled:opacity-40"
              style={{ background: "var(--spectra-primary)", color: "#fff" }}
            >
              {loading ? "Analysing…" : "Analyse"}
            </button>
          </div>

          {/* Preset chips */}
          <div className="flex gap-2 mt-2.5 flex-wrap">
            {PRESETS.map((p) => (
              <button
                key={p.url}
                onClick={() => {
                  setUrl(p.url);
                  analyse(p.url);
                }}
                className="px-3 py-1 rounded-full text-xs font-medium transition-opacity hover:opacity-75"
                style={{
                  background: "var(--spectra-surface)",
                  color: "var(--spectra-secondary)",
                  border: "1px solid rgba(162,155,254,0.2)",
                }}
              >
                Try {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Content ────────────────────────────────────────────────────────── */}
      <div className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">
        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--spectra-secondary)" }} />
            <div>
              <p className="text-sm font-medium">
                {loadingStage === "fetch" ? "Fetching page…" : "Analysing structure…"}
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--spectra-muted)" }}>
                {loadingStage === "fetch" 
                  ? "Downloading HTML and extracting content" 
                  : "Running AI analysis and accessibility checks"}
              </p>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div
            className="rounded-lg px-4 py-3 text-sm"
            style={{ background: "#450a0a", color: "#fca5a5", border: "1px solid #991b1b" }}
          >
            <strong>Error: </strong>{error}
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="flex flex-col gap-4">
            {/* Site card */}
            <div
              className="rounded-xl px-4 py-3 flex items-center gap-3"
              style={{ background: "var(--spectra-surface)", border: "1px solid rgba(255,255,255,0.08)" }}
            >
              <Globe className="w-4 h-4 shrink-0" style={{ color: "var(--spectra-secondary)" }} />
              <div className="flex-1 min-w-0">
                {result.title && (
                  <p className="text-sm font-medium truncate">{result.title}</p>
                )}
                <p className="text-xs truncate" style={{ color: "var(--spectra-muted)" }}>{result.url}</p>
              </div>
              <a
                href={result.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium shrink-0 transition-opacity hover:opacity-75"
                style={{ background: "rgba(255,255,255,0.08)", color: "var(--spectra-text)" }}
              >
                Open
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            {/* Overview counts */}
            {grouped && (
              <div className="grid grid-cols-4 gap-2">
                {(["button", "link", "input", "heading"] as const).map((type) => {
                  const Icon = TYPE_ICON[type];
                  return (
                    <div
                      key={type}
                      className="rounded-lg p-3 text-center flex flex-col items-center gap-1"
                      style={{ background: "var(--spectra-surface)" }}
                    >
                      <Icon className="w-4 h-4" style={{ color: "var(--spectra-secondary)", opacity: 0.7 }} />
                      <div
                        className="text-xl font-bold leading-none"
                        style={{ color: "var(--spectra-secondary)" }}
                      >
                        {grouped[type].length}
                      </div>
                      <div className="text-xs capitalize" style={{ color: "var(--spectra-muted)" }}>
                        {type}s
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Tabs */}
            <div
              className="flex gap-1 rounded-lg p-1"
              style={{ background: "var(--spectra-surface)" }}
            >
              {(["elements", "a11y"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className="flex-1 py-1.5 text-xs font-medium rounded-md transition-colors"
                  style={{
                    background: activeTab === tab ? "var(--spectra-primary)" : "transparent",
                    color: activeTab === tab ? "#fff" : "var(--spectra-muted)",
                  }}
                >
                  {tab === "elements" ? "Interactive elements" : "Accessibility hints"}
                </button>
              ))}
            </div>

            {/* Elements tab */}
            {activeTab === "elements" && grouped && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {(["heading", "button", "link", "input"] as const)
                  .filter((t) => grouped[t].length > 0)
                  .map((type) => {
                    const Icon = TYPE_ICON[type];
                    return (
                      <div key={type}>
                        <h3
                          className="text-xs font-semibold uppercase tracking-wider mb-2 flex items-center gap-1.5"
                          style={{ color: "var(--spectra-muted)" }}
                        >
                          <Icon className="w-3 h-3" />
                          {type}s ({grouped[type].length})
                        </h3>
                        <div className="flex flex-col gap-1.5">
                          {grouped[type].map((el, i) => (
                            <div
                              key={i}
                              className="rounded-lg px-3 py-2.5 flex items-start gap-2.5"
                              style={{ background: "var(--spectra-surface)" }}
                            >
                              <Icon
                                className="w-3.5 h-3.5 mt-0.5 shrink-0"
                                style={{ color: "var(--spectra-secondary)" }}
                              />
                              <div className="flex-1 min-w-0">
                                <div className="text-sm font-medium truncate">
                                  {el.text || (
                                    <em style={{ color: "var(--spectra-muted)" }}>no text</em>
                                  )}
                                </div>
                                <div className="flex gap-1.5 mt-1 flex-wrap">
                                  {el.role && (
                                    <span
                                      className="text-xs px-1.5 py-0.5 rounded"
                                      style={{
                                        background: "rgba(108,92,231,0.18)",
                                        color: "var(--spectra-secondary)",
                                      }}
                                    >
                                      {el.role}
                                    </span>
                                  )}
                                  {el.importance && IMPORTANCE_BADGE[el.importance] && (
                                    <span
                                      className="text-xs px-1.5 py-0.5 rounded"
                                      style={IMPORTANCE_BADGE[el.importance]}
                                    >
                                      {el.importance}
                                    </span>
                                  )}
                                  {el.selector && (
                                    <span
                                      className="text-xs px-1.5 py-0.5 rounded font-mono"
                                      style={{
                                        background: "rgba(255,255,255,0.05)",
                                        color: "var(--spectra-muted)",
                                      }}
                                    >
                                      {el.selector}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}

            {/* A11y tab */}
            {activeTab === "a11y" && (
              <div className="flex flex-col gap-2">
                {a11yHints.map((hint, i) => (
                  <div
                    key={i}
                    className="rounded-lg px-3 py-2.5 text-sm flex gap-2.5 items-start"
                    style={{ background: "var(--spectra-surface)" }}
                  >
                    {hint.ok ? (
                      <CircleCheck className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "#4ade80" }} />
                    ) : (
                      <TriangleAlert className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "#facc15" }} />
                    )}
                    <span>{hint.text}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!loading && !result && !error && (
          <div className="py-16 flex flex-col items-center text-center gap-6">
            <div
              className="inline-flex items-center justify-center w-16 h-16 rounded-2xl"
              style={{ background: "rgba(108,92,231,0.12)", border: "1px solid rgba(108,92,231,0.2)" }}
            >
              <Eye className="w-7 h-7" style={{ color: "var(--spectra-secondary)" }} />
            </div>
            <div>
              <p className="text-xl font-semibold mb-2">See your site the way AI does</p>
              <p className="text-sm max-w-md mx-auto" style={{ color: "var(--spectra-muted)" }}>
                See buttons, links, inputs, and headings exactly as Spectra does.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-3 text-xs">
              {[
                { icon: <MousePointerClick className="w-3.5 h-3.5" />, label: "Buttons & links" },
                { icon: <TextCursorInput className="w-3.5 h-3.5" />, label: "Form inputs" },
                { icon: <Heading className="w-3.5 h-3.5" />, label: "Heading structure" },
                { icon: <TriangleAlert className="w-3.5 h-3.5" />, label: "Accessibility hints" },
              ].map(({ icon, label }) => (
                <span
                  key={label}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
                  style={{ background: "var(--spectra-surface)", color: "var(--spectra-muted)", border: "1px solid rgba(255,255,255,0.07)" }}
                >
                  {icon}{label}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer
        className="px-4 sm:px-6 py-4 text-center text-xs flex-shrink-0 flex flex-col items-center gap-2"
        style={{ borderTop: "1px solid rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.5)" }}
      >
        <a
          href="https://cloud.google.com/run"
          target="_blank"
          rel="noopener noreferrer"
          className="opacity-60 hover:opacity-90 transition-opacity"
          aria-label="Deployed on Google Cloud Run"
        >
          <img
            src="https://deploy.cloud.run/button.svg"
            alt="Run on Google Cloud"
            className="h-7"
          />
        </a>
        <div>
          Built by Anya, Aqta
          {" · "}
          <a href="/" className="hover:text-white/80 transition-colors">
            Spectra
          </a>
          {" · "}
          <a href="/guide" className="hover:text-white/80 transition-colors">
            Guide
          </a>
          {" · "}
          <a
            href="https://github.com/Aqta-ai/spectra"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white/80 transition-colors"
          >
            GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
