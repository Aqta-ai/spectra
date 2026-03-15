/**
 * Multimodal Feedback System
 * Provides audio, visual, and haptic feedback for actions
 */

export interface FeedbackPreferences {
  audioEnabled: boolean;
  audioVolume: number; // 0-1
  visualEnabled: boolean;
  visualIntensity: number; // 0-1
  hapticEnabled: boolean;
  hapticIntensity: number; // 0-1
  reducedMotion: boolean;
}

export interface Action {
  type: 'click' | 'type' | 'scroll' | 'navigate' | 'press_key' | 'describe';
  target?: { x: number; y: number; description?: string };
  params?: any;
}

export interface Result {
  success: boolean;
  message?: string;
  error?: string;
}

// Audio earcons (short sounds for actions)
class AudioFeedback {
  private audioContext: AudioContext | null = null;
  private volume: number = 0.3;
  private enabled: boolean = true;

  constructor() {
    if (typeof window !== 'undefined' && 'AudioContext' in window) {
      this.audioContext = new AudioContext();
    }
  }

  setVolume(volume: number) {
    this.volume = Math.max(0, Math.min(1, volume));
  }

  setEnabled(enabled: boolean) {
    this.enabled = enabled;
  }

  async play(actionType: string, success: boolean) {
    if (!this.enabled || !this.audioContext) return;

    try {
      const oscillator = this.audioContext.createOscillator();
      const gainNode = this.audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      // Different sounds for different actions
      const sounds = {
        click: { freq: success ? 800 : 400, duration: 0.1 },
        type: { freq: success ? 600 : 300, duration: 0.05 },
        scroll: { freq: success ? 500 : 250, duration: 0.15 },
        navigate: { freq: success ? 1000 : 500, duration: 0.2 },
        press_key: { freq: success ? 700 : 350, duration: 0.08 },
        describe: { freq: success ? 900 : 450, duration: 0.12 },
      };

      const sound = sounds[actionType as keyof typeof sounds] || sounds.click;

      oscillator.frequency.value = sound.freq;
      oscillator.type = 'sine';

      // Envelope
      gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
      gainNode.gain.linearRampToValueAtTime(
        this.volume,
        this.audioContext.currentTime + 0.01
      );
      gainNode.gain.exponentialRampToValueAtTime(
        0.01,
        this.audioContext.currentTime + sound.duration
      );

      oscillator.start(this.audioContext.currentTime);
      oscillator.stop(this.audioContext.currentTime + sound.duration);
    } catch (error) {
      console.error('[AudioFeedback] Error playing sound:', error);
    }
  }

  async playSuccess() {
    await this.play('click', true);
  }

  async playError() {
    await this.play('click', false);
  }
}

// Visual feedback (highlights, animations, overlays)
class VisualFeedback {
  private intensity: number = 1.0;
  private enabled: boolean = true;
  private reducedMotion: boolean = false;

  setIntensity(intensity: number) {
    this.intensity = Math.max(0, Math.min(1, intensity));
  }

  setEnabled(enabled: boolean) {
    this.enabled = enabled;
  }

  setReducedMotion(reduced: boolean) {
    this.reducedMotion = reduced;
  }

  async show(action: Action, success: boolean) {
    if (!this.enabled) return;

    const { type, target } = action;

    if (target && target.x !== undefined && target.y !== undefined) {
      this.showTargetHighlight(target.x, target.y, type, success);
    }

    this.showActionIndicator(type, success);
  }

  private showTargetHighlight(x: number, y: number, actionType: string, success: boolean) {
    // Create highlight element
    const highlight = document.createElement('div');
    highlight.className = 'spectra-action-highlight';
    highlight.style.cssText = `
      position: fixed;
      left: ${x}px;
      top: ${y}px;
      width: 40px;
      height: 40px;
      margin-left: -20px;
      margin-top: -20px;
      border: 3px solid ${success ? '#22c55e' : '#ef4444'};
      border-radius: 50%;
      pointer-events: none;
      z-index: 999999;
      opacity: ${this.intensity};
      ${!this.reducedMotion ? 'animation: spectra-pulse 0.6s ease-out;' : ''}
    `;

    document.body.appendChild(highlight);

    // Remove after animation
    setTimeout(() => {
      highlight.remove();
    }, 600);
  }

  private showActionIndicator(actionType: string, success: boolean) {
    // Create indicator element
    const indicator = document.createElement('div');
    indicator.className = 'spectra-action-indicator';
    
    const icons = {
      click: '👆',
      type: '⌨️',
      scroll: '📜',
      navigate: '🧭',
      press_key: '⌨️',
      describe: '👁️',
    };

    const icon = icons[actionType as keyof typeof icons] || '✨';
    const color = success ? '#22c55e' : '#ef4444';

    indicator.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 20px;
      background: ${color};
      color: white;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      pointer-events: none;
      z-index: 999999;
      opacity: ${this.intensity};
      ${!this.reducedMotion ? 'animation: spectra-slide-in 0.3s ease-out;' : ''}
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    `;

    indicator.textContent = `${icon} ${actionType.replace('_', ' ')}`;

    document.body.appendChild(indicator);

    // Remove after delay
    setTimeout(() => {
      if (!this.reducedMotion) {
        indicator.style.animation = 'spectra-slide-out 0.3s ease-in';
      }
      setTimeout(() => indicator.remove(), 300);
    }, 2000);
  }

  showProgress(message: string) {
    const progress = document.createElement('div');
    progress.className = 'spectra-progress';
    progress.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      padding: 24px 32px;
      background: rgba(0, 0, 0, 0.9);
      color: white;
      border-radius: 12px;
      font-size: 16px;
      font-weight: 500;
      pointer-events: none;
      z-index: 999999;
      opacity: ${this.intensity};
      ${!this.reducedMotion ? 'animation: spectra-fade-in 0.2s ease-out;' : ''}
    `;

    progress.textContent = message;
    progress.id = 'spectra-progress-indicator';

    // Remove existing progress indicator
    const existing = document.getElementById('spectra-progress-indicator');
    if (existing) existing.remove();

    document.body.appendChild(progress);

    return {
      update: (newMessage: string) => {
        progress.textContent = newMessage;
      },
      remove: () => {
        if (!this.reducedMotion) {
          progress.style.animation = 'spectra-fade-out 0.2s ease-in';
        }
        setTimeout(() => progress.remove(), 200);
      },
    };
  }
}

