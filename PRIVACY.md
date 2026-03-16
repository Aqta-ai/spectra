# Privacy Policy

**Spectra** — Aqta Technologies Ltd, Dublin, Ireland

*Last updated: 16 March 2026*

---

## Summary

Spectra is designed with privacy at its core. We store nothing. No screenshots, no audio, no browsing history, no personal data. Everything happens in memory and is discarded when your session ends.

---

## 1. What Spectra Processes

During an active session, Spectra temporarily processes the following data **in memory only**:

| Data | Purpose | Retention |
|------|---------|-----------|
| **Screen frames** | Sent to Google's Gemini API for visual analysis so Spectra can understand your screen | Held as a single variable in RAM. Each new frame replaces the previous one. Discarded when the session ends. |
| **Voice audio** | Streamed to Google's Gemini API for speech recognition and natural language understanding | Streamed in real time. Not recorded. Not stored. |
| **Browser actions** | Click, type, scroll, and keyboard actions executed on your behalf via the Chrome extension | Transient messages routed between the frontend and extension. Not logged. |
| **Session preferences** | Shortcuts and preferences you explicitly teach Spectra (e.g. "remember that 'check email' means go to Gmail") | Stored in browser-local memory for the session duration. Cleared on "forget everything" or session end. |

**We do not process:**
- Your identity, name, email, or account information
- Your browsing history outside the active session
- Your passwords or form data (Spectra types what you dictate but does not store it)
- Any data from tabs you haven't shared with Spectra

---

## 2. What Leaves Your Device

The only data that leaves your device is sent to **Google's Gemini API**:

- **Screen frames** (JPEG images, ~80 KB each) — sent for visual understanding
- **Voice audio** (PCM 16 kHz) — streamed for speech recognition and response generation

This data is sent directly to Google's servers via an encrypted WebSocket connection (WSS/TLS). It is **not** routed through Aqta's servers — the Spectra backend acts as a bridge, not a storage layer.

**No other third-party services** receive your data. There are no analytics, tracking pixels, advertising networks, or data brokers involved.

---

## 3. Google's Data Handling

Data sent to the Gemini API is subject to Google's own privacy policies and terms:

- [Google Privacy Policy](https://policies.google.com/privacy)
- [Google Gemini API Terms of Service](https://ai.google.dev/gemini-api/terms)
- [Google Cloud Data Processing Terms](https://cloud.google.com/terms/data-processing-terms)

We recommend reviewing these policies if you have concerns about how Google handles API data.

---

## 4. What We Store

**Nothing.**

- No files are written to disc
- No database is used
- No cloud storage buckets are provisioned
- No cookies are set (beyond what your browser requires for HTTPS)
- No local storage is used for tracking
- No server-side logs contain your screen content or audio

When you close Spectra or end your session, all in-memory data is garbage-collected by the runtime.

---

## 5. The Chrome Extension (Spectra Bridge)

The Spectra Bridge Chrome extension requires `<all_urls>` permission to execute browser actions (click, type, scroll, navigate) on any website. The extension:

- **Does not** collect, transmit, or store any browsing data
- **Does not** communicate with any server other than the Spectra frontend tab
- **Does not** read or store your passwords, form data, or cookies
- **Only** executes actions when explicitly instructed by the Spectra frontend
- Is **fully open source** — you can inspect every line at [github.com/Aqta-ai/spectra/tree/main/extension](https://github.com/Aqta-ai/spectra/tree/main/extension)

The extension uses Chrome's `runtime.sendMessage` and `tabs.sendMessage` APIs to route action messages. It does not use `storage`, `history`, `bookmarks`, or any other sensitive Chrome API.

---

## 6. Self-Hosted Deployments

If you self-host Spectra (using Docker, Cloud Run, or running locally), you are responsible for:

- Your own API key management (store keys securely; never commit them to version control)
- Your server's logging configuration (we recommend `LOG_LEVEL=WARNING` in production)
- Compliance with applicable data protection regulations in your jurisdiction

The default deployment configuration (`deploy.sh`) stores the Gemini API key in Google Cloud Secret Manager, not in environment variables or source code.

---

## 7. Children's Privacy

Spectra is not directed at children under 13 (or the applicable age of consent in your jurisdiction). We do not knowingly collect data from children. If you believe a child has provided data through Spectra, please contact us.

---

## 8. Data Protection Rights

Because Spectra does not store personal data, most data subject rights (access, rectification, erasure, portability) are satisfied by default — there is no data to access, correct, delete, or transfer.

If you have taught Spectra preferences during a session, you can clear them at any time by saying **"Forget everything"** or **"Clear my memory."**

For questions about your rights under the GDPR, the UK Data Protection Act 2018, or any other applicable regulation, contact us at the address below.

---

## 9. Changes to This Policy

We may update this policy from time to time. Changes will be reflected in the "Last updated" date at the top of this page and committed to the public repository.

---

## 10. Contact

**Aqta Technologies Ltd**
Dublin, Ireland

- GitHub: [github.com/Aqta-ai](https://github.com/Aqta-ai)
- Website: [aqta.ai](https://aqta.ai)

---

## 11. Open Source Transparency

Spectra is open source under the Apache Licence 2.0. Every claim in this policy can be verified by inspecting the source code:

| Claim | Where to verify |
|-------|----------------|
| No data stored to disc | `backend/app/streaming/session.py` — `_latest_frame` is a single variable, overwritten each frame |
| No database | No ORM, no SQL, no database driver in `backend/requirements.txt` |
| No analytics or tracking | No Google Analytics, Mixpanel, Segment, or similar in `frontend/package.json` |
| Extension doesn't store data | `extension/content.js` and `extension/background.js` — no `chrome.storage` calls |
| API key in Secret Manager | `deploy.sh` — `gcloud secrets create spectra-gemini-key` |
| HTTPS/WSS only | `deploy.sh` — Cloud Run provides managed TLS; frontend connects via `wss://` |
