# Architecture

Spectra is a real-time AI screen assistant built for the Google Gemini Live Agent Challenge. It uses Gemini's native multimodal capabilities to see, understand, and interact with any screen, enabling hands-free navigation for visually impaired users, people with motor disabilities, and anyone who wants to control their computer by voice.

## System Overview

### Interactive Architecture Diagram

```mermaid
graph TB
    %% User Layer
    User[👤 User<br/>🎤 Voice + 🔊 Audio + ⌨️ Keyboard<br/>Wake: 'Hey Spectra' | Q/W/Esc]

    %% Frontend Layer
    subgraph Frontend["🌐 Frontend (Next.js + React)"]
        VoiceAct[🎤 Voice Activation<br/>Web Speech API]
        ScreenCap[📸 Screen Capture<br/>MediaStream API<br/>2fps JPEG @ 1280px]
        ActionExec[⚡ Action Executor<br/>click/type/scroll/keys]
        WSClient[🔌 WebSocket Client<br/>Audio + Control Messages]
        AudioPlayer[🔊 Audio Player<br/>PCM Playback]
    end

    %% Extension Bridge
    subgraph Extension["🔗 Spectra Bridge (Chrome Extension)"]
        ContentJS[content.js<br/>Execute actions in target tab]
        BackgroundJS[background.js<br/>Route messages between tabs]
        ExtActions[🎯 Actions:<br/>click, type, scroll, key, navigate]
    end

    %% Backend Layer
    subgraph Backend["⚙️ Backend (FastAPI on Cloud Run)"]
        WSServer[🔌 WebSocket Server<br/>Client ↔ Gemini Bridge]
        SessionMgr[📋 Session Manager<br/>SpectraStreamingSession]
        ToolRouter[🛠️ Tool Router<br/>Server vs Client tools]
        Personalisation[👤 User Preferences<br/>Workflows & History]
    end

    %% Gemini Live API
    subgraph GeminiAPI["🤖 Gemini Live API"]
        LiveModel[gemini-2.5-flash<br/>native audio]
        AudioStream[🎵 Real-time Audio<br/>Aoede Voice + VAD]
        VisionAnalysis[👁️ Vision Analysis<br/>Screenshot Understanding]
        FunctionCalls[⚙️ Function Calling<br/>UI Action Tools]
    end

    %% Tool Categories
    subgraph ServerTools["🖥️ Server-side Tools"]
        DescribeScreen[describe_screen<br/>Analyse UI elements]
        SaveSnapshot[save_snapshot<br/>Reference screenshots]
        DiffScreen[diff_screen<br/>Compare changes]
        TeachApp[teach_me_app<br/>Guided tours]
    end

    subgraph ClientTools["💻 Client-side Tools"]
        ClickElement[click_element<br/>Click at coordinates]
        TypeText[type_text<br/>Input text]
        ScrollPage[scroll_page<br/>Navigate content]
        PressKey[press_key<br/>Keyboard actions]
        Navigate[navigate<br/>Go to URL]
    end

    %% Data Flow Connections
    User -.->|Voice Input| VoiceAct
    User -.->|Keyboard| ActionExec
    VoiceAct -->|Wake Detection| WSClient
    ScreenCap -->|JPEG Frames| WSClient
    WSClient <-->|WebSocket| WSServer
    AudioPlayer <-.->|Audio Output| User

    WSServer <-->|Streaming| SessionMgr
    SessionMgr <-->|bidiGenerateContent| LiveModel
    SessionMgr --> ToolRouter
    SessionMgr --> Memory

    ToolRouter -->|Server Tools| ServerTools
    ToolRouter -->|Client Tools| WSClient
    WSClient -->|postMessage| BackgroundJS
    BackgroundJS -->|Route to Tab| ContentJS
    ContentJS -->|Execute| ExtActions
    ContentJS -.->|Results| BackgroundJS
    BackgroundJS -.->|Results| WSClient

    LiveModel --> AudioStream
    LiveModel --> VisionAnalysis
    LiveModel --> FunctionCalls

    %% Styling
    classDef userStyle fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef frontendStyle fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef backendStyle fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef geminiStyle fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef toolStyle fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef extensionStyle fill:#e0f2f1,stroke:#004d40,stroke-width:2px

    class User userStyle
    class Frontend,VoiceAct,ScreenCap,ActionExec,WSClient,AudioPlayer frontendStyle
    class Backend,WSServer,SessionMgr,ToolRouter,Memory backendStyle
    class GeminiAPI,LiveModel,AudioStream,VisionAnalysis,FunctionCalls geminiStyle
    class ServerTools,ClientTools,DescribeScreen,SaveSnapshot,DiffScreen,TeachApp,ClickElement,TypeText,ScrollPage,PressKey,Navigate toolStyle
    class Extension,ContentJS,BackgroundJS,ExtActions extensionStyle
```

