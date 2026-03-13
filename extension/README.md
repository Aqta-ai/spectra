# Spectra Bridge — Browser Extension

AI screen reader and voice assistant for blind and hands-free users. Built by Anya from Aqta.

## Browser support

| Browser | Supported |
|---------|-----------|
| **Chrome, Edge, Brave, Opera** | ✅ Yes |
| **Arc, Comet** | ✅ Yes (Chromium-based) |
| **Firefox** | ⚠️ May work (Manifest V3); not officially tested |
| **Safari** | ❌ No — Safari uses a different extension model |

Load as an **unpacked extension** in any Chromium-based browser (Chrome, Edge, Arc, Comet, etc.). Safari would require a separate Safari App Extension build.

## Installation

1. Open your browser (Chrome, Edge, Arc, Comet, etc.) and go to `chrome://extensions/` (or the equivalent Extensions page)
2. Enable **Developer mode** (toggle, top right)
3. Click **Load unpacked**
4. Select the `extension/` folder from this repo

Runs the same in **Chrome, Arc, Comet**, and other Chromium-based browsers.

## Usage

1. Install Spectra Bridge
2. Start Spectra at http://localhost:3000
3. Open any website in another tab (e.g. Gmail, BBC News, Google)
4. Press **Q** or say "Hey Spectra" — Spectra sees your screen and takes actions via voice

## How It Works

1. **Vision AI** — Gemini analyses screenshots to understand what's on screen
2. **Coordinate scaling** — captures at 960x540, scales to viewport coordinates for precise clicks
3. **Extension execution** — Spectra Bridge receives actions and executes them on the target tab

- `content.js` — Injected into every tab. On the Spectra page it bridges messages to the background worker. On other pages it executes actions (click, type, scroll, etc.)
- `background.js` — Service worker that routes messages from Spectra to the active target tab

## Supported Actions

| Action | Parameters | Description |
|--------|------------|-------------|
| `click` | x, y, description, captureWidth, captureHeight | Click at scaled coordinates with visual highlight |
| `type` | text, x, y, description, captureWidth, captureHeight | Type into input — finds by coordinates, description, or first visible field |
| `scroll` | direction, amount | Scroll up/down with keyboard fallback |
| `key` | key | Press Enter, Tab, Escape, arrows, etc. |
| `navigate` | url | Navigate the tab to a URL |
| `highlight_element` | x, y, label | Highlight an element without clicking |
| `read_selection` | mode (selected/paragraph/page) | Read text content from the page |

## Troubleshooting

- **Clicks missing target** — Make sure Spectra Bridge v2.0.0+ is loaded (has coordinate scaling)
- **Actions not working** — Ensure the target page is the active tab (not chrome:// pages)
- **Extension not detected** — Reload at `chrome://extensions/` by clicking the refresh icon

## Maintainer

**Anya Chueayen** — Aqta Technologies Ltd, Dublin, Ireland

- GitHub: [https://github.com/Aqta-ai](https://github.com/Aqta-ai)
- Website: [https://aqta.ai](https://aqta.ai)
