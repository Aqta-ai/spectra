# Spectra Offline Mode (Gemma 4)

## Overview

Spectra now supports **fully offline operation** using Ollama and Gemma 4, a 9B parameter language model. This enables:

- ✓ No API keys required
- ✓ Private local processing (no data sent to external services)
- ✓ Full browser control and accessibility features
- ✓ Real-time conversational interaction

## Architecture

### Provider Routing

Spectra can operate in two modes, selected via the `SPECTRA_PROVIDER` environment variable:

| Provider | Model | Latency | Quality | Fallback |
|----------|-------|---------|---------|----------|
| `gemini` | Gemini 2.5 Flash (cloud) | 1-2s | 9/10 | Primary |
| `ollama` | Gemma 4 (local) | 2-4s | 7/10 | Offline |

### Components

**Backend (Python/FastAPI):**
- `app/streaming/ollama_client.py` — HTTP client for Ollama `/api/generate` endpoint with streaming
- `app/streaming/ollama_session.py` — WebSocket session handler compatible with frontend
- `main.py` — Provider routing in `/ws` endpoint

**Frontend (TypeScript/React):**
- Provider toggle button ("Cloud" ↔ "Local") in header
- Automatic provider detection via `/api/system-info` on mount
- Dynamic provider switching via `/api/switch-provider` POST endpoint

## Setup

### Prerequisites

