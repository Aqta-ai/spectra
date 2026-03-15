/**
 * PCM Audio Player , plays raw PCM audio chunks from Gemini Live API.
 * Gemini returns audio/pcm;rate=24000 (24kHz, mono, Int16 LE).
 *
 * Uses gapless scheduling with a small initial buffer to absorb network
 * jitter. No per-chunk fading , chunks are stitched seamlessly.
 */
export class PcmAudioPlayer {
  private audioContext: AudioContext | null = null;
  private gainNode: GainNode | null = null;
  private nextStartTime = 0;
  private isPlaying = false;
  private chunkCount = 0;
  // pendingChunks counts play() calls that have started but not yet scheduled audio.
  // Incremented synchronously at the top of play() , BEFORE any await , so that
  // notifyWhenDone() called from onTurnComplete() sees a non-zero count and
  // defers the mic-unmute until the chunk is actually scheduled and later finishes.
  private pendingChunks = 0;

  private readonly SAMPLE_RATE = 24000;
  // Buffer ahead on first chunk to absorb jitter
  private readonly INITIAL_BUFFER_S = 0.08;
  // How far behind schedule before we reset (avoids stale queue buildup)
  private readonly MAX_DRIFT_S = 0.5;
  // Callback fired when all queued audio has finished playing
  private doneCallback: (() => void) | null = null;

  constructor() {
    // Don't create AudioContext in constructor - wait for user interaction
    // This avoids "AudioContext was not allowed to start" errors
  }

  private initAudioContext() {
    if (!this.audioContext) {
      this.audioContext = new AudioContext({ sampleRate: this.SAMPLE_RATE });
      this.gainNode = this.audioContext.createGain();
      // Start silent and ramp up to avoid an audible click on first chunk
      this.gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
      this.gainNode.gain.linearRampToValueAtTime(1.0, this.audioContext.currentTime + 0.05);
      this.gainNode.connect(this.audioContext.destination);
    }
  }

  private async ensureRunning(): Promise<AudioContext | null> {
    this.initAudioContext();
    if (!this.audioContext) return null;
    // Must resume if suspended (browser policy / tab background) or no sound plays
    if (this.audioContext.state === "suspended") {
      try {
        await this.audioContext.resume();
      } catch (e) {
        console.warn("[AudioPlayer] resume() failed:", e);
        return null;
      }
    }
    if (this.audioContext.state !== "running") {
      console.warn("[AudioPlayer] Context not running after resume:", this.audioContext.state);
    }
    return this.audioContext;
  }

  async play(base64Data: string): Promise<void> {
    // Increment BEFORE any await so notifyWhenDone() sees a non-zero count
    // even when turn_complete arrives while ensureRunning() is still awaiting.
    this.pendingChunks++;

    const ctx = await this.ensureRunning();
    if (!ctx || !this.gainNode) {
      console.error('[AudioPlayer] AudioContext or GainNode not available');
      this.pendingChunks--;
      // If everything is drained, fire the done callback (if any)
      if (this.chunkCount <= 0 && this.pendingChunks <= 0) {
        const cb = this.doneCallback;
        this.doneCallback = null;
        cb?.();
      }
      return;
    }

    // Hot path , verbose logging removed to keep latency low

    // Decode base64 to Int16 array
    const raw = atob(base64Data);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) {
      bytes[i] = raw.charCodeAt(i);
    }

    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);

    // Straight conversion , no per-chunk fading
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768;
    }

    const buffer = ctx.createBuffer(1, float32.length, this.SAMPLE_RATE);
    buffer.getChannelData(0).set(float32);

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.gainNode);

    const now = ctx.currentTime;

    if (!this.isPlaying || this.nextStartTime < now - this.MAX_DRIFT_S) {
      // First chunk or we've drifted too far , reset with a small buffer
      this.nextStartTime = now + this.INITIAL_BUFFER_S;
    }

    // If nextStartTime is slightly in the past but within drift tolerance,
    // just let it play immediately to catch up rather than resetting
    const startAt = Math.max(this.nextStartTime, now);

    // Bug fix: source.start() can throw (e.g. AudioContext closed, invalid buffer).
    // Without this catch, pendingChunks stays > 0 forever → notifyWhenDone never
    // fires → mic is permanently muted for the rest of the session.
    try {
      source.start(startAt);
    } catch (err) {
      console.error('[AudioPlayer] Failed to schedule audio chunk:', err);
      // pendingChunks was incremented at top of play() but lines below never ran
      this.pendingChunks--;
      if (this.chunkCount <= 0 && this.pendingChunks <= 0) {
        const cb = this.doneCallback;
        this.doneCallback = null;
        cb?.();
      }
      return;
    }

    this.nextStartTime = startAt + buffer.duration;
    this.pendingChunks--;
    this.isPlaying = true;
    this.chunkCount++;

    source.onended = () => {
      this.chunkCount--;
      if (this.chunkCount <= 0 && this.pendingChunks <= 0) {
        this.isPlaying = false;
        this.chunkCount = 0;
        const cb = this.doneCallback;
        this.doneCallback = null;
        cb?.();
      }
    };
  }

  /**
   * Call cb once all queued audio has finished playing.
   * If nothing is playing, cb is called synchronously immediately.
   * Only one callback is kept , subsequent calls replace the previous.
   */
  notifyWhenDone(cb: () => void): void {
    // Wait if any chunks are playing OR still being scheduled (pendingChunks > 0).
    // The pendingChunks check is critical: play() increments it before the first
    // await, so turn_complete arriving while play() is suspended won't cause
    // premature unmute.
    if (this.chunkCount <= 0 && this.pendingChunks <= 0) {
      cb();
      return;
    }
    this.doneCallback = cb;
  }

  /** Smoothly fade out and stop all audio */
  stop(): void {
    // Clear pending done-callback , caller is stopping intentionally
    this.doneCallback = null;
    if (this.gainNode && this.audioContext) {
      try {
        this.gainNode.gain.linearRampToValueAtTime(
          0,
          this.audioContext.currentTime + 0.1
        );
      } catch {
        // Context may already be closed
      }
    }

    this.nextStartTime = 0;
    this.isPlaying = false;
    this.chunkCount = 0;
    this.pendingChunks = 0;
    this.audioContext?.close();
    this.audioContext = null;
    this.gainNode = null;
  }

  /**
   * Pre-warm the AudioContext during a user gesture (e.g. button press).
   * Chrome suspends AudioContexts created outside a user-gesture , calling this
   * during the Q keypress / Start button click unlocks playback before audio
   * chunks arrive from the WebSocket.
   */
  warmup(): void {
    this.initAudioContext();
    if (this.audioContext?.state === "suspended") {
      this.audioContext.resume().catch(() => {});
    }
  }

  /** Check if audio is currently playing */
  get playing(): boolean {
    return this.isPlaying;
  }
}