### ASCII Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER                                            │
│                    Voice + Screen Share + Keyboard                           │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                                   │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Screen       │  │ Audio        │  │ WebSocket    │  │ Action       │    │
│  │ Capture      │  │ Stream       │  │ Client       │  │ Executor     │    │
│  │ (2 fps JPEG) │  │ (16kHz PCM)  │  │              │  │              │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         └─────────────────┴────────┬─────────┴─────────────────┘            │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │ WebSocket
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                                    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    SpectraStreamingSession                           │    │
│  │                                                                      │    │
│  │  • Bridges client ↔ Gemini Live API                                  │    │
│  │  • Routes tool calls (server-side vs client-side)                    │    │
│  │  • Handles barge-in and cancellation                                 │    │
│  │  • Manages screen snapshots for diff comparison                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │ Gemini Live API
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GEMINI LIVE API (bidiGenerateContent)                     │
│                                                                              │
│  Model: gemini-2.5-flash (native audio)                                       │
│  • Native audio input/output (Aoede voice)                                   │
│  • Real-time vision analysis of screenshots                                  │
│  • Function calling for UI actions                                           │
│  • Voice Activity Detection + barge-in support                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SPECTRA BRIDGE (Chrome Extension)                         │
│                                                                              │
│  • Executes UI actions in the target tab                                     │
│  • Visual feedback: cursor, ripple, element highlight                        │
│  • Description-first element finding (more reliable than coordinates)        │
│  • Coordinate scaling from screenshot space to viewport                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Agent Loop

Spectra runs a continuous observe-think-plan-act loop:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT LOOP                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. OBSERVE                                                                  │
│     • Screen frames (JPEG @ 2 fps via getDisplayMedia)                       │
│     • User audio (PCM 16kHz stream)                                          │
│     • Previous action results                                                │
│                                                                              │
│  2. THINK                                                                    │
│     • Parse user intent from speech                                          │
│     • Analyse visible UI elements, layout, text, buttons                     │
│     • Identify relevant elements for the task                                │
│                                                                              │
│  3. PLAN                                                                     │
│     • Select appropriate tool call                                           │
│     • Generate coordinates + description for clicks                          │
│     • Announce action before executing                                       │
│                                                                              │
│  4. ACT                                                                      │
│     • Server-side: describe_screen, save_snapshot, diff_screen               │
│     • Client-side: click, type, scroll, key, navigate                        │
│     • Re-capture screen to verify result                                     │
│                                                                              │
│  → Loop back to OBSERVE                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Voice Conversation
```
User speaks → Mic (PCM 16kHz) → Frontend → WebSocket → Backend → Gemini Live API
                                                                        │
User hears  ← Speaker ← AudioPlayer ← Frontend ← WebSocket ← Backend ←──┘
```

### Screen Understanding
```
Screen → getDisplayMedia → JPEG (1280px max) → WebSocket → Backend → Gemini Vision
```

### UI Actions
```
Gemini tool call → Backend → WebSocket → Frontend → Extension Bridge → Target Tab
                                                                           │
Gemini receives  ← Backend ← WebSocket ← Frontend ← action_result ←────────┘
```

## Tools

| Tool | Location | Description |
|------|----------|-------------|
| `describe_screen` | Server | Analyse and describe visible screen content |
| `click_element` | Client | Click at coordinates with element description |
| `type_text` | Client | Type text, optionally click field first |
| `scroll_page` | Client | Scroll up or down |
| `press_key` | Client | Press keyboard key (Enter, Tab, Escape, etc.) |
| `navigate` | Client | Navigate browser to URL |
| `confirm_action` | Server | Ask user confirmation before destructive actions (planned, not yet implemented) |
| `save_snapshot` | Server | Save current screen as named reference |
| `diff_screen` | Server | Compare current screen to saved snapshot |
| `teach_me_app` | Server | Guided tour of current application |

