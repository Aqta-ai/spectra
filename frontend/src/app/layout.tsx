import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Spectra | Your screen, your voice, your way",
  description:
    "For anyone who can't see a screen, doesn't want to stare at one or just needs their hands free. Spectra sees your screen, speaks what matters, and acts on your voice command.",
  keywords: ["accessibility", "screen reader", "AI agent", "voice control", "browser automation", "hands-free browsing"],
  authors: [{ name: "Anya from Aqta", url: "https://github.com/Aqta-ai/spectra" }],
  creator: "Anya from Aqta",
  metadataBase: new URL("https://spectra.aqta.ai"),
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/icon16.png", sizes: "16x16", type: "image/png" },
      { url: "/icon32.png", sizes: "32x32", type: "image/png" },
      { url: "/icon48.png", sizes: "48x48", type: "image/png" },
      { url: "/icon128.png", sizes: "128x128", type: "image/png" },
      { url: "/icon512.png", sizes: "512x512", type: "image/png" },
    ],
    shortcut: "/icon32.png",
    apple: "/icon512.png",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Spectra",
  },
  formatDetection: {
    telephone: false,
  },
  openGraph: {
    title: "Spectra | Your screen, your voice, your way",
    description:
      "For anyone who can't see a screen, doesn't want to stare at one or just needs their hands free.",
    url: "https://spectra.aqta.ai",
    siteName: "Spectra",
    locale: "en_GB",
    type: "website",
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: "Spectra | AI accessibility agent. Your screen, your voice, your way.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Spectra | Your screen, your voice, your way",
    description:
      "For anyone who can't see a screen, doesn't want to stare at one or just needs their hands free.",
    creator: "@AqtaTech",
    images: ["/opengraph-image"],
  },
};

export const viewport: Viewport = {
  themeColor: "#6C5CE7",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en-GB" suppressHydrationWarning>
      <head />
      <body>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-spectra-primary focus:text-white focus:rounded"
        >
          Skip to main content
        </a>
        <div
          className="sr-only"
          role="region"
          aria-label="Keyboard shortcuts"
        >
          <h2>Keyboard shortcuts</h2>
          <ul>
            <li>Q: Start or stop Spectra</li>
            <li>W: Share your screen</li>
            <li>Escape: Stop Spectra</li>
            <li>Tab: Navigate between controls</li>
          </ul>
        </div>
        <main id="main-content" role="main">
          {children}
        </main>
      </body>
    </html>
  );
}
