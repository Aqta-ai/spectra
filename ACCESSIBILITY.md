# ♿ Spectra Accessibility Features

Spectra is designed from the ground up for blind, visually impaired, and hands-free users.

---

## 🎤 For Blind & Low-Vision Users

### Starting Spectra (No Mouse Required)

- **Q key** — start or stop Spectra
- **W key** — share your screen (after starting)
- **Escape key** — stop Spectra
- **"Hey Spectra"** — wake word activation, no button press needed (also "Start Spectra", "OK Spectra", or just "Spectra")
- **Audio confirmation** — Spectra announces "Spectra is connected and ready. Press Q to start, or say Hey Spectra." when connected
- **"Listening" announcement** — ARIA assertive region announces "Listening" when the mic unmutes so you know it's safe to speak

### Screen Sharing Permission (Browser Limitation)

When you first start, the browser will ask for screen sharing permission. This dialog has limited accessibility:

- **Tab** — move between "Chrome Tab", "Window", "Entire Screen" options
- **Arrow keys** — navigate the list of available screens/windows
- **Enter** — select and share
- **Escape** — cancel

> **Tip:** Select "Entire Screen" (usually the first option after tabbing). You only need to grant this once per session. Spectra also works without screen sharing for voice-only interactions.

### Using Spectra

1. Navigate to the page with your screen reader
2. Press **Q** or say **"Hey Spectra"** to start
3. Allow screen sharing and microphone access when prompted
4. Say **"Where am I?"** to hear a description of your screen
5. Say **"Click the blue button"** or **"Type hello world"** to interact
6. Press **Q** or **Escape** to stop

### Voice Commands

| Command | What it does |
|---------|-------------|
| "Where am I?" / "What's on screen?" | Describes current page |
| "Read this page" | Reads the main content aloud |
| "Click the [description]" | Clicks a button, link, or element |
| "Type [text]" | Types into the focused field |
| "Scroll down / up" | Scrolls the page |
| "Go to [website]" | Navigates to a URL |
| "Press Enter / Tab / Escape" | Presses a key |
| "Remember this" | Saves a screen snapshot |
| "What changed?" | Compares to a saved snapshot |
| "Teach me this app" | Guided tour of the screen |
| "Stop" / "Cancel" | Interrupts the current action |

### Audio Output

- Gemini native audio (Aoede voice), natural, clear speech
- Audio plays automatically through your speakers/headphones
- **No conflict with screen readers** — Spectra speaks via Web Audio API, screen reader reads the UI. They can coexist
- Mic is automatically muted while Spectra speaks to prevent echo feedback loops
- Unmute happens only after all audio finishes, with a 2.5s safety timeout

---

## ⌨️ Keyboard & Navigation

| Feature | Detail |
|---------|--------|
| **Global shortcuts** | Q (toggle), W (screen share), Escape (stop). Work even when a text input is focused |
| **Skip-to-content link** | `<a href="#main-content">Skip to main content</a>`, visually hidden, visible on focus |
| **Main landmark** | `<main id="main-content" role="main">` wraps all content |
| **Hidden shortcut docs** | Screen-reader-only `role="region"` listing Q, W, Escape, Tab |
| **Toggleable shortcuts panel** | Expandable panel in header with `<kbd>` elements |
| **Persistent shortcut hints** | Always visible in active state: "Q toggle · W screen · Esc stop" |
| **Body focus management** | `tabIndex=-1` on body, auto-focus on mount, clicks on non-interactive areas refocus body so shortcuts always work |
| **High-contrast focus ring** | Yellow `#facc15`, 3px solid, 3px offset on all `*:focus-visible`, WCAG 2.1 AA compliant |
| **Orb focus ring** | `focus-visible:outline-4 focus-visible:outline-yellow-400` on both hero and mini orb |
| **Guide page section navigation** | Every `<section>` uses `aria-labelledby` pointing to its heading |

---

