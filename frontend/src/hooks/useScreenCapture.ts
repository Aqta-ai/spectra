"use client";

import { useRef, useCallback, useEffect, useState } from "react";

interface ScreenCaptureOptions {
  onFrame: (base64Jpeg: string, width: number, height: number) => void;
  onStop?: () => void;
  fps?: number;
}

/**
 * Screen capture hook with adaptive quality and performance optimizations.
 * Reduces JPEG quality when frames are large to save bandwidth,
 * skips identical frames, and uses efficient frame processing.
 */
export function useScreenCapture({ onFrame, onStop, fps = 2 }: ScreenCaptureOptions) {
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const onFrameRef = useRef(onFrame);
  const onStopRef = useRef(onStop);
  const lastFrameHashRef = useRef<string | null>(null);
  const frameCountRef = useRef(0);
  const [isActive, setIsActive] = useState(false);

  useEffect(() => { onFrameRef.current = onFrame; }, [onFrame]);
  useEffect(() => { onStopRef.current = onStop; }, [onStop]);

  /** Hash from a region of image data — samples top, center, bottom so scrolling is detected */
  const regionHash = useCallback((
    ctx: CanvasRenderingContext2D,
    canvasWidth: number,
    canvasHeight: number
  ): string => {
    const sampleSize = 80;
    const regions = [
      { x: canvasWidth / 2 - sampleSize / 2, y: 0, w: sampleSize, h: sampleSize }, // top
      { x: canvasWidth / 2 - sampleSize / 2, y: canvasHeight / 2 - sampleSize / 2, w: sampleSize, h: sampleSize }, // center
      { x: canvasWidth / 2 - sampleSize / 2, y: canvasHeight - sampleSize, w: sampleSize, h: sampleSize }, // bottom
    ];
    let h = 0;
    for (const r of regions) {
      const id = ctx.getImageData(Math.max(0, r.x), Math.max(0, r.y), r.w, r.h);
      for (let i = 0; i < id.data.length; i += 200) {
        h = ((h << 5) - h + id.data[i]) | 0;
      }
    }
    return h.toString(36);
  }, []);

  /** Adaptive quality based on resolution and frame rate */
  const getOptimalQuality = useCallback((width: number, height: number): number => {
    const pixels = width * height;
    if (pixels > 2_000_000) return 0.4; // 4K+ screens
    if (pixels > 1_500_000) return 0.5; // 1440p screens
    if (pixels > 800_000) return 0.6;   // 1080p screens
    return 0.7; // Lower resolutions
  }, []);

  const startCapture = useCallback(async () => {
    // Guard: if already capturing, don't create a second stream + setInterval.
    // Without this, a double-click on "Share screen" leaks the first MediaStream
    // and runs two frame intervals simultaneously.
    if (streamRef.current) return;

    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: 3, width: 960, height: 540 },
        audio: false,
      });
      streamRef.current = stream;

      const video = document.createElement("video");
      video.srcObject = stream;
      video.muted = true;
      (video as HTMLVideoElement & { playsInline: boolean }).playsInline = true;

      await new Promise<void>((resolve) => {
        const onLoadedMetadata = () => {
          video.removeEventListener("loadedmetadata", onLoadedMetadata);
          resolve();
        };
        video.addEventListener("loadedmetadata", onLoadedMetadata);
        video.play().catch(() => resolve());
      });

      videoRef.current = video;

      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      canvasRef.current = canvas;

      setIsActive(true);

      // Send one frame immediately so the backend has something to describe quickly
      const sendFirstFrame = () => {
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        if (!ctx || !video.videoWidth || !video.videoHeight) return;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0);
        try {
          const dataUrl = canvas.toDataURL("image/jpeg", 0.75);
          const base64 = dataUrl.split(",")[1];
          if (base64) {
            onFrameRef.current(base64, canvas.width, canvas.height);
          }
        } catch {
          // ignore
        }
      };
      
      // Send initial frame after video is ready
      setTimeout(sendFirstFrame, 100);

      // Optimised frame processing with requestAnimationFrame
      intervalRef.current = setInterval(() => {
        requestAnimationFrame(() => {
          // Bug fix: stopCapture() nulls streamRef between the setInterval tick and
          // this RAF callback firing. Without this guard, orphaned callbacks accumulate
          // on repeated start/stop cycles, accessing nulled canvas/video refs.
          if (!streamRef.current) return;

          const ctx = canvas.getContext("2d", {
            willReadFrequently: true,
            alpha: false // Disable alpha for better performance
          });
          if (!ctx || !video.videoWidth || !video.videoHeight) return;

          // Only resize canvas if dimensions changed
          if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
          }

          ctx.drawImage(video, 0, 0);

          try {
            // Force send every 2nd frame (~0.67s at 3fps) so Spectra's view updates at least once per second.
            // Gemini Live API accepts max 1 FPS, so we ensure fresh context without over-sending.
            frameCountRef.current++;
            const forceSend = frameCountRef.current % 2 === 0;

            if (!forceSend) {
              // Multi-region hash (top, center, bottom) — detects scrolling and partial changes
              const frameHash = regionHash(ctx, canvas.width, canvas.height);
              if (frameHash === lastFrameHashRef.current) {
                return; // Skip identical frame
              }
              lastFrameHashRef.current = frameHash;
            }

            // Adaptive quality based on resolution
            const quality = getOptimalQuality(canvas.width, canvas.height);
            const dataUrl = canvas.toDataURL("image/jpeg", quality);
            const base64 = dataUrl.split(",")[1];
            
            if (base64) {
              onFrameRef.current(base64, canvas.width, canvas.height);
            }
          } catch (err) {
            console.error("Frame capture error:", err);
          }
        });
      }, 1000 / fps);

      // Handle user stopping screen share via browser UI
      stream.getVideoTracks()[0].onended = () => {
        stopCapture();
        onStopRef.current?.();
      };
    } catch (error) {
      // Re-throw the error so the caller can handle it
      throw error;
    }
  }, [fps]);

  const stopCapture = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    videoRef.current = null;
    lastFrameHashRef.current = null;
    setIsActive(false);
  }, []);

  return { startCapture, stopCapture, isActive };
}
