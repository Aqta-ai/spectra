# Quick Start - Offline Mode (Gemma 4)

## 5-Minute Setup

### 1. Install Ollama
```bash
# macOS
brew install ollama
# or download from https://ollama.com

# Linux
curl https://ollama.ai/install.sh | sh

# Windows
Download from https://ollama.com
```

### 2. Download Gemma 4
```bash
ollama pull gemma4
# Takes 5-10 minutes (9.6GB download)
```

### 3. Start Ollama
```bash
ollama serve
# Server runs on http://127.0.0.1:11434
```

### 4. Terminal 2 - Start Backend
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 5. Terminal 3 - Start Frontend
```bash
cd frontend
npm run dev
# Opens http://localhost:3000
```

### 6. Test It
- Open http://localhost:3000 in browser
- Look for "Local" button in top-right (shows offline mode is available)
- Click button to switch between "Cloud" (Gemini) and "Local" (Ollama)
- **Type a message to test** (text-only mode, no voice yet)
- See response from Gemma 4 in 2-4 seconds

## Testing Checklist

Quick tests to verify everything works:

```bash
# 1. Check backend is running
curl http://localhost:8000/health

# 2. Check provider detection
curl http://localhost:8000/api/system-info

# 3. Switch to Ollama
curl -X POST http://localhost:8000/api/switch-provider \
  -H "Content-Type: application/json" \
  -d '{"new_provider": "ollama"}'

# 4. Verify switch
curl http://localhost:8000/api/system-info

# 5. Switch back to Gemini
curl -X POST http://localhost:8000/api/switch-provider \
  -H "Content-Type: application/json" \
  -d '{"new_provider": "gemini"}'
```

## What to Expect

### Ollama Mode (Local) - TEXT + BROWSER TTS
- **Speed:** 2-4 seconds to first response
- **Input:** Type messages (voice input planned for Phase 2)
- **Output:** Text responses with browser text-to-speech
- **TTS Quality:** Uses system voices (functional but robotic; local high-quality TTS planned for Phase 2)
- **Internet:** None required
- **API Key:** Not needed
- **Privacy:** All processing local
- **Note:** Phase 2 will add Whisper STT + Piper TTS for natural voice I/O

### Gemini Mode (Cloud) - FULL FEATURES
- **Speed:** 1-2 seconds to first response
- **Input:** Voice or text
- **Output:** Voice and text
- **Internet:** Required
- **API Key:** Needed (set via env var)
- **Privacy:** Requests sent to Google

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to Ollama" | Make sure `ollama serve` is running in Terminal 1 |
| "Model not found" | Run `ollama pull gemma4` |
| "Out of memory" | Your system needs 12GB+ RAM. Close other apps. |
| "Provider toggle doesn't work" | Restart backend: `python -m uvicorn app.main:app --port 8000` |
| "Slow responses from Ollama" | Normal on CPU-only. 2-4s is expected. |
| "No voice output" | Offline mode is text-only. Use Cloud mode for voice. |
| "Can't use microphone" | Offline mode accepts typed text. Voice input is Phase 2. |

## Example Conversation

**You:** "Who are you?"
**Ollama:** "I'm Spectra, an AI accessibility assistant..."

**You:** "Navigate to google.com"
**Ollama:** "I've navigated to Google. What would you like to search for?"

**You:** "Click the search box"
**Ollama:** "Done. You can now type your search query."

## Files to Know

- `backend/.env` — Provider configuration
- `OFFLINE_MODE.md` — Full documentation
- `DEPLOYMENT_CHECKLIST.md` — Production setup

## Performance on Different Hardware

| Hardware | Latency | Viable |
|----------|---------|--------|
| M1/M2 Mac | 2-3s | ✓ Excellent |
| Ryzen 5 | 3-4s | ✓ Good |
| i5 / i7 | 3-5s | ✓ Good |
| CPU-only | 10-30s | ✓ Works but slow |

## Next Steps

1. Test locally with this guide
2. Try both providers (click toggle button)
3. Read `OFFLINE_MODE.md` for advanced setup
4. Deploy to production when ready

---

## Credits

- **[Ollama](https://github.com/ollama/ollama)** — Local LLM engine
- **[Gemma](https://huggingface.co/google/gemma)** — Open-source models by Google
- **[FastAPI](https://fastapi.tiangolo.com)** — Python web framework
- **[Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)** — Browser speech APIs

**Questions?** See `OFFLINE_MODE.md` for complete documentation.
