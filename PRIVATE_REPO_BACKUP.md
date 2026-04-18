# Private Repo Backup Guide

This file documents what was removed from the **public hackathon repo** but should be kept in your **private production repo**.

## Files to Keep in Private Repo

### Backend Offline Mode
```
backend/app/streaming/ollama_session.py
backend/app/streaming/ollama_client.py
```

### Frontend Offline Mode
```
frontend/src/hooks/useOllamaAudio.ts
```

### Documentation (Optional)
```
docs/OFFLINE_MODE.md
OFFLINE_MODE_TEST.md
DEPLOYMENT_STRATEGY.md
```

## Code Changes to Restore in Private Repo

### backend/app/main.py
Restore provider routing:
```python
# Around line 191-200
provider = os.getenv("SPECTRA_PROVIDER", "gemini").lower()

if provider in ("ollama", "local", "offline"):
    from app.streaming.ollama_session import OllamaStreamingSession
    session = OllamaStreamingSession(websocket, user_id=user_id, session_id=session_id)
else:
    session = SpectraStreamingSession(websocket, user_id=user_id, session_id=session_id)
```

Restore system-info endpoint:
```python
@app.get("/api/system-info")
async def system_info():
    provider_type = os.getenv("SPECTRA_PROVIDER", "gemini").lower()
    offline_mode = provider_type in ("local_audio", "local", "audio", "gemma", "ollama")
    
    return {
        "provider": provider_type,
        "offline_mode": offline_mode,
        "version": "1.0.0",
    }
```

### frontend/src/app/page.tsx
Restore imports:
```typescript
import { useOllamaAudio } from "@/hooks/useOllamaAudio";
```

Restore state and refs:
```typescript
const [offlineMode, setOfflineMode] = useState(false);
const speakResponseRef = useRef<(text: string) => void>(() => {});
```

Restore offline mode detection:
```typescript
// In useEffect
const savedMode = localStorage.getItem('spectra_mode');
if (savedMode === 'offline') {
  setOfflineMode(true);
}
```

Restore Ollama hook:
```typescript
const { startListening: startOllamaListening, speakResponse } = useOllamaAudio({
  enabled: offlineMode && isConnected,
  // ... rest of hook configuration
});

useEffect(() => {
  speakResponseRef.current = speakResponse;
}, [speakResponse]);
```

Restore offline mode in handleStart:
```typescript
if (offlineMode) {
  startOllamaListening();
} else {
  await startMic();
  unmuteMic();
}
```

Restore speakResponse call in onTurnComplete:
```typescript
if (offlineMode) {
  speakResponseRef.current(finalText);
}
```

Restore Provider toggle UI in header.

## Environment Variables for Private Repo

```bash
# .env for offline mode
SPECTRA_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma2
```

## Quick Recovery Steps

If you need to restore offline mode in private repo:

1. **Get the files back:**
   ```bash
   git log --all --full-history -- backend/app/streaming/ollama_session.py
   git show <commit>:backend/app/streaming/ollama_session.py > backend/app/streaming/ollama_session.py
   # Repeat for other deleted files
   ```

2. **Or, restore from git history:**
   ```bash
   git checkout 2c741c6^ -- backend/app/streaming/ollama_session.py
   git checkout 2c741c6^ -- backend/app/streaming/ollama_client.py
   git checkout 2c741c6^ -- frontend/src/hooks/useOllamaAudio.ts
   ```

3. **Restore code changes to main files:**
   - Reference the diffs in commits 844c92c and 2c741c6

## Why This Approach?

✅ **Hackathon submission stays focused** — Gemini only, no distraction  
✅ **Offline moat stays proprietary** — Not exposed in public GitHub  
✅ **Production has full features** — Private repo has everything  
✅ **Easy to maintain** — Clean separation of concerns  

## Timeline

- **Now:** Public repo has Gemini only ✅
- **Later:** Push public repo to Aqta-ai/spectra
- **After hackathon:** Keep using private repo for production
- **spectra.aqta.ai:** Runs from private repo with offline mode enabled
