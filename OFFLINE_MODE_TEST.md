# Offline Mode E2E Test Checklist

Run this before committing to ensure offline mode works perfectly.

## Prerequisites Setup

```bash
# 1. Start Ollama in a terminal
ollama serve

# 2. In another terminal, verify model is available
ollama list
# Should show: gemma2  (or whatever OLLAMA_MODEL you configured)

# If not, pull it:
ollama pull gemma2
```

## Backend Test

```bash
# 1. Configure backend for offline mode
cd backend
cat >> .env << 'EOF'
SPECTRA_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma2
EOF

# 2. Start backend
cd ..
./run.sh

# 3. Monitor backend logs
tail -f /tmp/spectra-backend.log | grep -i ollama

# Expected output:
# [Ollama] Session s-xxxxxxxx initialized (user: default, model: gemma2)
```

## Frontend Test (Browser)

### Test 1: Mode Detection
- [ ] Open http://localhost:3000
- [ ] Check localStorage: `localStorage.getItem('spectra_mode')`
  - Should be `"offline"` (if you set it) or `null` (will use env var)
- [ ] Header shows Provider selector

### Test 2: Activate Offline Mode
- [ ] Click Provider toggle (top right)
- [ ] Select "Ollama" or set: `localStorage.setItem('spectra_mode', 'offline')`
- [ ] Page reloads
- [ ] Check console: `[Spectra] Using offline mode (from localStorage)` ✓

### Test 3: Voice Input (Web Speech API)
- [ ] Press **Q** to activate
- [ ] Status shows "Listening..."
- [ ] Orb shows listening state (pulsing)
- [ ] Speak clearly: **"hello spectra"**
- [ ] Check console for:
  ```
  [OllamaAudio] Listening started
  [OllamaAudio] Got final: hello spectra
  [OllamaAudio] Sending final transcript: hello spectra
  ```
- [ ] Message appears in chat: "You said: hello spectra. Spectra is thinking…"

### Test 4: Backend Processing
- [ ] Check backend log:
  ```
  [Ollama] Processing: hello spectra...
  [Ollama] Chunk N: "response text"
  [Ollama] Generation complete (X chunks, Y chars)
  ```
- [ ] Should see text chunks streaming (not buffered all at end)

### Test 5: Frontend Text Display
- [ ] Response appears in `currentResponse` state (accumulating in real-time)
- [ ] Check console:
  ```
  [Spectra] Got response text: Hello! How can I...
  [Spectra] Got response text: help you today?
  ```
- [ ] Text is **not** displayed in UI yet (held until turn_complete)

### Test 6: Turn Completion
- [ ] Backend sends turn_complete:
  ```
  [Ollama] Final response: Hello! How can I help you today?
  ```
- [ ] Frontend receives turn_complete:
  ```
  [SpectraSocket] case "turn_complete"
  [Spectra] Turn complete, final response: Hello! How can I help...
  [Spectra] Calling speakResponse for offline mode
  [OllamaAudio] Speech synthesis started
  ```

### Test 7: Voice Output (Web Speech API)
- [ ] Response plays via browser TTS
- [ ] Speakers output: "Hello! How can I help you today?"
- [ ] Status shows "Speaking..." / Orb changes to speaking state
- [ ] Duration: ~3-5 seconds (depends on text length)

### Test 8: Speech Synthesis Completes
- [ ] Browser finishes playing response
- [ ] Check console:
  ```
  [OllamaAudio] Speech synthesis ended
  [OllamaAudio] Listening started (auto-resumed)
  ```
- [ ] Status shows "Listening..." again
- [ ] Ready for next turn (no manual Q needed)

### Test 9: Multi-turn Conversation
- [ ] Speak: **"go to google dot com"**
- [ ] Backend processes and responds about navigation
- [ ] Response is spoken
- [ ] Automatically listening for next command
- [ ] Speak: **"search for flights"**
- [ ] Full conversation flow works

### Test 10: Error Handling
- [ ] Stop Ollama server: `killall ollama`
- [ ] Try to send message
- [ ] Check backend log shows connection error
- [ ] Frontend should show error to user
- [ ] Restart Ollama
- [ ] Verify recovery on next attempt

## Performance Metrics

Measure these during testing:

| Metric | Expected | Actual |
|--------|----------|--------|
| Speech recognition latency | <1s | ___ |
| Backend response time | 2-4s | ___ |
| First text chunk arrival | <0.5s after send | ___ |
| Full response generation | ~3-5s | ___ |
| Speech synthesis latency | <0.5s | ___ |
| Auto-resume to listening | <1s | ___ |

## Known Issues During Testing

**Speech recognition fails:**
- Check browser support (Chrome/Edge/Safari work best)
- Firefox needs `media.webspeech.recognition.enabled = true` in `about:config`
- Check microphone permissions in browser settings

**No audio output:**
- Check browser's TTS engine
- macOS: System > Accessibility > Spoken Content
- Test with: `speechSynthesis.speak(new SpeechSynthesisUtterance("hello"))`

**Response never arrives:**
- Ollama not running: `curl http://localhost:11434/api/tags`
- Model not available: `ollama list`
- Check OLLAMA_BASE_URL is correct in `.env`

**Backend logs show errors:**
- Check Python traceback in logs
- Verify message format: `{"type": "text", "data": "..."}`
- Check JSON parsing doesn't fail

## Success Criteria

✅ All 10 tests pass  
✅ No console errors  
✅ No backend crashes  
✅ Voice recognition → Backend → Voice output complete loop works  
✅ Multi-turn conversation flows smoothly  
✅ Response latency acceptable (2-4s)  
✅ Auto-resume listening works without manual Q  

## Cleanup After Testing

```bash
# Remove offline mode from env (before committing to public repo)
cd backend
grep -v "SPECTRA_PROVIDER\|OLLAMA_BASE_URL\|OLLAMA_MODEL" .env > .env.tmp
mv .env.tmp .env

# Or just delete .env and it will use defaults (Gemini mode)
rm backend/.env
```

## Notes for Production

When deploying to spectra.aqta.ai (private):
- Set `SPECTRA_PROVIDER=ollama` in prod env
- Point `OLLAMA_BASE_URL` to your internal Ollama instance
- Ensure Ollama is running and accessible from backend container
- Monitor `/tmp/spectra-backend.log` for Ollama errors
- Consider running Ollama in a separate Docker container or VM