- **Ollama:** Download from [ollama.com](https://ollama.com)
- **Gemma 4:** `ollama pull gemma4` (9.6GB, requires 12GB+ VRAM)
- **Backend:** Python 3.11+, FastAPI

### 1. Install Ollama

```bash
# macOS / Linux / Windows
# Visit https://ollama.com and download the installer

# Or build from source
git clone https://github.com/ollama/ollama.git
cd ollama && make
```

### 2. Download Gemma 4

```bash
ollama pull gemma4
# Downloads ~9.6GB
# Models stored in ~/.ollama/models/
```

### 3. Run Ollama Server

```bash
ollama serve
# Listening on http://127.0.0.1:11434
```

### 4. Configure Backend

Edit `backend/.env`:

```bash
SPECTRA_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4
```

### 5. Start Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### 6. Start Frontend

```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:3000
```

## Usage

### Switching Providers

**Via Frontend UI:**
1. Open Spectra in browser
2. Look for "Cloud" or "Local" button in header (top-right)
3. Click to toggle between Gemini and Ollama
4. Browser automatically reconnects to new provider

**Via API:**
```bash
# Check current provider
curl http://localhost:8000/api/system-info

# Switch to Ollama
curl -X POST http://localhost:8000/api/switch-provider \
  -H "Content-Type: application/json" \
  -d '{"new_provider": "ollama"}'

# Switch back to Gemini
curl -X POST http://localhost:8000/api/switch-provider \
  -H "Content-Type: application/json" \
  -d '{"new_provider": "gemini"}'
```

**Via Environment Variable:**
```bash
export SPECTRA_PROVIDER=ollama
python -m uvicorn app.main:app --port 8000
```

### Example Conversation

**You:** "Navigate to google.com"
- Gemini: ~1.5s latency, responds with natural language context
- Ollama: ~3-4s latency, same functionality

**You:** "Click the search box and type hello world"
- Both providers execute the click and type actions
- Response: "I've typed 'hello world' into the search box"

**You:** "What's on screen?"
- Describes visible content using browser's accessibility API
- Works identically on both providers

## Performance

### Latency Comparison

```
Gemini (Cloud):    ~1s first token
Ollama (Local):    ~2-4s first token

Throughput:
Gemini:    60-100 tokens/sec (limited by API streaming)
Ollama:    30-50 tokens/sec (CPU/GPU dependent)
```

### Hardware Requirements

**Ollama + Gemma 4:**
- **CPU:** Intel i7 / Apple M1+ / Ryzen 5+ (at least 4 cores)
- **RAM:** 12GB minimum, 16GB+ recommended
- **GPU (optional):** Nvidia CUDA (2GB+ VRAM) or Apple Metal

**Testing Machine (used during development):**
- Apple M2 Pro (8-core GPU)
- 16GB unified memory
- ~3-4s latency in real conversations

## Architecture Details

### Message Flow (Ollama Mode)

```
User → Browser → WebSocket → Backend → Ollama
  ↓                           ↓
Speech-to-Text          Prompt + History
(Browser Web Speech API)  (via HTTP /api/generate)
                          ↓
                       Streaming chunks
                          ↓
Backend Response Stream → Browser → Text-to-Speech
                                   (Browser TTS API)
```

### Tool Execution

Both Gemini and Ollama can call browser control tools:

- `describe_screen` — Get accessible content
- `click_element` — Click buttons, links, etc.
- `type_text` — Fill form fields
- `scroll_page` — Scroll up/down
- `press_key` — Send keyboard input (Enter, Tab, etc.)
- `navigate` — Go to new URL
- `wait_for_content` — Wait for page update
- And 6 more...

Text-only Ollama mode sends tool results as text context back to the model, enabling multi-turn reasoning.

## Troubleshooting

### "Cannot connect to Ollama"

```
Error: Failed to connect to Ollama at http://127.0.0.1:11434
```

**Solution:**
```bash
# Check if Ollama is running
ollama serve

# Or specify custom URL in .env
OLLAMA_BASE_URL=http://192.168.1.100:11434
```

### "Model not found"

```
Error: Model gemma4 not found
```

**Solution:**
```bash
ollama pull gemma4
```

### "Out of memory"

```
Error: CUDA out of memory / VRAM exhausted
```

**Solution:**
- Close other GPU applications
- Reduce model size: `ollama pull gemma2` (7B, faster)
- Increase system RAM or swap

### "Ollama responses are slow"

**Expected behavior:** 2-4s latency is normal for Gemma 4 on consumer hardware.

**If slower:**
- Check CPU usage: `top` or Activity Monitor
- Close background apps
- Check Ollama logs: `ollama serve` (verbose output)
- Try smaller model: `ollama pull phi2` (2.7B, very fast)

### "Provider toggle not working"

```bash
# Verify backend is responding
curl http://localhost:8000/api/system-info

# Check .env file is readable
cat backend/.env

# Restart backend after .env changes
pkill -f uvicorn
python -m uvicorn app.main:app --port 8000
```

## Deployment

### Local Development

Already configured in this repo. Just run:

```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: Backend
cd backend && python -m uvicorn app.main:app --port 8000

# Terminal 3: Frontend
cd frontend && npm run dev
```

### Docker (Offline Mode)

Build and run with Docker Compose (requires Ollama host):

```bash
# Update docker-compose.yml for your Ollama URL
# Then:
docker-compose up

# Frontend: http://localhost:3000
# Backend: http://localhost:8080/health
```

### Cloud Deployment (Gemini Only)

For production without Ollama:

```bash
# Cloud Run / Vercel / etc.
# Set SPECTRA_PROVIDER=gemini (default)
# Provide GOOGLE_CLOUD_PROJECT or GOOGLE_API_KEY
# Deploy as usual
```

## Switching to Offline for Production

To deploy spectra.aqta.ai with offline capability:

1. **Install Ollama** on your server
2. **Download Gemma 4:** `ollama pull gemma4`
3. **Set environment variable:**
   ```bash
   export SPECTRA_PROVIDER=ollama
   export OLLAMA_BASE_URL=http://localhost:11434
   ```
4. **Start Ollama:** `ollama serve` (systemd/supervisor for auto-restart)
5. **Deploy backend & frontend** as usual

## Limitations (Text-Only Mode)

Current Ollama implementation is **text-only**:

- ✓ Browser control (click, type, navigate, etc.)
- ✓ Conversational responses
- ✓ Screen content reading
- ✗ Native audio streaming (no microphone input)
- ✗ Voice output (would require external TTS)

**Workaround:** Use browser's Web Speech API for STT/TTS on the frontend while keeping backend text-only.

## Future Enhancements

1. **Full-duplex audio:** Add Whisper STT + local TTS (Piper/Coqui)
2. **Faster models:** Support phi2, mistral, neural-chat (streaming trade-offs)
3. **GPU optimization:** CUDA, ROCm, Metal quantized models
4. **Multi-modal:** Integrate vision models for screenshot analysis

## References & Credits

- **[Ollama](https://github.com/ollama/ollama)** — Local LLM inference engine
- **[Gemma Models](https://huggingface.co/google/gemma)** — Google's open-source language models
- **[Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)** — Browser native speech recognition and synthesis
- **[FastAPI](https://fastapi.tiangolo.com)** — Modern Python web framework for building APIs