// Haptic feedback (vibration for mobile)
class HapticFeedback {
  private intensity: number = 1.0;
  private enabled: boolean = true;

  setIntensity(intensity: number) {
    this.intensity = Math.max(0, Math.min(1, intensity));
  }

  setEnabled(enabled: boolean) {
    this.enabled = enabled;
  }

  async vibrate(pattern: 'success' | 'error' | 'warning' | 'info') {
    if (!this.enabled || !('vibrate' in navigator)) return;

    try {
      const patterns = {
        success: [50, 50, 50],
        error: [100, 50, 100],
        warning: [75],
        info: [30],
      };

      const vibrationPattern = patterns[pattern].map(
        (duration) => duration * this.intensity
      );

      navigator.vibrate(vibrationPattern);
    } catch (error) {
      console.error('[HapticFeedback] Error:', error);
    }
  }
}

// Main feedback system
export class MultimodalFeedback {
  private audioFeedback: AudioFeedback;
  private visualFeedback: VisualFeedback;
  private hapticFeedback: HapticFeedback;
  private preferences: FeedbackPreferences;

  constructor(preferences?: Partial<FeedbackPreferences>) {
    this.audioFeedback = new AudioFeedback();
    this.visualFeedback = new VisualFeedback();
    this.hapticFeedback = new HapticFeedback();

    this.preferences = {
      audioEnabled: true,
      audioVolume: 0.3,
      visualEnabled: true,
      visualIntensity: 1.0,
      hapticEnabled: true,
      hapticIntensity: 1.0,
      reducedMotion: false,
      ...preferences,
    };

    this.applyPreferences();
    this.injectStyles();
  }

  async provideFeedback(action: Action, result: Result) {
    // Parallel feedback
    await Promise.all([
      this.audioFeedback.play(action.type, result.success),
      this.visualFeedback.show(action, result.success),
      this.hapticFeedback.vibrate(result.success ? 'success' : 'error'),
    ]);
  }

  async showSuccess(message?: string) {
    await Promise.all([
      this.audioFeedback.playSuccess(),
      this.hapticFeedback.vibrate('success'),
    ]);
  }

  async showError(message?: string) {
    await Promise.all([
      this.audioFeedback.playError(),
      this.hapticFeedback.vibrate('error'),
    ]);
  }

  showProgress(message: string) {
    return this.visualFeedback.showProgress(message);
  }

  setPreferences(prefs: Partial<FeedbackPreferences>) {
    this.preferences = { ...this.preferences, ...prefs };
    this.applyPreferences();
  }

  getPreferences(): FeedbackPreferences {
    return { ...this.preferences };
  }

  private applyPreferences() {
    this.audioFeedback.setEnabled(this.preferences.audioEnabled);
    this.audioFeedback.setVolume(this.preferences.audioVolume);
    this.visualFeedback.setEnabled(this.preferences.visualEnabled);
    this.visualFeedback.setIntensity(this.preferences.visualIntensity);
    this.visualFeedback.setReducedMotion(this.preferences.reducedMotion);
    this.hapticFeedback.setEnabled(this.preferences.hapticEnabled);
    this.hapticFeedback.setIntensity(this.preferences.hapticIntensity);
  }

  private injectStyles() {
    if (typeof document === 'undefined') return;

    const styleId = 'spectra-feedback-styles';
    if (document.getElementById(styleId)) return;

    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      @keyframes spectra-pulse {
        0% {
          transform: scale(0.5);
          opacity: 1;
        }
        100% {
          transform: scale(2);
          opacity: 0;
        }
      }

      @keyframes spectra-slide-in {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }

      @keyframes spectra-slide-out {
        from {
          transform: translateX(0);
          opacity: 1;
        }
        to {
          transform: translateX(100%);
          opacity: 0;
        }
      }

      @keyframes spectra-fade-in {
        from {
          opacity: 0;
          transform: translate(-50%, -50%) scale(0.9);
        }
        to {
          opacity: 1;
          transform: translate(-50%, -50%) scale(1);
        }
      }

      @keyframes spectra-fade-out {
        from {
          opacity: 1;
          transform: translate(-50%, -50%) scale(1);
        }
        to {
          opacity: 0;
          transform: translate(-50%, -50%) scale(0.9);
        }
      }

      @media (prefers-reduced-motion: reduce) {
        .spectra-action-highlight,
        .spectra-action-indicator,
        .spectra-progress {
          animation: none !important;
        }
      }
    `;

    document.head.appendChild(style);
  }
}

// Global instance
let _feedbackSystem: MultimodalFeedback | null = null;

export function getFeedbackSystem(preferences?: Partial<FeedbackPreferences>): MultimodalFeedback {
  if (!_feedbackSystem) {
    _feedbackSystem = new MultimodalFeedback(preferences);
  }
  return _feedbackSystem;
}
