/**
 * Onboarding Guide Component
 * Shows helpful guidance for first-time users
 */

import React, { useEffect, useState } from 'react';

interface OnboardingGuideProps {
  isFirstTime: boolean;
  hasSharedScreen: boolean;
  isConnected: boolean;
  onDismiss?: () => void;
}

export function OnboardingGuide({
  isFirstTime,
  hasSharedScreen,
  isConnected,
  onDismiss,
}: OnboardingGuideProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [step, setStep] = useState<'welcome' | 'share-screen' | 'ready'>('welcome');

  useEffect(() => {
    if (!isFirstTime || hasSharedScreen) {
      setIsVisible(false);
      return;
    }

    if (isConnected && !hasSharedScreen) {
      setIsVisible(true);
      setStep('share-screen');
    }
  }, [isFirstTime, hasSharedScreen, isConnected]);

  useEffect(() => {
    if (hasSharedScreen && step === 'share-screen') {
      setStep('ready');
      // Auto-dismiss after showing success
      setTimeout(() => {
        setIsVisible(false);
        onDismiss?.();
      }, 3000);
    }
  }, [hasSharedScreen, step, onDismiss]);

  if (!isVisible) return null;

  return (
    <div
      className="fixed top-4 right-4 z-50 max-w-md bg-spectra-surface border border-spectra-primary/50 rounded-xl shadow-2xl p-6 animate-slide-in text-white"
      role="dialog"
      aria-labelledby="onboarding-title"
      aria-describedby="onboarding-description"
    >
      {step === 'share-screen' && (
        <>
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-spectra-primary rounded-full flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
              </div>
            </div>
            <div className="flex-1">
              <h3
                id="onboarding-title"
                className="text-lg font-semibold text-gray-900 dark:text-white mb-2"
              >
                Welcome to Spectra! 👋
              </h3>
              <p
                id="onboarding-description"
                className="text-gray-600 dark:text-gray-300 mb-4"
              >
                I'm your voice-controlled screen assistant. To get started, I need to see your screen.
              </p>
              <div className="bg-spectra-primary/20 rounded-lg p-4 mb-4 border border-spectra-primary/30">
                <p className="text-sm font-medium text-white mb-2">
                  Press <kbd className="px-2 py-1 bg-white/10 rounded border border-white/20 font-mono text-sm">W</kbd> to share your screen
                </p>
                <p className="text-xs text-white/70">
                  This allows me to see what's on your screen so I can help you navigate, click buttons, and more!
                </p>
              </div>
              <div className="space-y-2 text-sm text-white/70">
                <p className="flex items-center gap-2">
                  <span className="text-spectra-secondary">✓</span>
                  Describe any webpage
                </p>
                <p className="flex items-center gap-2">
                  <span className="text-spectra-secondary">✓</span>
                  Click buttons and links
                </p>
                <p className="flex items-center gap-2">
                  <span className="text-spectra-secondary">✓</span>
                  Fill out forms
                </p>
                <p className="flex items-center gap-2">
                  <span className="text-spectra-secondary">✓</span>
                  Navigate websites hands-free
                </p>
              </div>
            </div>
          </div>
          <button
            onClick={() => {
              setIsVisible(false);
              onDismiss?.();
            }}
            className="absolute top-2 right-2 text-white/50 hover:text-white"
            aria-label="Dismiss onboarding"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </>
      )}

      {step === 'ready' && (
        <div className="flex items-center gap-4">
          <div className="flex-shrink-0">
            <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center">
              <svg
                className="w-6 h-6 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-white mb-1">
              Screen shared — ready to help
            </h3>
            <p className="text-sm text-white/80">
              I'm ready to help. Just ask me anything!
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// Keyboard shortcut indicator component
export function KeyboardShortcut({ keys }: { keys: string[] }) {
  return (
    <span className="inline-flex gap-1">
      {keys.map((key, index) => (
        <React.Fragment key={key}>
          {index > 0 && <span className="text-gray-400">+</span>}
          <kbd className="px-2 py-1 bg-white dark:bg-gray-700 rounded border border-gray-300 dark:border-gray-600 font-mono text-sm">
            {key}
          </kbd>
        </React.Fragment>
      ))}
    </span>
  );
}
