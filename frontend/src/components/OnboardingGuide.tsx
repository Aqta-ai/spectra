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
  onConnect?: () => void;
  onComplete?: () => void;
}

export function OnboardingGuide({
  hasSharedScreen,
  isConnected,
  onDismiss,
  onConnect,
  onComplete,
}: OnboardingGuideProps) {
  const [step, setStep] = useState<'welcome' | 'share-screen' | 'ready'>('welcome');
  const [isConnecting, setIsConnecting] = useState(false);

  useEffect(() => {
    if (!isConnected && !hasSharedScreen) {
      setStep('welcome');
      setIsConnecting(false);
    } else if (isConnected && !hasSharedScreen) {
      setStep('share-screen');
      setIsConnecting(false);
    } else if (isConnected && hasSharedScreen) {
      setStep('ready');
      // Auto-dismiss after showing success
      const timer = setTimeout(() => {
        onComplete?.();
        onDismiss?.();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isConnected, hasSharedScreen, onComplete, onDismiss]);

  const handleConnect = () => {
    setIsConnecting(true);
    onConnect?.();
  };

  const handleDismiss = () => {
    onComplete?.();
    onDismiss?.();
  };

  return (
    <div
      className="fixed top-6 right-6 z-50 max-w-sm bg-gradient-to-br from-spectra-surface/95 to-spectra-surface/90 backdrop-blur-xl border border-spectra-primary/30 rounded-2xl shadow-2xl p-6 animate-slide-in text-white"
      role="dialog"
      aria-labelledby="onboarding-title"
      aria-describedby="onboarding-description"
    >
      {/* X Button - Always visible */}
      <button
        onClick={handleDismiss}
        className="absolute top-3 right-3 text-white/50 hover:text-white/90 transition-colors p-1 rounded-lg hover:bg-white/10"
        aria-label="Dismiss onboarding"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {step === 'welcome' && (
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 bg-gradient-to-br from-spectra-primary to-spectra-secondary rounded-xl flex items-center justify-center shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          </div>
          <div className="flex-1 pr-6">
            <h3 id="onboarding-title" className="text-lg font-semibold text-white mb-2">
              Welcome to Spectra
            </h3>
            <p id="onboarding-description" className="text-white/80 text-sm mb-4">
              Your voice assistant for hands-free web navigation.
            </p>
            
            <div className="space-y-3 mb-4">
              <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-spectra-primary/10 to-spectra-secondary/10 rounded-xl border border-spectra-primary/20">
                <div className="w-5 h-5 bg-spectra-primary rounded-full flex items-center justify-center text-white text-xs font-bold">1</div>
                <div>
                  <p className="text-sm font-medium text-white">Connect</p>
                  <p className="text-xs text-white/70">Press <kbd className="px-1.5 py-0.5 bg-white/10 rounded border border-white/20 font-mono text-xs">Q</kbd> or click below</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-white/5 rounded-xl border border-white/10">
                <div className="w-5 h-5 bg-white/20 rounded-full flex items-center justify-center text-white text-xs font-bold">2</div>
                <div>
                  <p className="text-sm font-medium text-white/70">Share screen</p>
                  <p className="text-xs text-white/60">Press <kbd className="px-1.5 py-0.5 bg-white/10 rounded border border-white/20 font-mono text-xs">W</kbd> when connected</p>
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleConnect}
                disabled={isConnecting}
                className="flex-1 px-4 py-2.5 bg-gradient-to-r from-spectra-primary to-spectra-secondary hover:from-spectra-primary/90 hover:to-spectra-secondary/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all text-sm focus:outline-none focus:ring-2 focus:ring-spectra-primary/50 flex items-center justify-center gap-2 shadow-lg"
              >
                {isConnecting ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                    </svg>
                    Connecting...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    Get Started
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {step === 'share-screen' && (
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
          <div className="flex-1 pr-6">
            <h3 id="onboarding-title" className="text-lg font-semibold text-white mb-2">
              Almost there!
            </h3>
            <p id="onboarding-description" className="text-white/80 text-sm mb-4">
              Now let's share your screen so I can help you navigate.
            </p>
            <div className="bg-gradient-to-r from-spectra-primary/10 to-spectra-secondary/10 rounded-xl p-4 border border-spectra-primary/20">
              <p className="text-sm font-medium text-white mb-2 flex items-center gap-2">
                <kbd className="px-2 py-1 bg-white/10 rounded border border-white/20 font-mono text-sm">W</kbd>
                Press W to share your screen
              </p>
              <p className="text-xs text-white/70">
                This allows me to see what's on your screen so I can help you click, scroll, and navigate.
              </p>
            </div>
          </div>
        </div>
      )}

      {step === 'ready' && (
        <div className="flex items-center gap-4">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
          <div className="flex-1 pr-6">
            <h3 className="text-lg font-semibold text-white mb-1">
              Perfect! You're all set
            </h3>
            <p className="text-sm text-white/80">
              I'm ready to help. Just say "Hey Spectra" or press Q to start.
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