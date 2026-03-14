"use client";

import { useRef, useCallback } from "react";

interface AudioStreamOptions {
  onAudioChunk: (base64Pcm: string) => void;
}

/** Inline AudioWorklet processor as a blob URL , avoids needing a separate file */
const WORKLET_CODE = `
class PcmProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    const float32 = input[0];
    const int16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
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
    workletNodeRef.current?.disconnect();
    workletNodeRef.current = null;
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