## 🔊 Screen Reader / ARIA

### Dual ARIA Live Regions

Spectra uses two ARIA live regions to keep screen reader users informed without moving focus:

- **`aria-live="assertive"`** — urgent events:
  - "Spectra is connected and ready. Press Q to start, or say Hey Spectra."
  - "Spectra has disconnected."
  - "Connection lost. Reconnecting..."
  - "Could not reconnect. Please press Q to try again."
  - "Listening" (mic unmuted, safe to speak)
  - "Failed to start Spectra. Please check microphone permissions."

- **`aria-live="polite"`** — status and responses:
  - "You said: {text}. Spectra is thinking…"
  - Action labels: "Looking at your screen...", "Clicking...", "Scrolling..."
  - Action results: "Page loaded: github.com.", "Scrolled down.", "Typed into search."
  - Spectra's full response text

### ARIA Attributes on All Controls

| Element | ARIA |
|---------|------|
| Orb button | `aria-label="Start Spectra"` / `"Stop Spectra (Q)"` |
| Connection indicator | `aria-label="Connection: {state}"` |
| Extension status | `"Browser extension connected"` / `"Browser extension not found"` |
| Shortcuts toggle | `aria-label="Toggle keyboard shortcuts"` + `aria-expanded` |
| Share screen button | `"Share screen (W)"` / `"Stop screen share (W)"` |
| End session button | `"End session"` |
| Text input | `"Message to Spectra"` |
| Send button | `"Send message"` |
| Start CTA | `"Start Spectra, tap to begin"` |
| Connect CTA | `"Connect to Spectra"` |
| Thinking dots | `aria-label="Spectra is thinking"` |
| Onboarding dialog | `role="dialog"` + `aria-labelledby` + `aria-describedby` |
| Reconnecting spinner | `role="status" aria-live="polite"` |
| Extension banner | `role="status"` |
| Conversation area | `role="log"` + `aria-label="Conversation with Spectra"` |

### Hidden from Assistive Technology

All decorative elements use `aria-hidden="true"`: logo image, decorative SVG icons, orb glow rings, hero mesh background, waveform bars, chat avatars.

### HTML Lang

`<html lang="en-GB">` set for correct screen reader pronunciation.

### Screen Reader Compatibility

Designed for VoiceOver (macOS), NVDA and JAWS (Windows). The AI system prompt includes VoiceOver-specific guidance (e.g., Ctrl+Option+Command+H for headings) and prefers keyboard/Tab navigation over coordinate-based clicking when used alongside screen readers.

---

## 👁️ Visual Accessibility

| Feature | Detail |
|---------|--------|
| **High-contrast focus ring** | Yellow `#facc15`, 3px, clearly visible on dark `#0f172a` background |
| **Three distinct orb states** | Idle (purple breathe), Listening (green glow), Speaking (violet glow) |
| **Waveform visualization** | 5 animated bars during listening, visual confirmation mic is active |
| **Connection state colors** | Green = connected, amber pulse = reconnecting, red = failed, dim = disconnected |
| **Status indicators** | Individual colored dots + text for mic, screen, and connection |
| **44px touch targets** | `@media (pointer: coarse)` sets `min-height: 44px` on all interactive elements (WCAG 2.5.5) |
| **Pinch-to-zoom** | `userScalable: true`, `maximumScale: 5` — allows up to 5x zoom |
| **Safe area insets** | `env(safe-area-inset-*)` padding for notched devices in PWA mode |
| **Click feedback (extension)** | Purple cursor dot + element highlight box with label overlay |

---

## 🎭 Motion & Sensory

**Full `prefers-reduced-motion` support:**

All animations are disabled when the user prefers reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

This covers: orb animations (idle/listen/speak), waveform bars, CTA glow pulse, message slide-in, fade-in transitions.

---

## 🌐 Multilingual

