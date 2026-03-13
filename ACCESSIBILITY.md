# Spectra Accessibility Features

Spectra is designed from the ground up for blind and visually impaired users.

## For Blind Users

### Starting Spectra (No Mouse Required)
- **Q key**: Press Q to start or stop Spectra
- **Voice activation**: Say "Hey Spectra", "Start Spectra", or "OK Spectra"
- **W key**: Press W to share your screen (after starting)
- **Escape key**: Press Escape to stop Spectra
- **Audio feedback**: Spectra announces "Spectra is ready. What can I help you with?" when connected
- **Screen reader compatible**: All controls have proper ARIA labels

### Screen Sharing Permission (Browser Limitation)
When you first start Spectra, the browser will ask for screen sharing permission. This dialog has limited accessibility:

**Keyboard Navigation:**
- **Tab**: Move between "Chrome Tab", "Window", "Entire Screen" options
- **Arrow keys**: Navigate through the list of available screens/windows
- **Enter**: Select the highlighted option and share
- **Escape**: Cancel the dialog

**Important Notes:**
- Screen readers may not fully announce all options in this browser dialog
- This is a browser limitation, not a Spectra issue
- **Recommended**: Select "Entire Screen" (usually the first option after tabbing)
- You only need to grant this permission once per session
- **Alternative**: You can use Spectra without screen sharing for voice-only interactions (just allow microphone)

### Using Spectra
1. Navigate to the page with your screen reader
2. Press Q, or say "Hey Spectra" to start
3. Allow screen sharing and microphone access when prompted (optional)
4. Say "Where am I?" to hear a description of your screen
5. Say "Click the blue button" or "Type 'hello world'" to interact
6. Press Q or Escape to stop

### Voice Commands
- **Navigation**: "Where am I?", "What's on screen?", "Read this page"
- **Actions**: "Click the [description]", "Type [text]", "Scroll down", "Press Enter"
- **Safety**: Spectra will ask for confirmation before destructive actions like "Delete this email"

### Audio Output
- Spectra uses Gemini's native audio (Aoede voice) — natural, clear speech
- Audio plays automatically through your speakers/headphones
- No conflict with screen readers (Spectra speaks, screen reader reads UI)

## Technical Accessibility Features

### ARIA Support
- `role="log"` on conversation history
- `role="status"` on connection indicators
- `aria-live="polite"` for status updates
- `aria-label` on all interactive elements
- Skip-to-content link for keyboard navigation

### Keyboard Navigation
- All controls accessible via Tab key
- Enter to activate buttons
- Escape to close dialogs
- Focus indicators visible for sighted keyboard users

### Screen Reader Compatibility
- Designed for VoiceOver (macOS), NVDA and JAWS (Windows)
- All interactive elements have `aria-label` attributes
- Live regions announce status changes without focus movement

## Implementation Status

These features are implemented in code and can be verified by inspection:

| Feature | Status | Where |
|---------|--------|-------|
| ARIA live regions (assertive + polite) | ✅ Implemented | `frontend/src/app/page.tsx` |
| Keyboard shortcuts (Q / W / Escape) | ✅ Implemented | `page.tsx` — `useEffect` key handler |
| Wake word detection ("Hey Spectra") | ✅ Implemented | `useVoiceActivation.ts` — Web Speech API |
| Screen reader audio announcements | ✅ Implemented | `announceAssertive()` / `announcePolite()` helpers |
| Skip-to-content link | ✅ Implemented | `layout.tsx` |
| Barge-in / interrupt | ✅ Implemented | Gemini VAD — frontend sends stop signal |
| Error recovery (reconnect) | ✅ Implemented | `useSpectraSocket.ts` — 15-attempt backoff |
| Focus management | ✅ Implemented | `layout.tsx` + `page.tsx` |
| VoiceOver real-user test | 📋 Planned | Community testers welcome |
| NVDA real-user test | 📋 Planned | Community testers welcome |

## Future Enhancements
- Text-only mode (disable audio, use screen reader only)
- Firefox support for Spectra Bridge extension
- Customisable voice and speech rate