## Hallucination Prevention

1. **Visual confirmation only** — The model must see the current screenshot before clicking. No acting on elements not visually identified.

2. **Description-first element finding** — The extension prioritises matching by text/aria-label over raw coordinates, since vision model coordinates are approximate.

3. **Fallback on failure** — If element not found: scroll, re-describe, retry. If still not found, admit uncertainty.

4. **No blind clicks** — `click_element` requires x, y, and description. Coordinates come from vision analysis.

## Error Recovery

| Scenario | Response |
|----------|----------|
| Element not visible | Scroll, re-describe, retry |
| Wrong page / layout changed | Describe current screen, inform user |
| Form validation errors | Describe errors, fix one field at a time |
| User says "stop" | Immediately halt, acknowledge, listen |
| Client cancel | Abort pending action, return `cancelled_by_user` |

## WebSocket Protocol

### Client → Server
```json
{ "type": "audio", "data": "<base64 PCM>" }
{ "type": "screenshot", "data": "<base64 JPEG>", "width": 1280, "height": 720 }
{ "type": "text", "data": "user message" }
{ "type": "action_result", "result": "clicked: Submit", "id": "abc123" }
{ "type": "cancel" }
{ "type": "pong" }
```

### Server → Client
```json
{ "type": "audio", "data": "<base64 PCM>" }
{ "type": "text", "data": "assistant response" }
{ "type": "transcript", "data": "user speech transcript" }
{ "type": "action", "action": "click", "params": {...}, "id": "abc123" }
{ "type": "turn_complete" }
{ "type": "heartbeat", "uptime": 45.2 }
{ "type": "usage_limit", "tier": "free", "used": 300, "limit": 300 }
```

## Extension Architecture

The Spectra Bridge extension runs in two contexts:

1. **Spectra page** — Listens for `postMessage` from frontend, forwards to background script
2. **Target tab** — Receives actions from background, executes clicks/types/scrolls

### Element Finding Strategy
```
1. Search by description text (aria-label, title, textContent)
2. Try elementFromPoint at scaled coordinates
3. Search nearby interactive elements by proximity
4. Walk up DOM for clickable ancestor
5. Find closest interactive element within radius
```

### Coordinate Scaling
Screenshots are captured at up to 1280×720. The extension scales coordinates from screenshot space to viewport space, accounting for browser chrome when sharing window/screen.

## GCP Services

| Service | Purpose |
|---------|---------|
| Cloud Run | Host backend (FastAPI + WebSocket) |
| Artifact Registry | Container images |
| Secret Manager | API keys |

### Cloud Run — Spectra Backend
```yaml
Service: spectra-backend
Region: europe-west1
CPU: 2 vCPU
Memory: 1 GiB
Concurrency: 20
Session Affinity: true
Min Instances: 1
Max Instances: 10
Timeout: 3600s
```

## Scalability & Performance

- **Response Time**: Sub-second (real-time streaming)
- **Concurrent Users**: 100+ supported
- **Horizontal scaling**: Auto-scaling Cloud Run instances
- **Geographic**: Multi-region deployment ready

## Security & Privacy

- **Encryption**: All data encrypted in transit and at rest
- **Privacy**: Screen captures processed in-session, not stored
- **Authentication**: Secure session management via `secrets.token_hex`
- **IAM**: Principle of least privilege
- **API Keys**: Managed via Secret Manager
- **Network**: VPC and firewall protection

## Key Design Principles

- **Single agent loop** — Observe → Think → Plan → Act, repeat
- **Interruptible** — User can say "stop" or click Stop at any time
- **Grounded** — Agent announces actions before executing; visual highlights show targets
- **Accessibility-first** — Voice activation, keyboard shortcuts, screen reader compatible
- **Transparent** — Powered by Google Gemini, built by the Spectra team

## Competitive Advantages

### vs. Generic AI Agents
- Actually controls browsers with pixel precision
- Sees and understands visual interfaces
- Handles interruptions naturally

### vs. Browser Automation
- Natural language control instead of rigid scripting
- Adapts to UI changes in real-time
- Accessibility-focused design

### vs. Accessibility Tools
- Full AI navigation beyond screen readers
- Universal compatibility with any website
- Personalised experience that learns and improves
