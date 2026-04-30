# Security policy and distribution scope

## Reporting a security issue

If you find a vulnerability in the code published in this repository (the Spectra frontend, backend, the Spectra Bridge Chrome extension, or any of the supporting scripts), please **do not file a public GitHub issue.** Instead, email <security@aqta.ai> with:

- A description of the issue
- Steps to reproduce
- The version / commit you tested against
- Your name and contact information so we can credit your disclosure if you wish

We aim to acknowledge reports within 5 working days and to provide a timeline for remediation within 14 days. We do not currently run a paid bug-bounty programme; responsible disclosures will be acknowledged in release notes.

If the issue concerns the **live application** at <https://spectra.aqta.ai>, the **production WebSocket endpoint**, or the **Spectra Bridge** browser extension as distributed by Aqta Technologies, please flag clearly so we can prioritise.

## Threat model

Spectra is a voice-first browser agent. The components most relevant to security are:

- **Screen capture** — frames stream from the user's browser to the Gemini Live API while a session is active. Frames are JPEG-compressed and transmitted over WSS/TLS. They are not stored on any server, but they may contain sensitive content (passwords, private documents, personal data) depending on what the user has on screen.
- **Voice audio** — PCM 16 kHz audio streams to the Gemini Live API while the user is speaking. Same transit and storage guarantees as screen frames.
- **Browser control** — the Spectra Bridge Chrome extension can click, type, scroll, and navigate on behalf of the user. It connects only to the Spectra backend and only when the user starts a session.
- **API credentials** — `GOOGLE_API_KEY` (or Vertex AI `GOOGLE_CLOUD_PROJECT` credentials) are required by the backend to reach the Gemini Live API. These are server-side only and never exposed to the frontend or extension.

Reasonable threats to report include: WebSocket session hijacking, prompt-injection escapes that cause the agent to act outside the user's intent, credential leakage through error messages or logs, extension permission escalation, and cross-origin request abuse.

## What's in scope of this repository

The code in this repository is the **public open-source release** of Spectra. It is licensed under Apache 2.0. You may inspect it, fork it, cite it, and reuse it under the terms of the licence. Specifically the following are open:

- `frontend/` — Next.js 14 application (landing page, guide, privacy, overlay accessibility analyser)
- `backend/app/` — FastAPI WebSocket server, Gemini Live session orchestration, agent toolset (click, type, scroll, navigate, describe, snapshot, diff)
- `backend/app/agents/` — system instructions, prompt templates, narration filtering, action validation
- `backend/app/overlay/` — page analysis backend that powers `/overlay`
- `backend/tests/` — unit and integration tests covering core logic
- `spectra-bridge/` — the Chrome extension source (manifest, background service worker, content scripts)
- `Dockerfile`, `run.sh`, `deploy-production.sh` — local-development and deployment scripts
- `ARCHITECTURE.md`, `OFFLINE_MODE.md`, `CONTRIBUTING.md`, `PRIVACY.md` — documentation

## What's NOT in scope of this repository

The following components of the Spectra platform are **not** distributed here and are not part of the open release:

| Component | Why it's closed | Path to access |
|---|---|---|
| **Production API keys and credentials** (`GOOGLE_API_KEY`, Vertex AI service-account JSON) | Operational secrets; supply your own when self-hosting | Provision your own via Google AI Studio or Google Cloud |
| **Production Cloud Run configuration** (custom domain, IAP, IAM bindings, secret-manager wiring) | Operational security boundary | Closed |
| **Internal monitoring and analytics** | Operational telemetry | Closed |
| **Hosted-version infrastructure as code** (Terraform, deployment scripts specific to Aqta's GCP project) | Operational security boundary | Closed |
| **Spectra Bridge published listing on the Chrome Web Store** (when published) | Distribution requires Aqta's developer account | Use the source in this repo via Load unpacked, or wait for the Web Store listing |
| **Internal pitch material, grant applications, business strategy documents** | Commercial-confidential | Closed |

## What the live hosted version does and doesn't do

`spectra.aqta.ai` runs the same code published here, configured against Aqta's `GOOGLE_API_KEY`. The hosted version:

- **Streams** screen frames and audio to the Gemini Live API only while a session is active
- **Does not store** frames, audio, transcripts, or chat history server-side
- **Does not run** any analytics, tracking pixels, or third-party data collection
- **Does not require** an account or sign-up
- **Does not have** the local Gemma 4 / Ollama offline pipeline available; that requires running Spectra on your own machine

Full details in [PRIVACY.md](PRIVACY.md).

## If you want to use Spectra in research, accessibility audits, or partnerships

- **For self-hosted use** (institutions that need Spectra on their own infrastructure for compliance): clone this repo, follow the Quick Start, supply your own Google API key. No partnership needed.
- **For accessibility audit work** at scale (e.g. EU Accessibility Act compliance audits): the Overlay tool at `/overlay` is a useful starting point. For higher-volume or institutional engagements, contact <partnerships@aqta.ai>.
- **For research collaborations** on voice-first accessibility, agentic UX, or assistive technology: contact <hello@aqta.ai>.

## Citation

```bibtex
@misc{spectra_v0_3_0,
  title  = {Spectra — voice-first AI browser agent for accessibility},
  author = {Chueayen, Anya},
  year   = {2026},
  url    = {https://github.com/Aqta-ai/spectra},
  note   = {Apache 2.0 licensed.}
}
```

## Contact

- **Security disclosures**: <security@aqta.ai>
- **Partnerships and pilots**: <partnerships@aqta.ai>
- **General**: <hello@aqta.ai>
- **Live application**: <https://spectra.aqta.ai>