- **AI auto-matches user language** — if you speak French, Spectra responds in French. Arabic, Spanish, Hindi, Chinese, German, and any other language
- **30+ languages** via Gemini native audio
- **Browser locale wake word detection** — speech recognition uses `navigator.language` instead of hardcoding English
- **Core prompt enforces it** — "I NEVER force English responses"

---

## 🔒 Privacy & Safety

- **Destructive action confirmation** — AI must call `confirm_action` before: deleting files/emails/accounts, making purchases/payments, submitting legal forms, unsubscribing, or permanently removing data
- **Email safety** — drafts are read back to user and explicit "yes" is required before sending
- **No data storage** — screenshots held in RAM only, each frame replaces the last. No files, no database, no cloud storage
- **No accounts, no tracking, no analytics**
- **Extension origin restriction** — only accepts messages from whitelisted Spectra origins

---

## 🧩 Browser Extension Accessibility

| Feature | Detail |
|---------|--------|
| **Description-first element targeting** | Matches against `textContent`, `aria-label`, `title`, `placeholder`, `alt`, `href` — ARIA-labelled elements are first-class targets |
| **Input finder via a11y attributes** | Checks `placeholder`, `aria-label`, `name`, `id`, `title`, falls back to `[role="searchbox"]` |
| **ARIA role-aware selectors** | Searches `[role="button"]`, `[role="link"]`, `[role="tab"]`, `[role="menuitem"]`, `[role="article"]`, `[role="textbox"]`, `[role="searchbox"]`, `[role="combobox"]` plus semantic HTML |
| **Semantic content extraction** | `read_selection` page mode extracts `<article>` / `[role="main"]` / `<main>`, strips nav, header, footer, aside, ads, cookie notices — designed for audio-first consumption |
| **Visual click feedback** | Purple cursor dot and element highlight with label for sighted users |

---

## 🔍 Built-in Accessibility Auditor (Overlay Page)

The `/overlay` page includes a client-side accessibility heuristic checker:

- Detects inputs missing accessible labels
- Flags buttons with generic text ("click", "submit", "ok")
- Warns about non-descriptive link text ("here", "read more")
- Checks for missing H1 heading
- Dedicated "Accessibility hints" tab with pass/fail indicators

---

## ✅ Implementation Status

All features listed above are **implemented in code** and can be verified by inspection.

| Feature | Status | Where |
|---------|--------|-------|
| Dual ARIA live regions (assertive + polite) | ✅ | `page.tsx` |
| Keyboard shortcuts (Q / W / Escape) | ✅ | `page.tsx` |
| Wake word detection ("Hey Spectra") | ✅ | `useVoiceActivation.ts` |
| Screen reader announcements (connect, disconnect, listening, actions) | ✅ | `page.tsx` |
| Skip-to-content link | ✅ | `layout.tsx` |
| Barge-in / interrupt | ✅ | Gemini VAD + frontend stop |
| Error recovery (reconnect with backoff) | ✅ | `useSpectraSocket.ts` |
| Focus management | ✅ | `layout.tsx` + `page.tsx` |
| `prefers-reduced-motion` support | ✅ | `globals.css` |
| 44px touch targets | ✅ | `globals.css` |
| High-contrast focus ring | ✅ | `globals.css` |
| Multilingual auto-match | ✅ | `system_instruction.py` + `core_instruction.txt` |
| Destructive action confirmation | ✅ | `system_instruction.py` + `core_instruction.txt` |
| Extension a11y-aware targeting | ✅ | `content.js` |
| Built-in accessibility auditor | ✅ | `overlay/page.tsx` |
| VoiceOver real-user test | 📋 Planned | Community testers welcome |
| NVDA real-user test | 📋 Planned | Community testers welcome |

---

## 🔮 Future Enhancements

- Text-only mode (disable audio, use screen reader only)
- Firefox support for Spectra Bridge extension
- Customisable voice and speech rate
- Haptic feedback for mobile users
- Voice training and accent adaptation
