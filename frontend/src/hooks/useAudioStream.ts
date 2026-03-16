"use client";

import { useRef, useCallback } from "react";

interface AudioStreamOptions {
  onAudioChunk: (base64Pcm: string) => void;
}

/** Inline AudioWorklet processor — outputs 16kHz s16le PCM for Gemini Live API.
 *  Browsers often ignore getUserMedia sampleRate; we resample if context !== 16kHz.
 */
const TARGET_RATE = 16000;
const WORKLET_CODE = `
class PcmProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.inputRate = sampleRate;
    this.ratio = this.inputRate / ${TARGET_RATE};
    this.buffer = [];
  }
  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    const float32 = input[0];
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]));
      this.buffer.push(s < 0 ? s * 0x8000 : s * 0x7fff);
    }
    if (this.ratio >= 0.99 && this.ratio <= 1.01) {
      const int16 = new Int16Array(this.buffer.length);
      for (let i = 0; i < this.buffer.length; i++) int16[i] = this.buffer[i];
      this.buffer = [];
      this.port.postMessage(int16.buffer, [int16.buffer]);
      return true;
    }
    if (this.ratio < 1) return true;
    const outLen = Math.floor(this.buffer.length / this.ratio);
    if (outLen < 1) return true;
    const consumed = Math.min(this.buffer.length, Math.floor(outLen * this.ratio));
    const int16 = new Int16Array(outLen);
    for (let i = 0; i < outLen; i++) {
      const srcIdx = i * this.ratio;
      const idx = Math.min(Math.floor(srcIdx), this.buffer.length - 1);
      const frac = srcIdx - idx;
      const a = this.buffer[idx] ?? 0;
      const b = this.buffer[Math.min(idx + 1, this.buffer.length - 1)] ?? a;
      int16[i] = Math.round(a + frac * (b - a));
    }
    this.buffer = this.buffer.slice(consumed);
    if (this.buffer.length > ${TARGET_RATE} * 2) this.buffer = [];
    this.port.postMessage(int16.buffer, [int16.buffer]);
    return true;
  }
}
registerProcessor('pcm-processor', PcmProcessor);
`;

function encodeInt16ToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary);
}

export function useAudioStream({ onAudioChunk }: AudioStreamOptions) {
  const streamRef = useRef<MediaStream | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const onAudioChunkRef = useRef(onAudioChunk);
  const mutedRef = useRef(false); // mute mic while Gemini is speaking
  const mutedAtRef = useRef<number | null>(null);
  onAudioChunkRef.current = onAudioChunk;

  const startMic = useCallback(async () => {
    // Always start unmuted , mutedRef can be left true if stopMic was called
    // while Spectra was speaking, which would make the next session permanently deaf
    mutedRef.current = false;
    mutedAtRef.current = null;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    } catch (err) {
      // Propagate mic permission errors so the caller can show a message
      throw new Error(`Microphone access denied: ${err instanceof Error ? err.message : String(err)}`);
    }
    streamRef.current = stream;

    const audioContext = new AudioContext({ sampleRate: 16000 });
    contextRef.current = audioContext;

    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }

    // Create blob URL; must revoke it even if addModule throws
    const blob = new Blob([WORKLET_CODE], { type: "application/javascript" });
    const workletUrl = URL.createObjectURL(blob);
    try {
      await audioContext.audioWorklet.addModule(workletUrl);
    } finally {
      // Always revoke , prevents memory leak if addModule fails
      URL.revokeObjectURL(workletUrl);
    }

    const source = audioContext.createMediaStreamSource(stream);
    const workletNode = new AudioWorkletNode(audioContext, "pcm-processor");
    workletNodeRef.current = workletNode;

    workletNode.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
      // Don't send audio while muted , prevents barge-in while Spectra is speaking
      if (mutedRef.current) {
        // Hard backstop: if muted for over 8s, something went wrong (Gemini died
        // mid-turn without sending turn_complete). Force-unmute so the user isn't
        // permanently deaf.
        if (mutedAtRef.current && Date.now() - mutedAtRef.current > 8000) {
          mutedRef.current = false;
          mutedAtRef.current = null;
        } else {
          return;
        }
      }
      onAudioChunkRef.current(encodeInt16ToBase64(e.data));
    };

    source.connect(workletNode);
  }, []);

  const stopMic = useCallback(() => {
    if (workletNodeRef.current) {
      // Null the message handler BEFORE disconnect so in-flight messages from the
      // AudioWorklet thread don't reach onAudioChunkRef after the session closes.
      // Without this, chunks queued in the worklet port fire after stopMic returns
      // and get sent to whatever backend session is open next.
      workletNodeRef.current.port.onmessage = null;
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    contextRef.current?.close();
    contextRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const muteMic = useCallback(() => {
    mutedRef.current = true;
    mutedAtRef.current = Date.now();
  }, []);
  const unmuteMic = useCallback(() => {
    mutedRef.current = false;
    mutedAtRef.current = null;
  }, []);

  return { startMic, stopMic, muteMic, unmuteMic };
}
