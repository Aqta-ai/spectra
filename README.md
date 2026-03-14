# Spectra 

> I got tired of reading. Tired of staring at screens. Tired of typing.
> So I built something that does it for me.

Spectra is a real-time AI agent that understands your screen, highlights what matters, and responds to your voice. It clicks, types, scrolls, and navigates, so you don't have to.

**Built for accessibility. Designed for everyone.**

[![Live App](https://img.shields.io/badge/LIVE_APP-spectra.aqta.ai-22c55e?style=for-the-badge)](https://spectra.aqta.ai)
[![Demo Video](https://img.shields.io/badge/DEMO_VIDEO-YouTube-ff0000?style=for-the-badge&logo=youtube&logoColor=white)](#)
[![Built With](https://img.shields.io/badge/BUILT_WITH-Gemini_Live_API-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/gemini-api/docs/live)
[![Google Cloud](https://img.shields.io/badge/GOOGLE_CLOUD-Cloud_Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)](https://cloud.google.com/run)
[![Python](https://img.shields.io/badge/PYTHON-FastAPI-3B82F6?style=for-the-badge&logo=python&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/NEXT.JS-14-111827?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)

---

Whether you're visually impaired, have RSI, multitasking or just want hands-free browsing, Spectra uses pure vision AI to understand and control any webpage.

**Your screen, your voice, your way.**

**[🚀 Live Demo](https://spectra.aqta.ai)** | **[▶️ Demo Video](#)** | **[Start Here](START_HERE.md)** | **[Quick Start](QUICKSTART.md)** | **[Accessibility](ACCESSIBILITY.md)** | **[Architecture](ARCHITECTURE.md)** | **[Troubleshooting](TROUBLESHOOTING.md)**

---

## Why only Gemini can do this

Every other AI browser agent uses a request–response loop: send a screenshot, wait for a text reply, parse it, act. That model has a floor , there's always a gap, always a turn boundary, always a moment where the AI is gone and you're waiting.

Gemini Live API eliminates that boundary entirely. `bidiGenerateContent` is a persistent bidirectional WebSocket: voice audio streams in continuously, Gemini's native audio streams back in real time, and tool calls (click, type, navigate) interleave with speech mid-conversation. The result is that Spectra *talks while it works* , it doesn't wait until it's finished clicking before responding. It sounds and feels like a person sitting next to you at a computer.

Three Gemini capabilities make this possible and aren't replicated anywhere else:

- **Native audio I/O** , no TTS/STT middleware; Gemini speaks directly with natural prosody and handles interruptions natively via Voice Activity Detection
- **Multimodal Live streaming** , screenshots and audio arrive in the same stream Gemini is already reasoning over; no separate vision API call, no round-trip
- **Thinking with suppressed chain-of-thought** , `gemini-2.5-flash-native-audio-latest` reasons internally via its thinking budget but we suppress emission of those thoughts (`include_thoughts=False`), so the model navigates complex multi-step tasks intelligently without leaking internal monologue to the audio stream

No other model family currently exposes all three in a single real-time API. That is why Spectra is built on Gemini.

---

## The Problem

2.2 billion people worldwide have a vision impairment. But here's the thing, even people with perfect vision are exhausted by screens.

### The Accessibility Gap

| Statistic | Source |
|-----------|--------|
| 2.2 billion people have vision impairment | WHO, 2023 |
| 43 million are blind | WHO, 2023 |
| 96% of top 1M websites have WCAG failures | WebAIM, 2024 |
| Average page has 50+ accessibility errors | WebAIM, 2024 |
| Only 3% of the web is accessible to screen readers | Estimated |
| Screen reader users spend 2–3x longer on tasks | Research studies |

We read for hours. We stare until our eyes burn. We type until our wrists ache. And traditional screen readers? They were built decades ago for a simpler web:

- **Rigid**, linear DOM reading; no understanding of layout, colours, or images
- **Fragile**, break on custom components and dynamic UIs
- **Passive**, they describe but never act; you still click everything yourself
- **Text-only**, they can't interpret visuals, charts, or screenshots

**The gap:** No tool lets you just talk to your screen and have AI both understand and act on what it sees.

---

## What Spectra Does

Spectra is a real-time AI agent that closes the loop between seeing and doing:

- **Sees**, continuously captures your screen via live stream
- **Understands**, Gemini vision interprets layout, text, images, buttons, colours
- **Listens**, you speak naturally: "Where am I?", "Read this article", "Click the blue button"
- **Acts**, executes real UI actions (click, scroll, type, press keys) in your browser
- **Speaks**, responds with natural Gemini audio in 30+ languages, interruptible at any time

No reading. No staring. No typing. Just talk.

### Example Interaction

This is a real end-to-end task a blind user would struggle with on any traditional screen reader:

```
You: "Hey Spectra , check my Gmail and read me any unread emails from today."

Spectra: "Navigating to Gmail now... You have three unread emails today.
          The first is from Sarah at 9:14am, subject: 'Team lunch Thursday'.
          She's asking if you can make it and suggests the Italian place on
          Grafton Street. The second is from your bank , a transaction alert
          for €42.50 at Tesco. The third is a GitHub notification."

You: "Reply to Sarah , tell her yes, Thursday works, see her at one."

Spectra: "Opening Sarah's email... clicking Reply... typing your message now...
          Done. I've typed 'Yes, Thursday works , see you at one!' Should I
          send it?"

You: "Send it."

Spectra: "Sent. Sarah will have your reply in a moment."
```

No mouse. No keyboard. No reading. A task that takes a sighted person 45 seconds, done by voice in under two minutes , on any website, without the site needing to support any accessibility standard.

---

## Technical Highlights

| Requirement | Status | Location |
|-------------|--------|----------|
| Gemini Live API (bidiGenerateContent) | ✅ | `backend/app/streaming/session.py` |
| Google GenAI SDK | ✅ | `backend/requirements.txt`, `google-genai>=1.14.0` |
| Google Cloud deployment (Cloud Run) | ✅ | `deploy.sh` · `infra/main.tf` |
| Multimodal: screenshot → action | ✅ | `frontend/src/hooks/useScreenCapture.ts` → `session.py` |
| Architecture diagram | ✅ | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| **Bonus:** Infrastructure-as-Code | ✅ | `infra/main.tf` (Terraform) · `deploy.sh` |
| **Bonus:** Test suite (325 backend + 61 frontend) | ✅ | `backend/tests/` · `frontend/tests/` |

**Cloud deployment proof:** see `.github/workflows/deploy.yml`, the `deploy-backend` job pushes to Cloud Run on every merge to `main`, with a health-check loop confirming the service is live.

---

## Performance Optimisations

Spectra has been optimised for speed and reliability:

| Optimization | Before | After | Impact |
|--------------|--------|-------|--------|
| Frame cooldown | 0.04s | 0.02s | 50% faster |
| Describe cache TTL | 8s | 3s | Fresher results |
| Typing delay | 30ms | 15ms | 50% faster |
| Scroll wait | 300ms | 150ms | 50% faster |
| Click delay | 10ms | 5ms | 50% faster |
| Extension probe | 2s/5s | 0.5s/1.5s | 60% faster |
| Vision concurrency | 3 → 2 | Fewer parallel calls | Lower per-call latency |

---

## 📊 By the Numbers

| Metric | Value |
|--------|-------|
| 🌍 People with vision impairment worldwide | 2.2 billion |
| ⚡ Voice-to-response latency | 200–500ms |
| 🎯 Element click accuracy | 95%+ |
| 📸 Screen capture rate | 2 frames/second |
| 🔊 Audio sample rate | 16kHz PCM mono (input) / 24kHz (output) |
| 🗣️ Languages supported (Gemini) | 30+ (Gemini native) |
| 💾 Data stored on disk | Zero , screenshots in RAM only |
| 📦 Lines of code | ~12,600 (source) |
| ⚙️ Dependencies | 10 (backend) + 11 (frontend) |
| 🐳 Docker image size | ~150MB |
| ☕ Coffees consumed | Lost count |

---

## 🎉 Fun Facts

- **Zero mouse clicks required** , 100% voice + keyboard controllable
- **Continuous mode available** , always-on listening, no wake word needed
- **1 screenshot = ~80KB** , JPEG frames, not video, saving 95% bandwidth
- **Barge-in works** , interrupt Spectra mid-sentence and she stops immediately
- **Wake word runs locally** , "Hey Spectra" detection never leaves your browser
- **Aoede voice** , named after the Greek muse of song (Google's choice, not ours)
- **Hardest bug** , WebSocket race conditions; 3 days to fix with single-reader pattern
- **Why "Spectra"?** , sees the full spectrum of your screen: colours, layout, text, images
- **Built in Dublin** 🇮🇪 , fuelled by Barry's Tea and determination

---

## 🤖 Agent Capabilities

Spectra's agent is optimised for speed and accuracy:

### Fast Response
- Optimised frame processing (0.02s cooldown vs 0.04s)
- Faster typing (15ms delay vs 30ms)
- Efficient vision calls with 3s describe-cache
- Sub-500ms voice-to-response latency

### Better Language Understanding
- Optimized system instruction for concise responses
- Clear action priority: describe → click → type → scroll → submit
- British English phrasing for natural conversation
- Decisive action without hesitation

### Reliable Actions
- **Click**: Move mouse first, then click for precision
- **Type**: Natural typing with 15ms delay, auto-submit on Enter
- **Scroll**: Smart scroll with context-aware amounts
- **Submit**: Auto-detects forms and submits with Enter or button click

### Tools
- `describe_screen` - See what's on screen
- `click_element(x, y, description)` - Click at coordinates
- `type_text(text, x, y)` - Type text (x,y optional for clicking first)
- `scroll_page(direction, amount)` - Scroll up/down
- `press_key(key)` - Press keyboard key
- `navigate(url)` - Go to URL

---

## 🏗️ Architecture

Spectra is split into a Next.js frontend and a FastAPI backend connected to [Gemini Live API](https://ai.google.dev/gemini-api/docs/live).

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (Visually Impaired)                 │
│    🎤 Voice In   🔊 Voice Out   ⌨️ Keyboard                     │
│   Wake word: "Hey Spectra" | Shortcuts: Q / W / Escape          │
└──────────────┬──────────────────────────┬───────────────────────┘
               │                          │
               ▼                          ▲
┌──────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js + React)                   │
│  • Voice activation (Web Speech API)                             │
│  • Screen capture (MediaStream)                                  │
│  • Action executor (click, type, scroll, press keys)             │
│  • WebSocket client (audio + control messages)                   │
└───────────────────┬───────────────────────────────┬──────────────┘
                    │                               │
                    ▼                               │
┌──────────────────────────────────────────────────────────────────┐
│              BACKEND (FastAPI on Cloud Run)                      │
│  • WebSocket bridge: Client ↔ Gemini Live API                    │
│  • Session manager for bidiGenerateContent                       │
│  • System instructions + tool declarations                       │
│                                                                  │
│  GEMINI LIVE API (gemini-2.5-flash-native-audio-latest)          │
│  • Real-time audio streaming (Aoede)                             │
│  • Vision over screenshots                                       │
│  • Function calling for UI actions                               │
│  • Voice Activity Detection + barge-in                           │
└──────────────────────────────────────────────────────────────────┘
```

**Tools and behaviours:**
- **Vision agent:** `describe_screen` – describes current UI, elements, and context
- **Navigator agent:** `click_element`, `scroll_page`, `type_text`, `press_key`
- **Safety agent:** `confirm_action` – confirmation before destructive actions

See `ARCHITECTURE.md` for deeper details.

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| AI Model | [Gemini 2.5 Flash](https://ai.google.dev/gemini-api) (native audio) | Multimodal vision + audio + function calling (30+ languages) |
| Real-time Comms | [Gemini Live API](https://ai.google.dev/gemini-api/docs/live) (bidiGenerateContent) | Bidirectional streaming audio + tool calls |
| Backend | FastAPI (Python) | Lightweight, async WebSockets, easy tooling |
| Frontend | Next.js 14 + TypeScript | Fast, accessible, PWA-ready |
| Voice Activation | Web Speech API | Wake words like "Hey Spectra" |
| Browser Actions | Browser APIs | Direct DOM manipulation (click, type, scroll) |
| Hosting | Google Cloud Run | First-class for Gemini / GCP apps |
| Audio | PCM 16kHz streaming | Low-latency mic/speaker via WebSocket |

---

## 📁 Project Structure

```
spectra/
├── backend/                    # FastAPI + Gemini Live API
│   ├── app/
│   │   ├── main.py             # FastAPI app + WebSocket endpoint
│   │   ├── agents/
│   │   │   └── orchestrator.py # System instructions + tools
│   │   ├── streaming/
│   │   │   └── session.py      # Gemini Live session manager
│   │   └── tools/
│   │       ├── browser.py      # Browser action tools (future)
│   │       └── screen.py       # Screenshot tools (future)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env                    # GOOGLE_API_KEY, GCP_PROJECT_ID
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Main UI (voice, convo, status)
│   │   │   └── layout.tsx      # Root layout (a11y-first, skip links)
│   │   ├── hooks/
│   │   │   ├── useSpectraSocket.ts  # WebSocket to backend
│   │   │   ├── useAudioStream.ts    # Mic capture (PCM 16kHz)
│   │   │   ├── useScreenCapture.ts  # Screen capture (JPEG)
│   │   │   └── useVoiceActivation.ts# Wake word detection
│   │   └── lib/
│   │       ├── actionExecutor.ts    # Execute click/type/scroll
│   │       └── audioPlayer.ts       # Play Gemini audio
│   ├── package.json
│   ├── next.config.mjs
│   └── Dockerfile
├── infra/
│   ├── main.tf                 # Terraform (Cloud Run, Service Account, IAM)
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
├── backend/tests/              # 17 backend test files (pytest)
├── ACCESSIBILITY.md
├── QUICKSTART.md
├── docker-compose.yml
└── README.md
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/Aqta-ai/spectra.git
cd spectra

# Authenticate with Google Cloud (Vertex AI)
gcloud auth application-default login

# Configure your project
cp backend/.env.example backend/.env
# Set GOOGLE_CLOUD_PROJECT=your-gcp-project-id in backend/.env

docker-compose up
```

Open **http://localhost:3000** → install the Chrome extension from `extension/` → press **Q** and start talking.

**Need more detail?** See [START_HERE.md](START_HERE.md) (5-min guide) or [QUICKSTART.md](QUICKSTART.md) (full setup with manual + Cloud Run options).

## ☁️ Cloud Deployment

One command deploys backend + frontend to Cloud Run with Vertex AI:

```bash
./deploy.sh analog-sum-485815-j3 europe-west1
```

This will:
- Enable required GCP APIs (Vertex AI, Cloud Run, Cloud Build)
- Create a `spectra-backend` service account with `roles/aiplatform.user`
- Deploy the FastAPI backend to Cloud Run (Vertex AI auth via service account ADC , no API key needed)
- Build and deploy the Next.js frontend via Cloud Build
- Wire CORS between frontend and backend

**Terraform (IaC):** See [infra/](infra/) for Terraform that provisions the same infrastructure:
```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # fill in your values
terraform init && terraform apply
```

---

## 🎮 Usage

Visit http://localhost:3000 (or your Cloud Run URL).

Press Q or say "Hey Spectra" to start.

Allow screen sharing and microphone when prompted.

Try: "Where am I?", "What's on screen?", "Click the blue button", "Type hello world".

Say "Stop" or "Cancel" to interrupt or halt actions.

### Voice Commands

- **"Where am I?"** – describe current screen
- **"What's on screen?"** – full description
- **"Click the [description]"** – click an element
- **"Type [text]"** – type into focused field
- **"Scroll down / up"** – scroll page
- **"Press Enter / Tab / Escape"** – key press
- **"Stop" / "Cancel"** – cancel current action

### Keyboard Shortcuts

- **Q** – start/stop Spectra
- **W** – share screen
- **Escape** – stop Spectra
- **Tab** – navigate controls

### Wake Words

- **"Hey Spectra"**
- **"Start Spectra"**
- **"OK Spectra"**

---

## 🔒 Safety, Ethics & Privacy

- **Confirmation before destructive actions** – "Are you sure you want to delete this?"
- **Nothing touches disk. Nothing persists.** – Screenshots are held as a single variable in the backend session; each new frame replaces the last. Named snapshots live in an in-memory dictionary, lost on restart. No files, no database, no cloud storage.
- **Gemini API is the only external service** – Screen frames are sent to [Google's Gemini API](https://ai.google.dev/gemini-api) for vision analysis. No other third-party services access your data.
- **No user accounts, no tracking, no analytics** – Self-hosters bring their own API key.
- **User always in control** – "Stop" / "Cancel" at any time
- **No passwords** – Spectra avoids interacting with password/auth fields
- **Open source** – Apache 2.0 for transparency and community audit

---

## 🔧 Troubleshooting (Common Issues)

- **Backend won't start:** check Python version, virtualenv, `GOOGLE_API_KEY` in `.env`, port 8080 availability.
- **"No module named 'app'":** you're not in `backend/` when running `uvicorn`.
- **Frontend won't start:** check Node 20+, `npm install`, `NEXT_PUBLIC_WS_URL`.
- **Voice activation not working:** check browser (Chrome/Edge), mic permissions, try keyboard shortcuts.
- **Screen sharing denied:** Spectra still works in text-only mode.

See `TROUBLESHOOTING.md` for full list.

---

## 🧩 Spectra Bridge, Chrome Extension

Spectra uses **Spectra Bridge**, a companion Chrome extension that executes actions (click, type, scroll, navigate) on any webpage on your behalf.

### Install Spectra Bridge

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle, top right)
3. Click **Load unpacked**
4. Select the `extension/` folder from this repo

Spectra Bridge will appear in your toolbar. You only need to do this once, Chrome remembers it across restarts.

### How Spectra Bridge works

- `content.js`, injected into every tab; listens for action messages from Spectra and executes them (click, type, scroll, key press, navigate). Also signals back to the Spectra page with the result.
- `background.js`, service worker that routes messages from the Spectra frontend tab to whichever tab you're currently working in.

### Actions supported

| Action | What it does |
|--------|-------------|
| `click` | Clicks element at (x, y) with purple highlight overlay |
| `type` | Types text into the focused input or contentEditable |
| `scroll` | Scrolls the page up or down |
| `key` | Presses a key (Enter, Tab, Escape, etc.) |
| `navigate` | Navigates the tab to a URL |

### Updating Spectra Bridge

If you change any files in `extension/`, go to `chrome://extensions/` and click the refresh icon on the Spectra Bridge card.

---

## 🤝 Contributing

Spectra is open source and built for the accessibility community.

**Ways to contribute:**
- Report bugs and suggest features
- Improve docs and accessibility
- Add new capabilities (e.g., app-specific workflows)
- Test with screen readers and real users
- Translate to other languages

See `CONTRIBUTING.md` for details.

---

## ⚠️ Disclaimer

**Spectra is an experimental research project and proof-of-concept.**

- **Not a certified medical device**, not certified or approved by any regulatory authority (FDA, CE, MHRA, etc.)
- **Not a replacement for professional assistive technology**, this is a research prototype, not a substitute for certified screen readers
- **Use at your own risk**, provided "as is" without warranties of any kind (Apache 2.0)

**If you rely on assistive technology for daily tasks, please continue using your certified tools.** Spectra is intended as a complementary experimental tool for exploration and research.

---

## 📄 License

Apache License 2.0 – see [LICENSE](LICENSE).

---

## 🙏 Acknowledgments

Spectra is built on the shoulders of giants:

- **Google Gemini**, The 2.5 Flash model with native audio and vision capabilities makes this possible
- **Gemini Live API**, Real-time bidirectional streaming enables natural conversation
- **Web Speech API**, Browser-native wake word detection
- **Open Source Community**, Inspiration from accessibility tools and AI agents

Built for #GeminiLiveAgentChallenge

---

## 📞 Maintainer

**Anya Chueayen**, Aqta Technologies Ltd, Dublin, Ireland

---

**Star ⭐ this repo if you find it helpful!**

**Share with others who might benefit from accessible tools.**