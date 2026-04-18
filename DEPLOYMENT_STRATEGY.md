# Deployment Strategy: Public vs Private

## Current State

You have **one working repo** with both Gemini Live (public) and Ollama offline (private).

## Three-Step Plan

### Step 1: Test Offline Mode Works ✅

Run the test suite in `OFFLINE_MODE_TEST.md` to verify everything works end-to-end.

**Key verification:**
- Speech recognition → Backend → Speech synthesis loop completes
- Multi-turn conversations work smoothly
- No crashes or console errors

### Step 2: Prepare Public Repo (Hackathon Submission)

When you're ready to push to **GitHub public** (`Aqta-ai/spectra`):

Remove offline mode code:
```bash
git rm backend/app/streaming/ollama_session.py
git rm backend/app/streaming/ollama_client.py
git rm frontend/src/hooks/useOllamaAudio.ts
```

Simplify `main.py` (remove Ollama branch):
```python
# In backend/app/main.py, line ~192-200
# Remove this block:
if provider in ("ollama", "local", "offline"):
    from app.streaming.ollama_session import OllamaStreamingSession
    session = OllamaStreamingSession(...)

# Keep only:
session = SpectraStreamingSession(websocket, user_id=user_id, session_id=session_id)
```

Simplify `page.tsx` (remove offline mode UI):
```typescript
// Remove: useOllamaAudio hook
// Remove: Provider toggle UI (lines ~736-770)
// Remove: speakResponseRef code
// Remove: offlineMode state
```

Update `.env.example` (Gemini only):
```bash
# Keep GOOGLE credentials, remove OLLAMA_* variables
```

Commit:
```bash
git commit -m "chore: prepare for public hackathon submission

- Remove offline mode (Ollama/Gemma 4) - kept private in Aqta-ai/spectra-ai
- Focus public repo on Gemini Live API integration
- Simplify configuration (Gemini-only)
- Production deployment uses private repo with full feature set"
```

### Step 3: Deploy Private Repo to Production

Your **private repo** (`Aqta-ai/spectra-ai`) keeps everything intact:
- ✅ Ollama session code
- ✅ Offline mode UI
- ✅ Feature flags
- ✅ Full configuration

Deploy to **spectra.aqta.ai** with:
```bash
# Environment variables
SPECTRA_PROVIDER=ollama
ENABLE_OFFLINE_MODE=true
OLLAMA_BASE_URL=http://internal-ollama:11434
OLLAMA_MODEL=gemma2
```

## Git Workflow

```
Your Local Machine
├── spectra (current - keep this, full code)
│   ├── All Gemini code ✅
│   ├── All Ollama code ✅
│   ├── All tests ✅
│   └── Ready for private production
│
└── GitHub
    ├── Aqta-ai/spectra (PUBLIC - Gemini only)
    │   ├── All Gemini code ✅
    │   ├── NO Ollama code
    │   ├── NO offline mode UI
    │   └── Hackathon submission
    │
    └── Aqta-ai/spectra-ai (PRIVATE - full)
        ├── All Gemini code ✅
        ├── All Ollama code ✅
        ├── All tests ✅
        ├── Feature flags
        └── Production deployment
```

## Timeline

1. **Now:** ✅ Offline mode works (verified via tests)
2. **Before hackathon submission:** Clean up public repo, remove Ollama code
3. **After hackathon:** Push cleaned version to `Aqta-ai/spectra` (public)
4. **Production deploy:** Keep all code in `Aqta-ai/spectra-ai` (private), deploy to spectra.aqta.ai

## Benefits of This Approach

✅ **Hackathon submission stays focused** — One AI model (Gemini), one provider  
✅ **Offline moat stays proprietary** — Gemma 4 implementation is your competitive advantage  
✅ **Production is feature-rich** — Full flexibility with environment flags  
✅ **Easy to maintain** — Private repo = full code, public repo = clean subset  
✅ **Scalable** — Can add more providers to private version without public noise  

## Feature Flags for Future

Once offline mode is in production, you can offer it as:

```
Free tier: Gemini Live only
Pro tier: Offline mode (Gemma 4) + Gemini Live
Enterprise: Custom LLM models
```

Set via environment:
```bash
ENABLE_OFFLINE_MODE=true   # Pro tier or higher
ENABLE_GEMINI_MODE=true    # All tiers
ALLOW_PROVIDER_TOGGLE=true # Let users choose
```

## What to Do Now

1. **Run offline mode tests** — Verify it all works
2. **Keep current repo intact** — Don't delete Ollama code yet
3. **When ready to push to GitHub:**
   - Create/push to `Aqta-ai/spectra` (public, Gemini only)
   - Create/push to `Aqta-ai/spectra-ai` (private, full)
   - Keep local copy for development
4. **Deploy to spectra.aqta.ai** — Use private repo with offline mode enabled

Does this strategy look good? Want me to help you prepare the public repo cleanup?
